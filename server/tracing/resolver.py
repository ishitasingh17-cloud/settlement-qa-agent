"""
server/tracing/resolver.py

Deterministic reference resolution logic for PS-8 (Phase 3).
Performs exact-matching lookups and prefix detection across the 5 supported identifier types.
Consumes Phase 2 DataStore.
"""

from typing import Optional, Tuple, Union
from server.tracing.models import IdentifierType
from server.tracing.exceptions import (
    InvalidQueryError,
    UnsupportedIdentifierTypeError,
)


def validate_and_normalize_query(
    query_value: Optional[str],
    identifier_type: Optional[Union[IdentifierType, str]] = None,
) -> Tuple[str, IdentifierType, bool]:
    """
    Validates input query string and normalizes identifier type.
    Returns (cleaned_query_value, resolved_identifier_type, auto_detected_flag).
    Raises InvalidQueryError or UnsupportedIdentifierTypeError if invalid.
    """
    if query_value is None:
        raise InvalidQueryError("Query identifier cannot be None.")

    if not isinstance(query_value, str):
        raise InvalidQueryError(f"Query identifier must be a string, got {type(query_value).__name__}.")

    cleaned_value = query_value.strip()
    if not cleaned_value:
        raise InvalidQueryError("Query identifier cannot be empty or whitespace-only.")

    auto_detected = False

    if identifier_type is not None:
        if isinstance(identifier_type, IdentifierType):
            resolved_type = identifier_type
        elif isinstance(identifier_type, str):
            try:
                resolved_type = IdentifierType(identifier_type)
            except ValueError:
                raise UnsupportedIdentifierTypeError(
                    f"Unsupported identifier type: '{identifier_type}'. Supported types: {[t.value for t in IdentifierType]}",
                    identifier_type=identifier_type,
                )
        else:
            raise UnsupportedIdentifierTypeError(
                f"Invalid identifier_type type: {type(identifier_type).__name__}"
            )
    else:
        # Auto-detect identifier type based on prefix patterns
        detected = detect_identifier_type(cleaned_value)
        if detected is None:
            raise UnsupportedIdentifierTypeError(
                f"Unable to determine identifier type for '{cleaned_value}'. Supported prefixes: pay_, order_, set_, UTR, led_",
                identifier_type=cleaned_value,
            )
        resolved_type = detected
        auto_detected = True

    return cleaned_value, resolved_type, auto_detected


def detect_identifier_type(value: str) -> Optional[IdentifierType]:
    """
    Deterministically detects the identifier type from value prefix.
    Returns None if unrecognized.
    """
    if value.startswith("pay_") and len(value) > 4:
        return IdentifierType.GATEWAY_TRANSACTION_ID
    if value.startswith("order_") and len(value) > 6:
        return IdentifierType.ORDER_ID
    if value.startswith("set_") and len(value) > 4:
        return IdentifierType.SETTLEMENT_ID
    if value.startswith("UTR") and len(value) > 3:
        return IdentifierType.BANK_REFERENCE_NUMBER
    if value.startswith("led_") and len(value) > 4:
        return IdentifierType.LEDGER_ENTRY_ID
    return None
