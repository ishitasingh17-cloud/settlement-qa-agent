"""
server/tracing

PS-8 Settlement Q&A Agent Reference Resolution & Transaction Trace Engine (Phase 3).
"""

from server.tracing.models import (
    IdentifierType,
    TraceQuery,
    ResolutionStep,
    ResolutionPath,
    TraceResult,
)
from server.tracing.exceptions import (
    TracingError,
    InvalidQueryError,
    UnsupportedIdentifierTypeError,
    TransactionNotFoundError,
    AmbiguousIdentifierError,
)
from server.tracing.trace_engine import TraceEngine, trace_transaction
from server.tracing.resolver import detect_identifier_type, validate_and_normalize_query

__all__ = [
    "IdentifierType",
    "TraceQuery",
    "ResolutionStep",
    "ResolutionPath",
    "TraceResult",
    "TracingError",
    "InvalidQueryError",
    "UnsupportedIdentifierTypeError",
    "TransactionNotFoundError",
    "AmbiguousIdentifierError",
    "TraceEngine",
    "trace_transaction",
    "detect_identifier_type",
    "validate_and_normalize_query",
]
