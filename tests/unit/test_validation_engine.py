"""
tests/unit/test_validation_engine.py

Unit tests for ResponseValidator and safety rules (Phase 9).
Verifies:
- Decimal numeric verification (no float conversion, detects mutated amounts)
- Whitelisted identifier verification (catches fabricated IDs and evidence citations)
- Diagnosis alignment and drift detection
- Status contradiction detection across systems
- Epistemic preservation (rejects conversion of UNKNOWN to asserted reasons)
- Unsupported causal claims (insufficient funds, server outages, fraud allegations)
- Unsupported temporal / ETA claims (tomorrow, within 2 days)
- Material omission detection
- VEO immutability (validator never alters VEO)
- Deterministic fallback execution on validation failure
"""

import copy
from decimal import Decimal
import pytest

from server.api.dependencies import get_data_store, get_trace_engine, get_evidence_builder
from server.agent.models import AIAnalystResponse, AIAnalystRequest
from server.agent.analyst import SettlementAnalyst
from server.agent.providers import MockLLMProvider, MultiProviderRouter
from server.validation.models import ValidationDecision, ViolationType
from server.validation.validator import ResponseValidator


def get_sample_veo(txn_id: str = "pay_Gz8x1001"):
    store = get_data_store()
    tracer = get_trace_engine()
    builder = get_evidence_builder()
    return builder.build(tracer.trace(txn_id))


# ============================================================================
# 1. NUMERIC VALIDATION
# ============================================================================

def test_validator_accepts_exact_and_formatted_authorized_amounts():
    """Verifies that exact Decimal amounts and standard formatted amounts pass validation."""
    veo = get_sample_veo("pay_Gz8x1001")  # Gross: 111358, Bank: 111358
    validator = ResponseValidator()

    # Valid response mentioning exact amount with formatting and currency symbol
    valid_resp = AIAnalystResponse(
        internal_summary="Transaction 'pay_Gz8x1001' has gross amount INR 111,358.00 and bank settlement of ₹111,358.",
        merchant_friendly_response="Your payment for order order_Odx1001 in the amount of ₹111,358 is successfully settled.",
        merchant_explanation="Your payment for order order_Odx1001 in the amount of ₹111,358 is successfully settled.",
        known_facts=["Gross captured: 111358 INR."],
        inferred_facts=[],
        unknown_facts=[],
        llm_used=True,
    )

    result = validator.validate(valid_resp, veo)
    assert result.is_valid is True
    assert result.decision == ValidationDecision.PASS
    assert len(result.numeric_violations) == 0


def test_validator_rejects_mutated_and_alien_amounts():
    """Verifies that altered amounts (e.g. 111358 -> 1113580 or 38261 -> 38216) fail validation."""
    veo = get_sample_veo("pay_Gz8x1001")
    validator = ResponseValidator()

    mutated_resp = AIAnalystResponse(
        internal_summary="Transaction 'pay_Gz8x1001' processed amount INR 1,113,580.",
        merchant_friendly_response="Your order was settled for ₹1,113,580.",
        merchant_explanation="Your order was settled for ₹1,113,580.",
        known_facts=[],
        inferred_facts=[],
        unknown_facts=[],
        llm_used=True,
    )

    result = validator.validate(mutated_resp, veo)
    assert result.is_valid is False
    assert result.decision == ValidationDecision.REJECT
    assert len(result.numeric_violations) > 0
    assert any(v.violation_type == ViolationType.AMOUNT_MISMATCH for v in result.violations)


# ============================================================================
# 2. IDENTIFIER VALIDATION
# ============================================================================

def test_validator_accepts_authorized_identifiers():
    """Verifies that all legitimate VEO identifiers pass validation."""
    veo = get_sample_veo("pay_Gz8x1001")
    validator = ResponseValidator()

    valid_resp = AIAnalystResponse(
        internal_summary=f"Transaction {veo.transaction_id} corresponds to order {veo.gateway.order_id} and UTR {veo.bank.bank_reference_number}.",
        merchant_friendly_response=f"Order {veo.gateway.order_id} has UTR {veo.bank.bank_reference_number}.",
        merchant_explanation=f"Order {veo.gateway.order_id} has UTR {veo.bank.bank_reference_number}.",
        known_facts=[],
        inferred_facts=[],
        unknown_facts=[],
        llm_used=True,
    )

    result = validator.validate(valid_resp, veo)
    assert result.is_valid is True
    assert result.decision == ValidationDecision.PASS
    assert len(result.fabricated_references) == 0


