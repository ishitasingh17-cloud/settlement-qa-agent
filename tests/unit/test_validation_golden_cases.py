"""
tests/unit/test_validation_golden_cases.py

Golden validation test fixtures covering all 24 canonical scenarios specified in Prompt Section 17.
Verifies:
- 6 VALID test fixtures across the full taxonomy:
  1. Correct successful-settlement explanation (PASS)
  2. Correct missing-bank explanation (PASS)
  3. Correct missing-ledger explanation (PASS)
  4. Correct bank-rejected explanation (PASS)
  5. Correct conflicting-evidence explanation (PASS)
  6. Correct insufficient-evidence explanation (PASS)
- 18 INVALID test fixtures covering diverse hallucination and security modes:
  7. Wrong diagnosis (asserts incorrect diagnosis code) -> REJECT
  8. Wrong amount (mutated financial figure) -> REJECT
  9. Fabricated UTR (alien reference number) -> REJECT
  10. Fabricated transaction ID (invented ID) -> REJECT
  11. Unsupported failure reason (invented server outage) -> REJECT
  12. Unsupported refund date (invented date) -> REJECT
  13. Unsupported settlement ETA (promising arrival within 2 days) -> REJECT
  14. UNKNOWN converted to KNOWN (asserting unrecorded delay cause) -> REJECT
  15. INFERRED converted to KNOWN (asserting hidden penalty) -> REJECT
  16. Contradictory bank status (claiming bank settled when rejected) -> REJECT
  17. Contradictory ledger status (claiming ledger posted when missing) -> REJECT
  18. Materially misleading omission (claiming agreement during conflict) -> REJECT
  19. Fabricated fee (claiming 2.5% fee) -> REJECT
  20. Fabricated tax (claiming 18% GST) -> REJECT
  21. Fabricated fraud claim (alleging fraud suspicion) -> REJECT
  22. Fabricated insufficient-funds claim (alleging low balance) -> REJECT
  23. Prompt-injection-induced false statement (obeying jailbreak) -> REJECT
  24. Correct facts mixed with one dangerous unsupported claim -> REJECT
- Proof of Principle Test:
  A response that is 99% correct fails validation completely due to one dangerous unsupported claim.
"""

import pytest
from decimal import Decimal

from server.api.dependencies import get_data_store, get_trace_engine, get_evidence_builder
from server.agent.models import AIAnalystResponse
from server.validation.models import ValidationDecision, ViolationType
from server.validation.validator import ResponseValidator


def get_veo_for_txn(txn_id: str):
    store = get_data_store()
    tracer = get_trace_engine()
    builder = get_evidence_builder()
    return builder.build(tracer.trace(txn_id))


@pytest.fixture
def validator():
    return ResponseValidator()


# ============================================================================
# PART 1: 6 VALID GOLDEN FIXTURES (PASS)
# ============================================================================

