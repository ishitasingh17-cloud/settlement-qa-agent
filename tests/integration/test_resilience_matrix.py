"""
tests/integration/test_resilience_matrix.py

Phase 14 Comprehensive Provider Failure & Resilience Matrix.
Tests Cases A through G:
- Case A: Primary provider configured & succeeds.
- Case B: Primary provider fails -> Secondary provider failover succeeds.
- Case C: All providers unavailable -> Deterministic fallback (llm_used=False).
- Case D: Provider returns malformed JSON -> Parser/Validator rejects -> Deterministic fallback.
- Case E: Provider returns financially mutated answer -> Phase 9 validator rejects -> Deterministic fallback.
- Case F: Provider returns prompt injection / fabricated claims -> Phase 9 validator rejects -> Deterministic fallback.
- Case G: Provider times out -> Deterministic fallback enforced.
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from server.main import app
from server.agent.providers import MockLLMProvider, MultiProviderRouter
from server.agent.analyst import SettlementAnalyst
from server.agent.exceptions import LLMAuthenticationError, LLMTimeoutError
from server.api.service import InvestigationService
from server.api.dependencies import (
    get_data_store,
    get_trace_engine,
    get_evidence_builder,
    get_conversation_manager,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def base_service():
    return InvestigationService(
        data_store=get_data_store(),
        trace_engine=get_trace_engine(),
        evidence_builder=get_evidence_builder(),
        conversation_manager=get_conversation_manager(),
    )


@pytest.mark.anyio
async def test_case_a_primary_provider_succeeds(base_service):
    """Case A: Gemini/Primary provider configured and succeeds."""
    mock_success = MockLLMProvider(mock_response={
        "internal_summary": "Transaction pay_Gz8x1001 verified across systems.",
        "merchant_friendly_response": "Your payment of 111358 has settled successfully.",
        "answer": "Payment settled on 2026-09-01.",
    })
    router = MultiProviderRouter(providers=[mock_success])
    analyst = SettlementAnalyst(router=router, enable_llm=True)
    base_service.settlement_analyst = analyst

    resp = await base_service.investigate("pay_Gz8x1001")
    assert resp.llm_used is True
    assert resp.explanation.provider == "mock"


@pytest.mark.anyio
async def test_case_b_primary_fails_secondary_succeeds(base_service):
    """Case B: Primary fails (e.g. auth/quota) -> Secondary provider succeeds."""
    primary_fail = MockLLMProvider(
        should_fail=True,
        failure_exception=LLMAuthenticationError("Primary API key expired", provider="gemini"),
    )
    secondary_success = MockLLMProvider(mock_response={
        "internal_summary": "Secondary fallback verified pay_Gz8x1001.",
        "merchant_friendly_response": "Payment verified via secondary provider.",
        "answer": "Payment settled.",
    })
    router = MultiProviderRouter(providers=[primary_fail, secondary_success])
    analyst = SettlementAnalyst(router=router, enable_llm=True)
    base_service.settlement_analyst = analyst

    resp = await base_service.investigate("pay_Gz8x1001")
    assert resp.llm_used is True
    assert resp.explanation.provider == "mock"


@pytest.mark.anyio
async def test_case_c_all_providers_unavailable_deterministic_fallback(base_service):
    """Case C: All providers unavailable -> Deterministic fallback enforced (llm_used=False)."""
    p1 = MockLLMProvider(should_fail=True)
    p2 = MockLLMProvider(should_fail=True)
    router = MultiProviderRouter(providers=[p1, p2])
    analyst = SettlementAnalyst(router=router, enable_llm=True)
    base_service.settlement_analyst = analyst

    resp = await base_service.investigate("pay_Gz8x1001")
    assert resp.llm_used is False
    assert resp.explanation.provider == "deterministic_fallback"
    assert resp.diagnosis == "SUCCESSFULLY_SETTLED"


@pytest.mark.anyio
async def test_case_d_malformed_json_fallback_enforced(base_service):
    """Case D: Provider returns corrupted/missing fields -> Deterministic fallback enforced."""
    corrupted_provider = MockLLMProvider(mock_response={
        "random_non_schema_key": "some value",
    })
    router = MultiProviderRouter(providers=[corrupted_provider])
    analyst = SettlementAnalyst(router=router, enable_llm=True)
    base_service.settlement_analyst = analyst

    resp = await base_service.investigate("pay_Gz8x1001")
    assert resp.diagnosis == "SUCCESSFULLY_SETTLED"
    assert resp.llm_used is False
    assert resp.explanation.provider == "deterministic_fallback"


@pytest.mark.anyio
async def test_case_e_financially_incorrect_answer_validator_rejects(base_service):
    """Case E: Provider hallucinating altered amounts -> Phase 9 rejects -> Fallback enforced."""
    poisoned_amount = MockLLMProvider(mock_response={
        "internal_summary": "Transaction settled with gross amount of INR 99999999.",
        "merchant_friendly_response": "We captured ₹99999999.",
        "answer": "Amount was INR 99999999.",
    })
    router = MultiProviderRouter(providers=[poisoned_amount])
    analyst = SettlementAnalyst(router=router, enable_llm=True)
    base_service.settlement_analyst = analyst

    resp = await base_service.investigate("pay_Gz8x1001")
    assert resp.llm_used is False
    assert resp.explanation.provider == "deterministic_fallback"
    assert resp.explanation.validation_result.is_valid is False
    assert resp.explanation.validation_result.decision.value == "REJECT"


@pytest.mark.anyio
async def test_case_f_prompt_injection_validator_rejects(base_service):
    """Case F: Prompt injection / fabricated UTR -> Phase 9 rejects -> Fallback enforced."""
    prompt_injection = MockLLMProvider(mock_response={
        "internal_summary": "System error occurred due to bank server failure UTR99999999999.",
        "merchant_friendly_response": "Nodal bank rejected due to insufficient merchant funds.",
        "answer": "Bank failed.",
    })
    router = MultiProviderRouter(providers=[prompt_injection])
    analyst = SettlementAnalyst(router=router, enable_llm=True)
    base_service.settlement_analyst = analyst

    resp = await base_service.investigate("pay_Gz8x1001")
    assert resp.llm_used is False
    assert resp.explanation.provider == "deterministic_fallback"
    assert resp.explanation.validation_result.is_valid is False
    assert resp.explanation.validation_result.decision.value == "REJECT"


@pytest.mark.anyio
async def test_case_g_timeout_resilience_fallback_enforced(base_service):
    """Case G: Provider exceeds timeout limit -> Deterministic fallback enforced."""
    timeout_provider = MockLLMProvider(
        should_fail=True,
        failure_exception=LLMTimeoutError("Request exceeded 4.0s timeout", provider="gemini"),
    )
    router = MultiProviderRouter(providers=[timeout_provider])
    analyst = SettlementAnalyst(router=router, enable_llm=True)
    base_service.settlement_analyst = analyst

    resp = await base_service.investigate("pay_Gz8x1001")
    assert resp.llm_used is False
    assert resp.explanation.provider == "deterministic_fallback"