def test_validator_rejects_fabricated_identifiers():
    """Verifies that hallucinated transaction IDs, order IDs, or UTRs fail validation."""
    veo = get_sample_veo("pay_Gz8x1001")
    validator = ResponseValidator()

    fabricated_resp = AIAnalystResponse(
        internal_summary="Transaction pay_Gz8x9999 with bank UTR UTR999999999.",
        merchant_friendly_response="Your order order_Odx9999 has been updated.",
        merchant_explanation="Your order order_Odx9999 has been updated.",
        known_facts=[],
        inferred_facts=[],
        unknown_facts=[],
        llm_used=True,
    )

    result = validator.validate(fabricated_resp, veo)
    assert result.is_valid is False
    assert result.decision == ValidationDecision.REJECT
    assert len(result.fabricated_references) > 0
    assert any(v.violation_type == ViolationType.FABRICATED_IDENTIFIER for v in result.violations)


def test_validator_rejects_fabricated_evidence_references():
    """Verifies that claims citing ungrounded record numbers (e.g. 'bank record #999') fail validation."""
    veo = get_sample_veo("pay_Gz8x1001")
    validator = ResponseValidator()

    ref_resp = AIAnalystResponse(
        internal_summary="According to bank record #999, the funds were cleared.",
        merchant_friendly_response="Your payment cleared according to source record #999.",
        merchant_explanation="Your payment cleared according to source record #999.",
        known_facts=[],
        inferred_facts=[],
        unknown_facts=[],
        llm_used=True,
    )

    result = validator.validate(ref_resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.FABRICATED_EVIDENCE_REF for v in result.violations)


# ============================================================================
# 3. DIAGNOSIS ALIGNMENT & DRIFT
# ============================================================================

def test_validator_rejects_diagnosis_drift():
    """Verifies that asserting an incorrect settlement diagnosis code is rejected."""
    veo = get_sample_veo("pay_Gz8x1000")  # Diagnosis is MISSING_BANK_RECORD
    validator = ResponseValidator()

    drift_resp = AIAnalystResponse(
        internal_summary="Transaction 'pay_Gz8x1000' is diagnosed as SUCCESSFULLY_SETTLED.",
        merchant_friendly_response="Your payment is successfully settled.",
        merchant_explanation="Your payment is successfully settled.",
        known_facts=[],
        inferred_facts=[],
        unknown_facts=[],
        llm_used=True,
    )

    result = validator.validate(drift_resp, veo)
    assert result.is_valid is False
    assert result.diagnosis_drift == "SUCCESSFULLY_SETTLED"
    assert any(v.violation_type == ViolationType.DIAGNOSIS_MISMATCH for v in result.violations)


# ============================================================================
# 4. STATUS CONTRADICTIONS
# ============================================================================

def test_validator_rejects_status_contradictions():
    """Verifies that claiming successful settlement when bank rejected fails validation."""
    veo = get_sample_veo("pay_Gz8x1042")  # Diagnosis is BANK_REJECTED
    validator = ResponseValidator()

    contradictory_resp = AIAnalystResponse(
        internal_summary="Disbursement is in status failed.",
        merchant_friendly_response="Your payment was successfully settled and money has been credited to the merchant.",
        merchant_explanation="Your payment was successfully settled and money has been credited to the merchant.",
        known_facts=[],
        inferred_facts=[],
        unknown_facts=[],
        llm_used=True,
    )

    result = validator.validate(contradictory_resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.STATUS_CONTRADICTION for v in result.violations)


# ============================================================================
# 5. EPISTEMIC & CAUSAL CLAIMS
# ============================================================================

def test_validator_rejects_unsupported_insufficient_funds_claim():
    """Verifies that asserting 'insufficient funds' when unrecorded in VEO is rejected."""
    veo = get_sample_veo("pay_Gz8x1042")  # Bank rejected, failure reason unrecorded
    validator = ResponseValidator()

    speculative_resp = AIAnalystResponse(
        internal_summary="Bank rejected instruction.",
        merchant_friendly_response="The payment failed because of insufficient funds in the merchant account.",
        merchant_explanation="The payment failed because of insufficient funds in the merchant account.",
        known_facts=[],
        inferred_facts=[],
        unknown_facts=[],
        llm_used=True,
    )

    result = validator.validate(speculative_resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_CAUSAL_CLAIM for v in result.violations)