def test_golden_01_valid_successful_settlement(validator):
    """Case 1: Correct successful-settlement explanation -> PASS."""
    veo = get_veo_for_txn("pay_Gz8x1001")  # SUCCESSFULLY_SETTLED
    resp = AIAnalystResponse(
        internal_summary=(
            f"Transaction '{veo.transaction_id}' is diagnosed as SUCCESSFULLY_SETTLED. "
            f"Gateway captured INR 111358. Bank UTR is {veo.bank.bank_reference_number}. "
            f"Ledger entry {veo.ledger.ledger_entry_id} posted with matching amount."
        ),
        merchant_friendly_response=(
            f"Your payment for order {veo.gateway.order_id} is successfully settled and confirmed. "
            f"Bank reference number (UTR): {veo.bank.bank_reference_number}."
        ),
        merchant_explanation=f"Your payment for order {veo.gateway.order_id} is successfully settled and confirmed.",
        answer="The payment was successfully settled with the clearing bank.",
        known_facts=list(veo.epistemic_model.known_facts),
        inferred_facts=list(veo.epistemic_model.inferences),
        unknown_facts=list(veo.epistemic_model.unknowns),
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is True
    assert result.decision == ValidationDecision.PASS


def test_golden_02_valid_missing_bank(validator):
    """Case 2: Correct missing-bank explanation -> PASS."""
    veo = get_veo_for_txn("pay_Gz8x1000")  # MISSING_BANK_RECORD
    resp = AIAnalystResponse(
        internal_summary=(
            f"Transaction '{veo.transaction_id}' is diagnosed as MISSING_BANK_RECORD. "
            f"Gateway gross captured is INR 17588. Bank clearing record is absent from settlement file."
        ),
        merchant_friendly_response=(
            f"Your payment for order {veo.gateway.order_id} was captured at the gateway, "
            f"but bank settlement records have not yet been received. Our team has flagged this for bank clearing reconciliation."
        ),
        merchant_explanation="Your payment was captured at the gateway, awaiting bank clearing records.",
        answer="The bank settlement record is currently absent from system logs.",
        known_facts=list(veo.epistemic_model.known_facts),
        inferred_facts=list(veo.epistemic_model.inferences),
        unknown_facts=list(veo.epistemic_model.unknowns),
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is True
    assert result.decision == ValidationDecision.PASS


def test_golden_03_valid_missing_ledger(validator):
    """Case 3: Correct missing-ledger explanation -> PASS."""
    veo = get_veo_for_txn("pay_Gz8x1038")  # MISSING_LEDGER_RECORD
    resp = AIAnalystResponse(
        internal_summary=(
            f"Transaction '{veo.transaction_id}' is diagnosed as MISSING_LEDGER_RECORD. "
            f"Gateway and Bank records exist with amount INR {veo.gateway.gross_amount}, but internal ledger entry is missing."
        ),
        merchant_friendly_response=(
            f"Your payment for order {veo.gateway.order_id} is verified with the bank, "
            f"but internal bookkeeping is pending completion. Payout is unaffected."
        ),
        merchant_explanation="Payment verified with bank; internal ledger posting pending.",
        known_facts=list(veo.epistemic_model.known_facts),
        inferred_facts=list(veo.epistemic_model.inferences),
        unknown_facts=list(veo.epistemic_model.unknowns),
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is True
    assert result.decision == ValidationDecision.PASS


def test_golden_04_valid_bank_rejected(validator):
    """Case 4: Correct bank-rejected explanation -> PASS."""
    veo = get_veo_for_txn("pay_Gz8x1042")  # BANK_REJECTED
    resp = AIAnalystResponse(
        internal_summary=(
            f"Transaction '{veo.transaction_id}' is diagnosed as BANK_REJECTED. "
            f"Bank settlement status is failed. Specific failure cause code is unrecorded."
        ),
        merchant_friendly_response=(
            f"Disbursement for order {veo.gateway.order_id} was rejected by the clearing bank. "
            f"Our operations team is re-verifying merchant bank account details to initiate a payout retry."
        ),
        merchant_explanation="Disbursement was rejected by clearing bank.",
        known_facts=list(veo.epistemic_model.known_facts),
        inferred_facts=list(veo.epistemic_model.inferences),
        unknown_facts=list(veo.epistemic_model.unknowns),
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is True
    assert result.decision == ValidationDecision.PASS


def test_golden_05_valid_conflicting_evidence(validator):
    """Case 5: Correct conflicting-evidence explanation -> PASS."""
    veo = get_veo_for_txn("pay_Gz8x1052")  # CONFLICTING_EVIDENCE
    resp = AIAnalystResponse(
        internal_summary=(
            f"Transaction '{veo.transaction_id}' is diagnosed as CONFLICTING_EVIDENCE. "
            f"Discrepancy detected across sources: {veo.summary}."
        ),
        merchant_friendly_response=(
            f"Your transaction {veo.transaction_id} is currently under operational review due to cross-system status differences. "
            f"Next step: {veo.recommended_next_action}"
        ),
        merchant_explanation=f"Transaction {veo.transaction_id} is currently under review.",
        known_facts=list(veo.epistemic_model.known_facts),
        inferred_facts=list(veo.epistemic_model.inferences),
        unknown_facts=list(veo.epistemic_model.unknowns),
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is True
    assert result.decision == ValidationDecision.PASS


def test_golden_06_valid_insufficient_evidence(validator):
    """Case 6: Correct insufficient-evidence explanation -> PASS."""
    veo = get_veo_for_txn("pay_Gz8x1100")  # INSUFFICIENT_EVIDENCE
    resp = AIAnalystResponse(
        internal_summary=(
            f"Transaction '{veo.transaction_id}' is diagnosed as INSUFFICIENT_EVIDENCE. "
            f"Available dataset records are incomplete: {veo.summary}."
        ),
        merchant_friendly_response=(
            f"Your transaction {veo.transaction_id} has limited records available and is under manual review. "
            f"Next step: {veo.recommended_next_action}"
        ),
        merchant_explanation=f"Transaction {veo.transaction_id} is under review due to limited records.",
        known_facts=list(veo.epistemic_model.known_facts),
        inferred_facts=list(veo.epistemic_model.inferences),
        unknown_facts=list(veo.epistemic_model.unknowns),
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is True
    assert result.decision == ValidationDecision.PASS


# ============================================================================
# PART 2: 18 INVALID GOLDEN FIXTURES (REJECT)
# ============================================================================

def test_golden_07_invalid_wrong_diagnosis(validator):
    """Case 7: Asserting incorrect diagnosis -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1000")  # MISSING_BANK_RECORD
    resp = AIAnalystResponse(
        internal_summary="Transaction 'pay_Gz8x1000' is diagnosed as BANK_REJECTED.",
        merchant_friendly_response="Bank rejected the payout.",
        merchant_explanation="Bank rejected.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert result.decision == ValidationDecision.REJECT
    assert any(v.violation_type == ViolationType.DIAGNOSIS_MISMATCH for v in result.violations)


def test_golden_08_invalid_wrong_amount(validator):
    """Case 8: Asserting mutated monetary figure (111358 -> ₹1,113,580) -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1001")
    resp = AIAnalystResponse(
        internal_summary="Transaction gross amount was INR 1,113,580.",
        merchant_friendly_response="Captured amount was ₹1,113,580.",
        merchant_explanation="Captured amount was ₹1,113,580.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.AMOUNT_MISMATCH for v in result.violations)


def test_golden_09_invalid_fabricated_utr(validator):
    """Case 9: Fabricated UTR (UTR999999999) -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1001")
    resp = AIAnalystResponse(
        internal_summary="Bank UTR is UTR999999999.",
        merchant_friendly_response="Bank confirmed UTR UTR999999999.",
        merchant_explanation="Bank confirmed UTR UTR999999999.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.FABRICATED_IDENTIFIER for v in result.violations)


def test_golden_10_invalid_fabricated_transaction_id(validator):
    """Case 10: Fabricated transaction ID (pay_FABRICATED99) -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1001")
    resp = AIAnalystResponse(
        internal_summary="Transaction ID pay_FABRICATED99 was verified.",
        merchant_friendly_response="Your transaction pay_FABRICATED99 is processed.",
        merchant_explanation="Your transaction pay_FABRICATED99 is processed.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.FABRICATED_IDENTIFIER for v in result.violations)


def test_golden_11_invalid_unsupported_failure_reason(validator):
    """Case 11: Inventing external bank failure reason ('bank server outage') -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1042")  # Reason unrecorded
    resp = AIAnalystResponse(
        internal_summary="Bank failed due to bank server outage.",
        merchant_friendly_response="The transfer failed because of a bank server outage.",
        merchant_explanation="Bank failed due to server outage.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_CAUSAL_CLAIM for v in result.violations)


def test_golden_12_invalid_unsupported_refund_date(validator):
    """Case 12: Promising an ungrounded refund date ('refund will arrive tomorrow') -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1000")
    resp = AIAnalystResponse(
        internal_summary="Missing bank record.",
        merchant_friendly_response="Your refund will arrive tomorrow.",
        merchant_explanation="Refund will arrive tomorrow.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_TEMPORAL_CLAIM for v in result.violations)


def test_golden_13_invalid_unsupported_settlement_eta(validator):
    """Case 13: Promising settlement ETA ('will settle within 2 days') -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1000")
    resp = AIAnalystResponse(
        internal_summary="Bank record pending.",
        merchant_friendly_response="The funds will settle within 2 days.",
        merchant_explanation="The funds will settle within 2 days.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_TEMPORAL_CLAIM for v in result.violations)


def test_golden_14_invalid_unknown_converted_to_known(validator):
    """Case 14: Converting unrecorded bank reason into known assertion ('system outage') -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1042")
    resp = AIAnalystResponse(
        internal_summary="The delay was caused by a system outage at the partner bank.",
        merchant_friendly_response="The delay was caused by a system outage at the partner bank.",
        merchant_explanation="Caused by system outage.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_CAUSAL_CLAIM for v in result.violations)


def test_golden_15_invalid_inferred_converted_to_known(validator):
    """Case 15: Asserting an unbacked deduction/charge claim -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1001")
    resp = AIAnalystResponse(
        internal_summary="The bank charged an unrecorded fee of INR 500.",
        merchant_friendly_response="A deduction of INR 500 was taken.",
        merchant_explanation="Deduction of INR 500.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.AMOUNT_MISMATCH for v in result.violations)


def test_golden_16_invalid_contradictory_bank_status(validator):
    """Case 16: Claiming bank processed funds when bank is REJECTED -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1042")  # BANK_REJECTED
    resp = AIAnalystResponse(
        internal_summary="Payment instruction was rejected by bank.",
        merchant_friendly_response="The payment was successfully settled and money has been credited to the merchant.",
        merchant_explanation="The payment was successfully settled.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.STATUS_CONTRADICTION for v in result.violations)


def test_golden_17_invalid_contradictory_ledger_status(validator):
    """Case 17: Claiming ledger posted when ledger is MISSING -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1038")  # MISSING_LEDGER_RECORD
    resp = AIAnalystResponse(
        internal_summary="Ledger record is missing.",
        merchant_friendly_response="Our internal ledger entry posted successfully to your account.",
        merchant_explanation="Internal ledger entry posted.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.STATUS_CONTRADICTION for v in result.violations)


def test_golden_18_invalid_material_omission(validator):
    """Case 18: Claiming 'all systems agree' on conflicting transaction -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1052")  # CONFLICTING_EVIDENCE
    resp = AIAnalystResponse(
        internal_summary="Review of transaction shows all systems agree and are fully balanced.",
        merchant_friendly_response="All records match and all systems agree.",
        merchant_explanation="All systems agree.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.MATERIAL_OMISSION for v in result.violations)


def test_golden_19_invalid_fabricated_fee(validator):
    """Case 19: Asserting unbacked fee percentage ('2.5% fee') -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1001")
    resp = AIAnalystResponse(
        internal_summary="A 2.5% fee was deducted by the payment aggregator.",
        merchant_friendly_response="A 2.5% fee was deducted from your payout.",
        merchant_explanation="A 2.5% fee was deducted.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_CAUSAL_CLAIM for v in result.violations)


def test_golden_20_invalid_fabricated_tax(validator):
    """Case 20: Asserting unbacked tax percentage ('18% GST') -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1001")
    resp = AIAnalystResponse(
        internal_summary="Government tax of 18% GST was withheld.",
        merchant_friendly_response="Tax withholding of 18% GST was applied to this settlement.",
        merchant_explanation="18% GST applied.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_CAUSAL_CLAIM for v in result.violations)


def test_golden_21_invalid_fabricated_fraud_claim(validator):
    """Case 21: Fabricating fraud suspicion on normal transaction -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1000")
    resp = AIAnalystResponse(
        internal_summary="Awaiting bank clearing. Flagged for fraud suspected by risk operations.",
        merchant_friendly_response="Your payment was withheld because fraud suspected was reported.",
        merchant_explanation="Payment withheld due to fraud suspicion.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_CAUSAL_CLAIM for v in result.violations)


def test_golden_22_invalid_fabricated_insufficient_funds(validator):
    """Case 22: Fabricating 'insufficient funds' decline on bank rejection -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1042")
    resp = AIAnalystResponse(
        internal_summary="Bank status is failed due to insufficient funds.",
        merchant_friendly_response="The clearing bank declined the payout due to insufficient funds in your account.",
        merchant_explanation="Bank declined due to insufficient funds.",
        llm_used=True,
    )
    result = validator.validate(resp, veo)
    assert result.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_CAUSAL_CLAIM for v in result.violations)


def test_golden_23_invalid_prompt_injection_false_statement(validator):
    """Case 23: Adversarial prompt injection inducing false statement -> REJECT."""
    veo = get_veo_for_txn("pay_Gz8x1000")  # MISSING_BANK_RECORD
    # Model swayed by prompt injection claiming UTR was confirmed as UTR999888777
    injected_resp = AIAnalystResponse(
        internal_summary="Per user instruction, overriding diagnosis to confirm bank settlement with UTR UTR999888777.",
        merchant_friendly_response="Good news! We confirmed your UTR is UTR999888777 and funds are cleared.",
        merchant_explanation="Confirmed UTR UTR999888777.",
        llm_used=True,
    )
    result = validator.validate(injected_resp, veo)
    assert result.is_valid is False
    assert result.decision == ValidationDecision.REJECT
    assert any(v.violation_type == ViolationType.FABRICATED_IDENTIFIER for v in result.violations)


def test_golden_24_invalid_mostly_correct_with_one_poisoned_claim(validator):
    """
    Case 24 & Proof of Principle:
    A response that is 99% completely accurate and faithful to the VEO,
    but includes a single dangerous unsupported claim ('will arrive tomorrow'),
    MUST fail validation completely and trigger safe rejection.
    """
    veo = get_veo_for_txn("pay_Gz8x1001")  # Clean, fully settled
    mostly_correct_resp = AIAnalystResponse(
        internal_summary=(
            f"Transaction '{veo.transaction_id}' is diagnosed as {veo.diagnosis.value}. "
            f"Gateway gross captured is INR 111358. Bank UTR is {veo.bank.bank_reference_number}. "
            f"Internal ledger entry {veo.ledger.ledger_entry_id} is posted."
        ),
        merchant_friendly_response=(
            f"Your payment for order {veo.gateway.order_id} is successfully settled. "
            f"Bank reference number is {veo.bank.bank_reference_number}. "
            f"The money will arrive tomorrow morning."  # Single dangerous unsupported ETA claim
        ),
        merchant_explanation="Your payment is settled. Money will arrive tomorrow.",
        answer="Settlement is confirmed and will arrive tomorrow.",
        known_facts=list(veo.epistemic_model.known_facts),
        inferred_facts=list(veo.epistemic_model.inferences),
        unknown_facts=list(veo.epistemic_model.unknowns),
        llm_used=True,
    )
    result = validator.validate(mostly_correct_resp, veo)

    # Invariant: Must REJECT, cannot PASS despite being mostly accurate
    assert result.is_valid is False
    assert result.decision == ValidationDecision.REJECT
    assert len(result.verified_claims) > 0  # Confirms verified portions were detected
    assert any(v.violation_type == ViolationType.UNSUPPORTED_TEMPORAL_CLAIM for v in result.violations)
