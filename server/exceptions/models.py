"""
server/exceptions/models.py

Pydantic models for PS-8 Settlement Q&A Agent Exception Engine & Epistemic Honesty (Phase 5).
Defines exception taxonomy, severity, physical evidence references, and the Tri-State Epistemic Model.
Adheres strictly to docs/rules.md and docs/prd.md:
- Deterministic, serializable models
- Strict separation between facts (directly observed), inferences (logically derived), and unknowns (data silent)
- Preserves raw evidence references without attributing unverified causes
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class ExceptionType(str, Enum):
    """
    Standardized exception taxonomy for settlement discrepancies.
    Matches Section 6.1 of docs/prd.md and Section 8 of prompt.
    """
    STATUS_MISMATCH = "ERR_STATUS_MISMATCH"
    AMOUNT_MISMATCH = "ERR_AMOUNT_MISMATCH"
    MISSING_BANK = "ERR_MISSING_BANK"
    MISSING_LEDGER = "ERR_MISSING_LEDGER"
    MISSING_GATEWAY = "ERR_MISSING_GATEWAY"
    REFERENCE_MISMATCH = "ERR_REFERENCE_MISMATCH"
    DUPLICATE_RECORD = "ERR_DUPLICATE_RECORD"
    CONFLICTING_EVIDENCE = "ERR_CONFLICTING_EVIDENCE"
    BANK_REJECTION = "ERR_BANK_REJECTION"
    GATEWAY_FAILURE = "ERR_GATEWAY_FAILURE"
    UNBATCHED_SETTLEMENT = "INFO_UNBATCHED"
    NONE = "NONE"


class ExceptionSeverity(str, Enum):
    """Severity classification for operational exceptions."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class EvidenceReference(BaseModel):
    """
    Traceable reference linking a diagnostic finding directly back to physical source evidence.
    Guarantees that every conclusion can be traced to system, file, and 1-based CSV line number.
    """
    source_system: Literal["GATEWAY", "BANK", "LEDGER"] = Field(
        ...,
        description="Originating financial system"
    )
    record_id: str = Field(
        ...,
        description="System primary or anchor identifier (e.g. pay_..., set_..., led_...)"
    )
    field_name: str = Field(
        ...,
        description="Entity attribute name supporting the finding"
    )
    field_value: str = Field(
        ...,
        description="Observed string representation of the attribute value"
    )
    source_file: str = Field(
        ...,
        description="Physical CSV source filename"
    )
    source_row_index: int = Field(
        ...,
        description="1-based physical CSV line number, including header"
    )

    model_config = ConfigDict(frozen=True)


class EpistemicBreakdown(BaseModel):
    """
    Tri-State Epistemic Model separating verified knowledge from speculation.
    Matches Section 7.1 of docs/prd.md and Section 10 of prompt:
    - KNOWN: Directly provable from source records.
    - INFERRED: Logically derived from multiple verified facts.
    - UNKNOWN: Data is absent or silent; explicitly stated as unrecorded.
    """
    known_facts: List[str] = Field(
        default_factory=list,
        description="Factual observations directly extracted from source records"
    )
    inferences: List[str] = Field(
        default_factory=list,
        description="Deterministic conclusions derived from comparing multiple verified facts"
    )
    unknowns: List[str] = Field(
        default_factory=list,
        description="Questions or causes that cannot be established from the available evidence"
    )

    @property
    def inferred_facts(self) -> List[str]:
        return self.inferences

    @property
    def unknown_facts(self) -> List[str]:
        return self.unknowns

    model_config = ConfigDict(frozen=True)


class SettlementException(BaseModel):
    """
    Represents an individual operational exception detected during investigation.
    Preserves multiple simultaneous exceptions rather than discarding secondary anomalies.
    """
    exception_type: ExceptionType = Field(
        ...,
        description="Standardized discrepancy classification code"
    )
    severity: ExceptionSeverity = Field(
        ...,
        description="Operational impact severity"
    )
    message: str = Field(
        ...,
        description="Deterministic factual explanation of the exception condition"
    )
    affected_fields: List[str] = Field(
        default_factory=list,
        description="Specific entity field names involved in the anomaly"
    )
    conflicting_values: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Factual values from conflicting records, or None if not applicable"
    )
    remediation: Optional[str] = Field(
        default=None,
        description="Operational recommendation for resolving this specific exception"
    )

    model_config = ConfigDict(frozen=True)
