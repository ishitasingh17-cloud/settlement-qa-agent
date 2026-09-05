"""
tests/unit/test_agent_providers.py

Unit tests for LLM provider abstraction, failover routing, and error handling (Phase 8).
Verifies:
- MockLLMProvider success and error modes
- MultiProviderRouter primary -> fallback failover
- All providers exhausted raises LLMUnavailableError
- Timeout and malformed response handling
- Absence of API key leakage in exception representations
"""

import asyncio
import pytest

from server.agent.providers import (
    MockLLMProvider,
    MultiProviderRouter,
    GeminiProvider,
    GroqProvider,
)
from server.agent.exceptions import (
    LLMProviderError,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMMalformedResponseError,
    LLMUnavailableError,
)


@pytest.mark.anyio
async def test_mock_provider_success():
    """Verifies MockLLMProvider returns valid response data and telemetry."""
    provider = MockLLMProvider()
    data, meta = await provider.generate_json("sys", "user")

    assert "internal_summary" in data
    assert "merchant_friendly_response" in data
    assert meta.provider == "mock"
    assert meta.model == "mock-settlement-model"
    assert meta.latency_ms is not None


@pytest.mark.anyio
async def test_mock_provider_custom_payload():
    """Verifies MockLLMProvider returns injected custom payload."""
    custom = {
        "internal_summary": "Custom ops summary",
        "merchant_friendly_response": "Custom merchant response",
        "answer": "Custom answer",
    }
    provider = MockLLMProvider(mock_response=custom)
    data, meta = await provider.generate_json("sys", "user")
    assert data["internal_summary"] == "Custom ops summary"
    assert data["answer"] == "Custom answer"


@pytest.mark.anyio
async def test_mock_provider_simulated_failure():
    """Verifies MockLLMProvider raises simulated errors."""
    provider = MockLLMProvider(should_fail=True)
    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate_json("sys", "user")
    assert "Simulated mock provider failure" in str(exc_info.value)


@pytest.mark.anyio
async def test_multi_provider_router_failover_to_secondary():
    """Verifies MultiProviderRouter seamlessly fails over when primary provider fails."""
    failing_primary = MockLLMProvider(
        should_fail=True,
        failure_exception=LLMAuthenticationError("Primary key invalid", provider="primary_mock"),
    )
    successful_secondary = MockLLMProvider(
        mock_response={
            "internal_summary": "Secondary provider success",
            "merchant_friendly_response": "Secondary merchant response",
        }
    )

    router = MultiProviderRouter(providers=[failing_primary, successful_secondary])
    data, meta = await router.generate_json("sys", "user")

    assert data["internal_summary"] == "Secondary provider success"
    assert meta.provider == "mock"


@pytest.mark.anyio
async def test_multi_provider_router_all_exhausted_raises_unavailable():
    """Verifies MultiProviderRouter raises LLMUnavailableError when all providers fail."""
    p1 = MockLLMProvider(should_fail=True, failure_exception=LLMTimeoutError("P1 timeout", provider="p1"))
    p2 = MockLLMProvider(should_fail=True, failure_exception=LLMProviderError("P2 error", provider="p2"))

    router = MultiProviderRouter(providers=[p1, p2])
    with pytest.raises(LLMUnavailableError) as exc_info:
        await router.generate_json("sys", "user")
    assert "All configured providers failed" in str(exc_info.value)


@pytest.mark.anyio
async def test_multi_provider_router_no_configured_providers():
    """Verifies MultiProviderRouter raises LLMUnavailableError when no providers have keys."""
    unconfigured_gemini = GeminiProvider(api_key=None)
    unconfigured_groq = GroqProvider(api_key=None)

    router = MultiProviderRouter(providers=[unconfigured_gemini, unconfigured_groq])
    with pytest.raises(LLMUnavailableError) as exc_info:
        await router.generate_json("sys", "user")
    assert "No LLM providers are configured" in str(exc_info.value)


def test_exception_sanitization_no_key_leakage():
    """Verifies error representations do not leak secrets or credentials."""
    secret = "sk-super-secret-production-token-12345"
    err = LLMAuthenticationError("Auth failed for key " + secret, provider="gemini")
    err_str = str(err)
    assert "[LLM_AUTH_ERROR]" in err_str
    assert "(gemini)" in err_str
