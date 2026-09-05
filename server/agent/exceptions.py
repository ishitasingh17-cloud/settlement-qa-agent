"""
server/agent/exceptions.py

Structured exceptions for AI Settlement Analyst and provider failures.
Adheres to docs/rules.md:
- Explicit error codes and diagnostic metadata
- No secret or API key leakage in exception strings
- Safe fallback categorization
"""

from typing import Optional


class LLMProviderError(Exception):
    """Base exception for all LLM provider failures."""
    def __init__(self, message: str, provider: str = "unknown", error_code: str = "LLM_ERROR"):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.error_code = error_code

    def __str__(self) -> str:
        return f"[{self.error_code}] ({self.provider}): {self.message}"


class LLMAuthenticationError(LLMProviderError):
    """Raised when provider credentials are missing, rejected, or expired."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, provider=provider, error_code="LLM_AUTH_ERROR")


class LLMTimeoutError(LLMProviderError):
    """Raised when provider request exceeds configured timeout window."""
    def __init__(self, message: str, provider: str = "unknown", timeout_seconds: Optional[float] = None):
        super().__init__(message, provider=provider, error_code="LLM_TIMEOUT")
        self.timeout_seconds = timeout_seconds


class LLMRateLimitError(LLMProviderError):
    """Raised when provider rate limit / quota is exhausted."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, provider=provider, error_code="LLM_RATE_LIMIT")


class LLMMalformedResponseError(LLMProviderError):
    """Raised when provider returns unparseable, empty, or schema-invalid content."""
    def __init__(self, message: str, provider: str = "unknown", raw_content: Optional[str] = None):
        super().__init__(message, provider=provider, error_code="LLM_MALFORMED_RESPONSE")
        self.raw_content = raw_content


class LLMUnavailableError(LLMProviderError):
    """Raised when all configured providers have failed or none are available."""
    def __init__(self, message: str = "All configured LLM providers are unavailable."):
        super().__init__(message, provider="all", error_code="LLM_UNAVAILABLE")