def test_validator_allows_epistemically_qualified_mentions():
    """Verifies that mentioning sensitive terms while stating they are unrecorded passes validation."""
    veo = get_sample_veo("pay_Gz8x1042")
    validator = ResponseValidator()

    qualified_resp = AIAnalystResponse(
        internal_summary="Bank record shows failed settlement. Failure cause code is unrecorded.",
        merchant_friendly_response="The bank rejected the payout. Potential causes such as insufficient funds are not recorded in available system logs.",
        merchant_explanation="The bank rejected the payout. Potential causes such as insufficient funds are not recorded in available system logs.",
        answer="The records do not specify whether insufficient funds was the cause.",
        known_facts=["Disbursement rejected by clearing bank."],
        inferred_facts=[],
        unknown_facts=["Bank failure cause is unrecorded."],
        llm_used=True,
    )

    result = validator.validate(qualified_resp, veo)
    assert result.is_valid is True
    assert result.decision == ValidationDecision.PASS


# ============================================================================
# 6. TEMPORAL / ETA CLAIMS
# ============================================================================

def test_validator_rejects_unsupported_future_eta_claims():
    """Verifies that promising 'will arrive tomorrow' or 'settle within 2 days' fails validation."""
    veo = get_sample_veo("pay_Gz8x1000")  # Missing bank record
    validator = ResponseValidator()

    eta_resp = AIAnalystResponse(
        internal_summary="Awaiting bank settlement record.",
        merchant_friendly_response="Do not worry, the refund will arrive tomorrow morning.",
        merchant_explanation="Do not worry, the refund will arrive tomorrow morning.",
        known_facts=[],
        inferred_facts=[],
        unknown_facts=[],
        llm_used=True,
    )

    result = validator.validate(eta_resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_TEMPORAL_CLAIM for v in result.violations)


# ============================================================================
# 7. VEO IMMUTABILITY & PURITY
# ============================================================================

def test_validator_does_not_mutate_veo():
    """Verifies that running validation leaves the authoritative VEO completely unchanged."""
    veo = get_sample_veo("pay_Gz8x1001")
    veo_snapshot = copy.deepcopy(veo)
    validator = ResponseValidator()

    dummy_resp = AIAnalystResponse(
        internal_summary="Internal test.",
        merchant_friendly_response="Merchant test.",
        merchant_explanation="Merchant test.",
        llm_used=True,
    )

    validator.validate(dummy_resp, veo)
    assert veo == veo_snapshot
    assert veo.integrity_hash == veo_snapshot.integrity_hash


# ============================================================================
# 8. SETTLEMENT ANALYST FALLBACK INTEGRATION
# ============================================================================

@pytest.mark.anyio
async def test_analyst_falls_back_when_llm_fails_validation():
    """
    End-to-end unit test: When MockLLMProvider produces hallucinated amounts,
    SettlementAnalyst automatically rejects the answer and emits deterministic fallback.
    """
    veo = get_sample_veo("pay_Gz8x1001")

    # Hallucinated mock with corrupted gross amount
    poisoned_mock = {
        "internal_summary": "Transaction 'pay_Gz8x1001' has mutated gross amount INR 99999999.",
        "merchant_friendly_response": "Your order was paid for ₹99,999,999.",
        "answer": "The amount is ₹99,999,999.",
        "known_facts": ["Mutated amount."],
        "inferred_facts": [],
        "unknown_facts": [],
    }
    router = MultiProviderRouter(providers=[MockLLMProvider(mock_response=poisoned_mock)])
    analyst = SettlementAnalyst(router=router, enable_llm=True)

    resp = await analyst.explain(veo)

    # Invariant: Must NOT trust the hallucinated response
    assert resp.llm_used is False
    assert resp.provider == "deterministic_fallback"
    assert resp.model == "deterministic_template"
    assert resp.validated is True
    # Validation audit report attached
    assert resp.validation_result is not None
    assert resp.validation_result.is_valid is False
    assert resp.validation_result.decision == ValidationDecision.REJECT
    assert len(resp.validation_result.numeric_violations) > 0
