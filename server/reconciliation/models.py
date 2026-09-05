"""
server/reconciliation/models.py

Pydantic models for PS-8 Settlement Q&A Agent Deterministic Reconciliation (Phase 4).
Establishes financial comparison facts across Gateway, Bank, and Ledger records.
Adheres strictly to docs/rules.md:
- Deterministic, serializable models
- Pure Decimal arithmetic, zero float representation
- Explicit distinction between differing financial semantics (gross vs net) and actual mismatches
- Never manufactures zero amounts for missing evidence (uses None and MISSING_EVIDENCE)
- Preserves raw status evidence without assigning root-cause diagnosis (Phase 5 boundary)
"""

from enum import Enum
from decimal import Decimal
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class BankLedgerComparisonStatus(str, Enum):
    """Status of direct monetary comparison between Bank net settlement and Ledger amount."""
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    NOT_COMPARABLE = "NOT_COMPARABLE"


class GatewayBankComparisonStatus(str, Enum):
    """
    Status of monetary comparison between Gateway gross and Bank net.
    Crucial: Gross and Net represent distinct financial semantics.
    A numeric variance does NOT constitute an unexplained amount mismatch,
    and numerical equality does NOT constitute financial reconciliation.
    """
    NOT_COMPARABLE_GROSS_VS_NET = "NOT_COMPARABLE_GROSS_VS_NET"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    NOT_COMPARABLE = "NOT_COMPARABLE"


class StatusConsistencyStatus(str, Enum):
    """Factual cross-system status consistency state."""
    CONSISTENT = "CONSISTENT"
    CONFLICT = "CONFLICT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class BankLedgerComparison(BaseModel):
    """Direct comparison between Bank net settlement disbursement and Ledger booking."""
    bank_net_settlement_amount: Optional[Decimal] = Field(
        default=None,
        description="Bank net disbursement amount in Decimal, or None if missing"
    )
    ledger_amount: Optional[Decimal] = Field(
        default=None,
        description="Internal ledger booking amount in Decimal, or None if missing"
    )
    status: BankLedgerComparisonStatus = Field(
        ...,
        description="Deterministic comparison result (MATCH, MISMATCH, MISSING_EVIDENCE)"
    )
    numeric_difference: Optional[Decimal] = Field(
        default=None,
        description="Exact Decimal difference (bank - ledger), 0 if matched, None if missing"
    )
    is_match: bool = Field(
        default=False,
        description="True strictly when both records exist and amounts match exactly"
    )
    message: str = Field(
        ...,
        description="Factual explanation of comparison result"
    )

    model_config = ConfigDict(frozen=True)


class GatewayBankComparison(BaseModel):
    """
    Semantic comparison between Gateway gross amount and Bank net disbursement.
    Preserves gross vs net semantic distinction without inferring fees or errors.
    """
    gateway_gross_amount: Optional[Decimal] = Field(
        default=None,
        description="Gateway gross transaction amount in Decimal, or None if missing"
    )
    bank_net_settlement_amount: Optional[Decimal] = Field(
        default=None,
        description="Bank net disbursement amount in Decimal, or None if missing"
    )
    status: GatewayBankComparisonStatus = Field(
        ...,
        description="Comparison state preserving gross vs net semantics"
    )
    gross_minus_net_variance: Optional[Decimal] = Field(
        default=None,
        description="Raw arithmetic difference (gross - net) as a factual number, or None"
    )
    message: str = Field(
        ...,
        description="Factual note documenting gross vs net semantics and lack of fee schedule"
    )

    model_config = ConfigDict(frozen=True)


class StatusComparison(BaseModel):
    """Factual cross-system status alignment audit."""
    gateway_status: Optional[str] = Field(default=None, description="Raw normalized gateway status")
    bank_status: Optional[str] = Field(default=None, description="Raw normalized bank settlement status")
    ledger_entry_type: Optional[str] = Field(default=None, description="Raw normalized ledger entry type")
    status_consistency: StatusConsistencyStatus = Field(..., description="Overall consistency category")
    is_consistent: bool = Field(..., description="True if no contradictory statuses are detected")
    has_conflict: bool = Field(..., description="True if statuses directly contradict each other")
    conflict_details: Optional[str] = Field(default=None, description="Specific factual contradiction details")
    message: str = Field(..., description="Summary of status consistency audit")

    model_config = ConfigDict(frozen=True)


class ReconciliationResult(BaseModel):
    """
    Structured, deterministic financial reconciliation result for an investigated transaction.
    Phase 4 boundary:
    - Answers: what records exist, what values match, what values differ, are statuses aligned
    - Does NOT answer: why was settlement delayed, what is the root cause diagnosis
    - Does NOT perform LLM text synthesis or UI presentation
    """
    transaction_id: Optional[str] = Field(
        default=None,
        description="Anchor transaction ID or query identifier"
    )
    gateway_present: bool = Field(..., description="True if Gateway record exists")
    bank_present: bool = Field(..., description="True if Bank record exists")
    ledger_present: bool = Field(..., description="True if Ledger record exists")
    evidence_complete: bool = Field(..., description="True if records exist in all 3 systems")
    missing_evidence: List[Literal["GATEWAY", "BANK", "LEDGER"]] = Field(
        default_factory=list,
        description="Systems where records are absent"
    )
    is_orphan: bool = Field(
        ...,
        description="True if Bank or Ledger exists while Gateway record is absent"
    )
    gateway_gross_amount: Optional[Decimal] = Field(
        default=None,
        description="Gross amount from Gateway, or None if absent"
    )
    bank_net_settlement_amount: Optional[Decimal] = Field(
        default=None,
        description="Net settlement disbursement amount from Bank, or None if absent"
    )
    ledger_amount: Optional[Decimal] = Field(
        default=None,
        description="Booked amount from Ledger, or None if absent"
    )
    bank_ledger_comparison: BankLedgerComparison = Field(
        ...,
        description="Audit between Bank net disbursement and Ledger booking"
    )
    gateway_bank_comparison: GatewayBankComparison = Field(
        ...,
        description="Audit between Gateway gross amount and Bank net disbursement"
    )
    status_comparison: StatusComparison = Field(
        ...,
        description="Audit of cross-system status consistency"
    )
    currency: Optional[str] = Field(
        default="INR",
        description="Three-letter currency code established by present records"
    )
    provenance_sources: List[str] = Field(
        default_factory=list,
        description="Systems contributing verified evidence"
    )

    model_config = ConfigDict(frozen=True)
