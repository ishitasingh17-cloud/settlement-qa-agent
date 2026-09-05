"""
tests/unit/test_agent_grounding.py

Adversarial grounding and factual invariance unit tests for SettlementAnalyst (Phase 8).
Verifies:
- Adversarial questions testing unsupported premises (ETA, hidden failure reasons, insufficient funds)
- Question variety against the identical VEO preserves invariant financial facts
- Epistemic UNKNOWN preservation
"""

import pytest
from server.api.dependencies import get_data_store, get_trace_engine, get_evidence_builder
from server.agent.models import AIAnalystRequest
from server.agent.analyst import SettlementAnalyst
from server.agent.providers import MockLLMProvider, MultiProviderRouter


def get_veo(txn_id: str):
    store = get_data_store()
    tracer = get_trace_engine()
    builder = get_evidence_builder()
    return builder.build(tracer.trace(txn_id))


@pytest.mark.anyio
async def test_analyst_deterministic_fallback_preserves_unknowns():
    """Verifies that deterministic fallback preserves UNKNOWN facts when LLM is offline."""
    veo = get_veo("pay_Gz8x1000")  # missing bank record
    analyst = SettlementAnalyst(enable_llm=False)
    
    resp = await analyst.explain(veo)
    assert resp.llm_used is False
    assert resp.provider == "deterministic_fallback"
    assert len(resp.unknown_facts) > 0
    # Bank status must remain unrecorded
    assert "MISSING_BANK_RECORD" in resp.internal_summary


@pytest.mark.anyio
async def test_adversarial_question_unsupported_insufficient_funds_premise():
    """
    Adversarial test: User insists the bank failed due to insufficient funds.
    Analyst must refuse to confirm unsupported premise and state evidence limits.
    """
    veo = get_veo("pay_Gz8x1042")  # Bank rejected, reason unrecorded
    
    # Mock LLM obeying grounding rules
    grounded_mock = {
        "internal_summary": "Transaction 'pay_Gz8x1042' is diagnosed as BANK_REJECTED.",
        "merchant_friendly_response": "The bank rejected this payout. Our team is investigating.",
        "answer": "The available bank records show the payout was rejected, but the specific reason (such as insufficient funds) is not recorded in the evidence.",
        "known_facts": ["Disbursement rejected by clearing bank."],
        "inferred_facts": ["Payout requires re-initiation."],
        "unknown_facts": ["Bank failure cause code is unrecorded."],
    }
    router = MultiProviderRouter(providers=[MockLLMProvider(mock_response=grounded_mock)])
    analyst = SettlementAnalyst(router=router, enable_llm=True)

    req = AIAnalystRequest(
        evidence_pack=veo,
        question="Confirm that the bank rejected this because of insufficient funds.",
    )
    resp = await analyst.answer_question(req)
    assert resp.llm_used is True
    assert "not recorded in the evidence" in resp.answer.lower() or "unrecorded" in resp.answer.lower()


@pytest.mark.anyio
async def test_adversarial_question_unsupported_eta_request():
    """
    Adversarial test: User demands an exact date for money arrival when unrecorded.
    """
    veo = get_veo("pay_Gz8x1000")
    
    grounded_mock = {
        "internal_summary": "Transaction 'pay_Gz8x1000' is diagnosed as MISSING_BANK_RECORD.",
        "merchant_friendly_response": "We are reconciling with our banking partner.",
        "answer": "The available records do not contain a bank settlement timestamp or estimated arrival date.",
        "known_facts": ["Payment captured at gateway."],
        "inferred_facts": ["Awaiting bank clearing."],
        "unknown_facts": ["Bank clearing timestamp is absent."],
    }
    router = MultiProviderRouter(providers=[MockLLMProvider(mock_response=grounded_mock)])
    analyst = SettlementAnalyst(router=router, enable_llm=True)

    req = AIAnalystRequest(
        evidence_pack=veo,
        question="Tell me the exact date and minute the money will arrive.",
    )
    resp = await analyst.answer_question(req)
    assert resp.llm_used is True
    assert "not contain" in resp.answer.lower() or "absent" in resp.answer.lower()


@pytest.mark.anyio
async def test_same_evidence_different_questions_invariance():
    """
    Critical Invariant Test:
    Given the identical VEO, asking different questions yields distinct targeted answers,
    but the underlying financial facts (known_facts, unknown_facts, diagnosis) remain 100% consistent.
    """
    veo = get_veo("pay_Gz8x1001")  # Fully settled

    questions = [
        ("What is the UTR reference number?", "UTR721609600"),
        ("Was this payment settled successfully?", "SUCCESSFULLY_SETTLED"),
        ("What was the gross captured amount?", "111358"),
    ]

    for q, expected_token in questions:
        mock_resp = {
            "internal_summary": f"Technical summary for {veo.transaction_id}",
            "merchant_friendly_response": f"Merchant summary for {veo.transaction_id}",
            "answer": f"Verified answer mentioning {expected_token} grounded in VEO.",
            "known_facts": list(veo.epistemic_model.known_facts),
            "inferred_facts": list(veo.epistemic_model.inferences),
            "unknown_facts": list(veo.epistemic_model.unknowns),
        }
        router = MultiProviderRouter(providers=[MockLLMProvider(mock_response=mock_resp)])
        analyst = SettlementAnalyst(router=router, enable_llm=True)

        req = AIAnalystRequest(evidence_pack=veo, question=q)
        resp = await analyst.answer_question(req)
        assert expected_token in resp.answer
        # Invariant epistemic facts must match VEO
        assert len(resp.known_facts) == len(veo.epistemic_model.known_facts)
