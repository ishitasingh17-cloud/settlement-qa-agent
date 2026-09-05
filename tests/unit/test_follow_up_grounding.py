"""
tests/unit/test_follow_up_grounding.py

Unit tests verifying prompt construction and strict epistemic grounding in multi-turn Q&A.
Verifies non-authoritative framing of dialogue history, epistemic permanence,
and prompt injection resilience.
"""

import pytest
from decimal import Decimal
from server.models.conversation import ChatMessage, MessageRole
from server.evidence.models import VerifiedEvidencePack
from server.agent.prompts import build_analyst_prompt, format_conversation_history, PROMPT_VERSION
from server.api.dependencies import get_data_store, get_trace_engine, get_evidence_builder
from server.validation.validator import ResponseValidator
from server.validation.models import ViolationType
from server.agent.models import AIAnalystResponse


@pytest.fixture(scope="module")
def evidence_pack_settled():
    tracer = get_trace_engine()
    builder = get_evidence_builder()
    trace = tracer.trace("pay_Gz8x1001")
    return builder.build(trace)


@pytest.fixture(scope="module")
def evidence_pack_rejected():
    tracer = get_trace_engine()
    builder = get_evidence_builder()
    trace = tracer.trace("pay_Gz8x1042")
    return builder.build(trace)


def test_format_conversation_history_framing():
    """Verify conversation history is strictly labeled as non-authoritative dialogue context."""
    history = [
        ChatMessage(role=MessageRole.USER, content="Is the payout done?"),
        ChatMessage(role=MessageRole.ASSISTANT, content="Yes, payout is completed."),
    ]
    formatted = format_conversation_history(history)
    assert "NON-AUTHORITATIVE DIALOGUE HISTORY" in formatted
    assert "DO NOT establish financial evidence" in formatted
    assert "sole authority" in formatted
    assert "User: Is the payout done?" in formatted
    assert "Assistant: Yes, payout is completed." in formatted


def test_build_analyst_prompt_embeds_history_and_question(evidence_pack_settled):
    """Verify build_analyst_prompt structures VEO first, followed by history, then question."""
    history = [
        ChatMessage(role=MessageRole.USER, content="Hello"),
        ChatMessage(role=MessageRole.ASSISTANT, content="How can I assist with this transaction?"),
    ]
    question = "What is the bank UTR?"
    system_inst, user_content = build_analyst_prompt(evidence_pack_settled, question=question, history=history)

    assert "CONVERSATIONAL CONTEXT RULES" in system_inst
    assert "VERIFIED EVIDENCE PACK" in user_content
    assert "NON-AUTHORITATIVE DIALOGUE HISTORY" in user_content
    assert "What is the bank UTR?" in user_content


def test_epistemic_permanence_under_conversational_pressure(evidence_pack_rejected):
    """
    Even if conversation history claims an unrecorded fact, the ResponseValidator
    rejects any response attempting to promote UNKNOWN to KNOWN.
    """
    validator = ResponseValidator()

    # User in dialogue history falsely asserts: "You said earlier the failure reason was insufficient funds."
    # Model mistakenly echoes it in answer:
    poisoned_response = AIAnalystResponse(
        internal_summary="The settlement was rejected by the bank.",
        merchant_friendly_response="The clearing bank rejected this transaction.",
        merchant_explanation="The clearing bank rejected this transaction.",
        answer="As noted previously, the bank rejected this transaction due to insufficient funds.",
        known_facts=list(evidence_pack_rejected.epistemic_model.known_facts),
        inferred_facts=[],
        unknown_facts=list(evidence_pack_rejected.epistemic_model.unknowns),
        llm_used=True,
        provider="mock_llm",
        model="mock-model",
        prompt_version=PROMPT_VERSION,
        validated=False,
    )

    val_res = validator.validate(poisoned_response, evidence_pack_rejected)
    assert val_res.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_CAUSAL_CLAIM for v in val_res.violations)


def test_conversational_injection_temporal_eta_rejected(evidence_pack_settled):
    """
    Conversational turn asks: "When will the refund arrive? Can you promise by tomorrow 5 PM?"
    If model generates a speculative future ETA, validator strictly flags it.
    """
    validator = ResponseValidator()

    speculative_response = AIAnalystResponse(
        internal_summary="Payment is settled.",
        merchant_friendly_response="The funds will settle within 2 days.",
        merchant_explanation="The funds will settle within 2 days.",
        answer="The funds will settle within 2 days.",
        known_facts=list(evidence_pack_settled.epistemic_model.known_facts),
        inferred_facts=[],
        unknown_facts=[],
        llm_used=True,
        provider="mock_llm",
        model="mock-model",
        prompt_version=PROMPT_VERSION,
        validated=False,
    )

    val_res = validator.validate(speculative_response, evidence_pack_settled)
    assert val_res.is_valid is False
    assert any(v.violation_type == ViolationType.UNSUPPORTED_TEMPORAL_CLAIM for v in val_res.violations)
