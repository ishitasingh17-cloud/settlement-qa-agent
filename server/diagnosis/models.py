"""
server/diagnosis/models.py

Pydantic models for PS-8 Settlement Q&A Agent Deterministic Diagnosis (Phase 5).
Maps cross-system reconciliation and trace evidence into the authoritative 11-state taxonomy.
Adheres strictly to docs/rules.md, docs/prd.md, and docs/arch.md:
- Controlled 11-state settlement classification
- Rule-based confidence scoring (HIGH, MEDIUM, LOW)
- Preserves full provenance and epistemic breakdown
- Serializable, immutable data structures
"""

from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

from server.exceptions.models import (
    ExceptionType,
    ExceptionSeverity,
    SettlementException,
    EpistemicBreakdown,
    EvidenceReference,
)


class SettlementDiagnosis(str, Enum):
    """
    Authoritative controlled 11-state settlement diagnosis taxonomy.
    Matches Section 6.2 of docs/prd.md and Section 7.2 of docs/arch.md.
    """
    SUCCESSFULLY_SETTLED = "SUCCESSFULLY_SETTLED"
    SETTLEMENT_PENDING = "SETTLEMENT_PENDING"
    GATEWAY_FAILED = "GATEWAY_FAILED"
    BANK_REJECTED = "BANK_REJECTED"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    MISSING_BANK_RECORD = "MISSING_BANK_RECORD"
    MISSING_LEDGER_RECORD = "MISSING_LEDGER_RECORD"
    REFERENCE_MISMATCH = "REFERENCE_MISMATCH"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ConfidenceLevel(str, Enum):
    """Deterministic, explainable confidence rating for the diagnosis."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class InvestigationStatus(str, Enum):
    """High-level operational lifecycle state of the investigated transaction."""
    RESOLVED = "RESOLVED"
    PENDING = "PENDING"
    EXCEPTION = "EXCEPTION"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DiagnosisResult(BaseModel):
    """
    Complete, deterministic diagnosis result for an investigated transaction.
    Transforms Phase 3 Tracing and Phase 4 Reconciliation into a defensible operational conclusion.
    """
    transaction_id: str = Field(
        ...,
        description="Resolved transaction or query anchor identifier"
    )
    diagnosis_code: SettlementDiagnosis = Field(
        ...,
        description="Authoritative 11-state settlement classification"
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Rule-based explainable confidence level"
    )
    confidence_reason: str = Field(
        ...,
        description="Deterministic heuristic rationale explaining the assigned confidence"
    )
    severity: ExceptionSeverity = Field(
        ...,
        description="Overall operational severity of the diagnosed condition"
    )
    status: InvestigationStatus = Field(
        ...,
        description="High-level operational investigation state (RESOLVED, PENDING, EXCEPTION, INSUFFICIENT_DATA)"
    )
    summary: str = Field(
        ...,
        description="Defensible, human-readable summary of the settlement state"
    )
    primary_exception: Optional[SettlementException] = Field(
        default=None,
        description="Leading operational exception driving the diagnosis code, or None if resolved"
    )
    exceptions: List[SettlementException] = Field(
        default_factory=list,
        description="All coexisting operational exceptions detected across the records"
    )
    epistemic_facts: EpistemicBreakdown = Field(
        ...,
        description="Strict separation of KNOWN facts, INFERRED conclusions, and UNKNOWN data gaps"
    )
    evidence_refs: List[EvidenceReference] = Field(
        default_factory=list,
        description="Direct physical source references supporting the diagnosis"
    )
    missing_records: List[Literal["GATEWAY", "BANK", "LEDGER"]] = Field(
        default_factory=list,
        description="Systems where required records were absent"
    )
    conflicts: List[str] = Field(
        default_factory=list,
        description="Factual cross-system contradiction statements if detected"
    )
    recommended_next_action: str = Field(
        ...,
        description="Clear, actionable next step for support agents or payment operations"
    )

    model_config = ConfigDict(frozen=True)

    @property
    def exception_type(self) -> ExceptionType:
        """Convenience property returning the primary exception type code."""
        return self.primary_exception.exception_type if self.primary_exception else ExceptionType.NONE

    @property
    def known_facts(self) -> List[str]:
        """Convenience property returning directly verified facts."""
        return self.epistemic_facts.known_facts

    @property
    def inferences(self) -> List[str]:
        """Convenience property returning derived inferences."""
        return self.epistemic_facts.inferences

    @property
    def unknowns(self) -> List[str]:
        """Convenience property returning explicit unrecorded knowledge gaps."""
        return self.epistemic_facts.unknowns
