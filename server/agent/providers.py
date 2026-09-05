"""
server/agent/providers.py

Modular LLM provider abstraction supporting:
- BaseLLMProvider (abstract interface)
- GeminiProvider (Google GenAI SDK 2.19.0)
- GroqProvider (fast inference REST failover via httpx)
- MockLLMProvider (deterministic offline testing)
- MultiProviderRouter (failover orchestration with timeout controls)
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple

import httpx

from server.agent.models import ProviderMetadata
from server.agent.exceptions import (
    LLMProviderError,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMMalformedResponseError,
    LLMUnavailableError,
)
from server.config.settings import settings

logger = logging.getLogger("settlement_qa_agent.llm")


class BaseLLMProvider(ABC):
    """Abstract interface for all LLM providers in PS-8."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. gemini, groq, mock)."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the specific model."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the required API keys or credentials exist."""
        pass

    @abstractmethod
    async def generate_json(
        self,
        system_instruction: str,
        user_content: str,
        timeout_seconds: float = 4.0,
    ) -> Tuple[Dict[str, Any], ProviderMetadata]:
        """
        Executes generation requesting JSON output.
        Returns parsed dictionary alongside telemetry metadata.
        """
        pass


class GeminiProvider(BaseLLMProvider):
    """
    Primary Google Gemini provider using the official modern google.genai SDK.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model = model
        self._client = None
        if self._api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize google.genai Client: {e}")

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        return bool(self._api_key and self._client)

    async def generate_json(
        self,
        system_instruction: str,
        user_content: str,
        timeout_seconds: float = 4.0,
    ) -> Tuple[Dict[str, Any], ProviderMetadata]:
        if not self.is_configured():
            raise LLMAuthenticationError("Gemini API key is not configured.", provider="gemini")

        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.0,
        )

        start_time = time.perf_counter()
        try:
            # Run async call with explicit timeout
            coro = self._client.aio.models.generate_content(
                model=self._model,
                contents=user_content,
                config=config,
            )
            response = await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            raise LLMTimeoutError(
                f"Gemini generation timed out after {timeout_seconds}s.",
                provider="gemini",
                timeout_seconds=timeout_seconds,
            )
        except Exception as e:
            err_str = str(e).lower()
            if "quota" in err_str or "rate" in err_str or "429" in err_str:
                raise LLMRateLimitError(f"Gemini rate limit exceeded: {e}", provider="gemini")
            elif "api_key" in err_str or "permission" in err_str or "403" in err_str or "401" in err_str:
                raise LLMAuthenticationError(f"Gemini authentication failed: {e}", provider="gemini")
            raise LLMProviderError(f"Gemini API call failed: {e}", provider="gemini")

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        text = response.text or ""
        if not text.strip():
            raise LLMMalformedResponseError("Gemini returned empty response text.", provider="gemini")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMMalformedResponseError(f"Failed to parse Gemini JSON: {e}", provider="gemini", raw_content=text)

        metadata = ProviderMetadata(
            provider="gemini",
            model=self._model,
            latency_ms=round(latency_ms, 2),
        )
        return data, metadata


class GroqProvider(BaseLLMProvider):
    """
    Failover Groq provider using high-speed OpenAI-compatible REST completions via httpx.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self._api_key = api_key or settings.GROQ_API_KEY
        self._model = model
        self._url = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def generate_json(
        self,
        system_instruction: str,
        user_content: str,
        timeout_seconds: float = 4.0,
    ) -> Tuple[Dict[str, Any], ProviderMetadata]:
        if not self.is_configured():
            raise LLMAuthenticationError("Groq API key is not configured.", provider="groq")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.post(self._url, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise LLMTimeoutError(
                f"Groq generation timed out after {timeout_seconds}s.",
                provider="groq",
                timeout_seconds=timeout_seconds,
            )
        except Exception as e:
            raise LLMProviderError(f"Groq network connection failed: {e}", provider="groq")

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if resp.status_code in (401, 403):
            raise LLMAuthenticationError(f"Groq authentication rejected ({resp.status_code}).", provider="groq")
        elif resp.status_code == 429:
            raise LLMRateLimitError("Groq rate limit or quota exceeded (429).", provider="groq")
        elif resp.status_code != 200:
            raise LLMProviderError(f"Groq returned HTTP {resp.status_code}: {resp.text}", provider="groq")

        try:
            body = resp.json()
            content = body["choices"][0]["message"]["content"]
            data = json.loads(content)
        except Exception as e:
            raise LLMMalformedResponseError(f"Failed to parse Groq response: {e}", provider="groq", raw_content=resp.text)

        usage = body.get("usage", {})
        metadata = ProviderMetadata(
            provider="groq",
            model=self._model,
            latency_ms=round(latency_ms, 2),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )
        return data, metadata


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic mock provider for offline testing, contract verification, and simulation.
    """
    def __init__(
        self,
        mock_response: Optional[Dict[str, Any]] = None,
        should_fail: bool = False,
        failure_exception: Optional[Exception] = None,
        latency_ms: float = 25.0,
    ):
        self._mock_response = mock_response
        self._should_fail = should_fail
        self._failure_exception = failure_exception
        self._latency_ms = latency_ms

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-settlement-model"

    def is_configured(self) -> bool:
        return True

    async def generate_json(
        self,
        system_instruction: str,
        user_content: str,
        timeout_seconds: float = 4.0,
    ) -> Tuple[Dict[str, Any], ProviderMetadata]:
        if self._should_fail:
            if self._failure_exception:
                raise self._failure_exception
            raise LLMProviderError("Simulated mock provider failure.", provider="mock")

        if self._mock_response is not None:
            data = dict(self._mock_response)
        else:
            # Generate sensible mock output matching schema
            data = {
                "internal_summary": "Deterministic mock analysis: Transaction verified across systems.",
                "merchant_friendly_response": "Your payment is being processed according to verified records.",
                "answer": "This is a verified mock answer based strictly on evidence.",
                "known_facts": ["Payment record verified."],
                "inferred_facts": ["Settlement lifecycle is standard."],
                "unknown_facts": ["No external unrecorded causes."],
            }

        metadata = ProviderMetadata(
            provider="mock",
            model="mock-settlement-model",
            latency_ms=self._latency_ms,
        )
        return data, metadata


class MultiProviderRouter:
    """
    Manages primary and fallback provider routing.
    Attempts primary configured provider; on failure, smoothly falls over to secondary.
    If all configured providers fail or none are configured, raises LLMUnavailableError.
    """
    def __init__(self, providers: Optional[List[BaseLLMProvider]] = None):
        if providers is not None:
            self._providers = providers
        else:
            # Default production hierarchy: Gemini primary, Groq fallback
            self._providers = [
                GeminiProvider(),
                GroqProvider(),
            ]

    @property
    def providers(self) -> List[BaseLLMProvider]:
        return list(self._providers)

    def has_configured_provider(self) -> bool:
        """Returns True if at least one provider has active credentials."""
        return any(p.is_configured() for p in self._providers)

    async def generate_json(
        self,
        system_instruction: str,
        user_content: str,
        timeout_seconds: float = 4.0,
    ) -> Tuple[Dict[str, Any], ProviderMetadata]:
        errors = []
        configured_providers = [p for p in self._providers if p.is_configured()]

        if not configured_providers:
            raise LLMUnavailableError("No LLM providers are configured with API credentials.")

        for provider in configured_providers:
            try:
                logger.info(f"Attempting LLM generation via {provider.provider_name} ({provider.model_name})...")
                data, meta = await provider.generate_json(
                    system_instruction=system_instruction,
                    user_content=user_content,
                    timeout_seconds=timeout_seconds,
                )
                return data, meta
            except LLMProviderError as e:
                logger.warning(f"Provider {provider.provider_name} failed: {e}. Attempting next configured provider...")
                errors.append(f"{provider.provider_name}: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error from provider {provider.provider_name}: {e}")
                errors.append(f"{provider.provider_name}: {e}")

        all_errors = "; ".join(errors)
        raise LLMUnavailableError(f"All configured providers failed ({all_errors}).")
