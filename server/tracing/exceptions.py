"""
server/tracing/exceptions.py

Structured exceptions for PS-8 reference resolution and transaction tracing (Phase 3).
Adheres strictly to docs/rules.md:
- Structured exception hierarchy
- No internal stack trace or path exposure in public messages
- Explicit error codes and diagnostic metadata
"""

from typing import Optional


class TracingError(Exception):
    """Base exception for all tracing engine failures."""
    def __init__(self, message: str, error_code: str = "TRACING_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class InvalidQueryError(TracingError):
    """Raised when a query is empty, whitespace-only, or structurally invalid."""
    def __init__(self, message: str, query_value: Optional[str] = None):
        super().__init__(message, error_code="INVALID_QUERY")
        self.query_value = query_value


class UnsupportedIdentifierTypeError(TracingError):
    """Raised when an identifier type is unsupported or cannot be determined."""
    def __init__(self, message: str, identifier_type: Optional[str] = None):
        super().__init__(message, error_code="UNSUPPORTED_IDENTIFIER_TYPE")
        self.identifier_type = identifier_type


class TransactionNotFoundError(TracingError):
    """Raised when an identifier is valid in format but does not match any record."""
    def __init__(self, message: str, query_value: str, identifier_type: Optional[str] = None):
        super().__init__(message, error_code="TRANSACTION_NOT_FOUND")
        self.query_value = query_value
        self.identifier_type = identifier_type


class AmbiguousIdentifierError(TracingError):
    """Raised when an identifier matches multiple conflicting records."""
    def __init__(self, message: str, query_value: str, match_count: int):
        super().__init__(message, error_code="AMBIGUOUS_IDENTIFIER")
        self.query_value = query_value
        self.match_count = match_count


# Aliases for architectural naming conventions
TraceEngineException = TracingError
TransactionNotFoundException = TransactionNotFoundError
InvalidQueryException = InvalidQueryError
UnsupportedIdentifierTypeException = UnsupportedIdentifierTypeError
AmbiguousIdentifierException = AmbiguousIdentifierError
