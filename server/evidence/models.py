"""
server/evidence/models.py

Pydantic models for PS-8 Verified Evidence Pack (VEO) (Phase 6).
The canonical, immutable data structure packaging all verified evidence from Phases 2-5:
- Raw/canonical records across Gateway, Bank, and Ledger
- Reconciliation facts and mathematical comparisons
- Controlled 11-state settlement diagnosis
- Tri-State Epistemic Model (KNOWN, INFERRED, UNKNOWN)
- Physical evidence references with 1-based CSV line numbers
- Chronological multi-system event timeline
- Cryptographic integrity fingerprint (SHA-256)

Adheres strictly to docs/arch.md Section 9.1 and docs/rules.md:
- Zero floats: pure Decimal representations
- Immutable, frozen models
- Deterministic serialization
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

from server.models.domain import GatewayRecord, BankRecord, LedgerRecord, SourceProvenance
from server.tracing.models import ResolutionPath
from server.reconciliation.models import (
    BankLedgerComparisonStatus,
    GatewayBankComparisonStatus,
    StatusConsistencyStatus,
)
from server.diagnosis.models import (
    SettlementDiagnosis,
    ConfidenceLevel,
    InvestigationStatus,
)
from server.exceptions.models import (
    ExceptionSeverity,
    SettlementException,
    EpistemicBreakdown,
    EvidenceReference,
)


class TimelineEvent(BaseModel):
    """
    An individual chronological event in the multi-system transaction lifecycle.
    """
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO-8601 UTC timestamp string, or 'PENDING', or 'UNRECORDED'"
    )
    system: Literal["GATEWAY", "BANK", "LEDGER", "SYSTEM"] = Field(
        ...,
        description="Originating system of this event"
    )
    event: str = Field(..., description="Short factual title of event")
    details: Optional[str] = Field(default=None, description="Detailed description of the event")
    source_row_index: Optional[int] = Field(
        default=None,
        description="1-based physical CSV line number, or None if synthetic/unrecorded"
    )

    model_config = ConfigDict(frozen=True)


class GatewayEvidence(BaseModel):
    """
    Gateway transaction evidence packaging.
    Contains both flattened attributes for immediate consumer access and the full domain record.
    """
    present: bool = Field(..., description="True if Gateway record exists in dataset")
    transaction_id: Optional[str] = Field(default=None, description="Gateway transaction ID (e.g. pay_...)")
    order_id: Optional[str] = Field(default=None, description="Merchant order ID")
    gross_amount: Optional[Decimal] = Field(default=None, description="Gross captured amount in Decimal, or None")
    currency: Optional[str] = Field(default="INR", description="Currency code")
    method: Optional[str] = Field(default=None, description="Payment method (upi, card, netbanking)")
    status: Optional[str] = Field(default=None, description="Gateway status (captured, failed)")
    error_code: Optional[str] = Field(default=None, description="Gateway error code if failed")
    error_description: Optional[str] = Field(default=None, description="Gateway decline reason description")
    captured_at: Optional[datetime] = Field(default=None, description="Normalized payment capture timestamp")
    provenance: Optional[SourceProvenance] = Field(default=None, description="Physical file and 1-based row index")
    record: Optional[GatewayRecord] = Field(default=None, description="Full canonical Gateway domain record")

    model_config = ConfigDict(frozen=True)


class BankEvidence(BaseModel):
    """
    Bank clearing file evidence packaging.
    Contains both flattened attributes for immediate consumer access and the full domain record.
    """
    present: bool = Field(..., description="True if Bank record exists in dataset")
    settlement_id: Optional[str] = Field(default=None, description="Bank settlement ID (e.g. set_...)")
    gateway_transaction_id: Optional[str] = Field(default=None, description="Cross-system linked gateway transaction ID")
    net_settlement_amount: Optional[Decimal] = Field(default=None, description="Net disbursement amount in Decimal, or None")
    bank_reference_number: Optional[str] = Field(default=None, description="Bank UTR / reference number")
    settlement_status: Optional[str] = Field(default=None, description="Bank settlement status (processed, failed, pending)")
    settled_at: Optional[datetime] = Field(default=None, description="Settlement disbursement timestamp if recorded")
    provenance: Optional[SourceProvenance] = Field(default=None, description="Physical file and 1-based row index")
    record: Optional[BankRecord] = Field(default=None, description="Full canonical Bank domain record")

    model_config = ConfigDict(frozen=True)


class LedgerEvidence(BaseModel):
    """
    Internal accounting ledger evidence packaging.
    Contains both flattened attributes for immediate consumer access and the full domain record.
    """
    present: bool = Field(..., description="True if Ledger record exists in dataset")
    ledger_entry_id: Optional[str] = Field(default=None, description="Ledger journal entry ID (e.g. led_...)")
    gateway_transaction_id: Optional[str] = Field(default=None, description="Cross-system linked gateway transaction ID")
    account_type: Optional[str] = Field(default=None, description="Ledger account type (e.g. merchant_payout_pool)")
    entry_type: Optional[str] = Field(default=None, description="Journal entry type (credit, debit)")
    ledger_amount: Optional[Decimal] = Field(default=None, description="Booked entry amount in Decimal, or None")
    booked_at: Optional[datetime] = Field(default=None, description="Accounting posting timestamp")
    provenance: Optional[SourceProvenance] = Field(default=None, description="Physical file and 1-based row index")
    record: Optional[LedgerRecord] = Field(default=None, description="Full canonical Ledger domain record")

    model_config = ConfigDict(frozen=True)


class ReconciliationSummary(BaseModel):
    """
    Reconciliation findings packaging.
    Answers mathematical and status agreement without diagnosing root cause.
    """
    bank_ledger_match: bool = Field(..., description="True if Bank net disbursement matches Ledger booked amount exactly")
    bank_ledger_status: BankLedgerComparisonStatus = Field(..., description="Deterministic comparison status (MATCH, MISMATCH, MISSING_EVIDENCE)")
    bank_ledger_numeric_diff: Optional[Decimal] = Field(default=None, description="Exact Decimal variance (bank - ledger)")
    gateway_bank_status: GatewayBankComparisonStatus = Field(..., description="Gross vs Net comparison status (NOT_COMPARABLE_GROSS_VS_NET)")
    gross_minus_net_variance: Optional[Decimal] = Field(default=None, description="Arithmetic difference (gross - net) as a factual Decimal")
    status_consistency: StatusConsistencyStatus = Field(..., description="Overall status consistency state (CONSISTENT, CONFLICT, INSUFFICIENT_DATA)")
    has_status_conflict: bool = Field(..., description="True if cross-system status contradiction detected")
    conflict_details: Optional[str] = Field(default=None, description="Factual contradiction details if any")
    currency: Optional[str] = Field(default="INR", description="Three-letter currency code")
    provenance_sources: List[str] = Field(default_factory=list, description="Systems contributing verified evidence")

    model_config = ConfigDict(frozen=True)


class VerifiedEvidencePack(BaseModel):
    """
    The canonical Verified Evidence Object (VEO) for PS-8 Settlement Q&A Agent.
    Everything the downstream AI explanation layer and frontend UI are allowed to know
    about an investigated transaction, packaged with complete provenance and cryptographic integrity.
    """
    # Schema Specification & Identity
    schema_version: str = Field(default="1.0.0", description="VEO schema specification version")
    veo_id: str = Field(..., description="Deterministic unique identifier for this evidence pack (e.g. veo_pay_...)")
    transaction_id: str = Field(..., description="Anchor cross-system transaction identifier")
    query_identifier: str = Field(..., description="Original query string supplied to tracer")
    query_type: str = Field(..., description="Identifier type used to initiate investigation")

    # Authoritative Diagnosis (from Phase 5)
    diagnosis: SettlementDiagnosis = Field(..., description="Controlled 11-state settlement diagnosis enum")
    confidence: ConfidenceLevel = Field(..., description="Rule-based confidence rating (HIGH, MEDIUM, LOW)")
    confidence_reason: str = Field(..., description="Deterministic heuristic explanation for confidence rating")
    severity: ExceptionSeverity = Field(..., description="Highest operational severity across detected issues")
    status: InvestigationStatus = Field(..., description="High-level operational lifecycle state")
    summary: str = Field(..., description="Deterministic, factual human-readable investigation summary")
    recommended_next_action: str = Field(..., description="Actionable next step for operations or merchant support")

    # Exceptions & Anomalies (Preserving multiple coexisting issues)
    primary_exception: Optional[SettlementException] = Field(default=None, description="Primary driving operational exception")
    exceptions: List[SettlementException] = Field(default_factory=list, description="All coexisting operational exceptions")

    # Multi-System Financial Evidence
    gateway: GatewayEvidence = Field(..., description="Gateway transaction evidence")
    bank: BankEvidence = Field(..., description="Bank clearing file evidence")
    ledger: LedgerEvidence = Field(..., description="Internal accounting ledger evidence")

    # Reconciliation Facts (from Phase 4)
    reconciliation: ReconciliationSummary = Field(..., description="Reconciliation facts and variance audits")

    # Tri-State Epistemic Model (from Phase 5)
    epistemic_model: EpistemicBreakdown = Field(..., description="Strict separation of KNOWN, INFERRED, and UNKNOWN facts")

    # Graph Traversal & Resolution Provenance (from Phase 3)
    resolution_path: ResolutionPath = Field(..., description="Audit path of entity hops used to link records")
    records_found: List[Literal["GATEWAY", "BANK", "LEDGER"]] = Field(..., description="Systems where records exist")
    missing_records: List[Literal["GATEWAY", "BANK", "LEDGER"]] = Field(..., description="Systems where records are missing")
    is_complete_chain: bool = Field(..., description="True if records exist in all 3 systems")
    is_orphan: bool = Field(..., description="True if Bank or Ledger records exist without Gateway origin")

    # Physical Evidence References (from Phase 5)
    evidence_refs: List[EvidenceReference] = Field(
        default_factory=list,
        description="Physical evidence references with 1-based CSV line numbers"
    )

    # Event Timeline
    timeline: List[TimelineEvent] = Field(
        default_factory=list,
        description="Chronologically ordered multi-system event lifecycle"
    )

    # Cryptographic Integrity
    integrity_hash: str = Field(..., description="Deterministic SHA-256 fingerprint of semantic financial facts")

    model_config = ConfigDict(frozen=True)


# Convenience alias matching architectural terminology
EvidencePack = VerifiedEvidencePack
