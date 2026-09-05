"""
server/reconciliation/exceptions.py

Structured exceptions for PS-8 Reconciliation Engine (Phase 4).
Adheres strictly to docs/rules.md:
- Structured exception hierarchy
- No internal stack trace or path exposure in public messages
- Financial discrepancies are data outcomes, not runtime exceptions
"""

from typing import Optional


class ReconciliationError(Exception):
    """Base exception for reconciliation engine runtime failures."""
    def __init__(self, message: str, error_code: str = "RECONCILIATION_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class InvalidTraceResultError(ReconciliationError):
    """Raised when reconciliation is invoked with an invalid or null TraceResult."""
    def __init__(self, message: str):
        super().__init__(message, error_code="INVALID_TRACE_RESULT")
