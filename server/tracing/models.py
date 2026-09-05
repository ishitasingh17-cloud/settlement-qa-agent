"""
server/tracing/models.py

Pydantic models for PS-8 Settlement Q&A Agent Reference Resolution & Tracing (Phase 3).
Represents queries, resolution paths, and factual trace results.
Adheres strictly to docs/rules.md:
- Deterministic, serializable models
- Preserves raw and canonical domain entities without modification
- Does NOT perform financial reconciliation or state diagnosis
- Distinguishes missing downstream records from orphan upstream records
"""

from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

from server.models.domain import GatewayRecord, BankRecord, LedgerRecord


class IdentifierType(str, Enum):
    """Supported query identifier types for transaction tracing."""
    GATEWAY_TRANSACTION_ID = "gateway_transaction_id"
    ORDER_ID = "order_id"
    SETTLEMENT_ID = "settlement_id"
    BANK_REFERENCE_NUMBER = "bank_reference_number"
    LEDGER_ENTRY_ID = "ledger_entry_id"


class TraceQuery(BaseModel):
    """Represents the validated input query to the trace engine."""
    identifier_value: str = Field(..., description="The query identifier string")
    identifier_type: IdentifierType = Field(..., description="The resolved or provided identifier type")
    auto_detected: bool = Field(default=False, description="True if identifier type was inferred from prefix/pattern")

    model_config = ConfigDict(frozen=True)


class ResolutionStep(BaseModel):
    """An individual hop/step in the reference resolution traversal."""
    step_number: int = Field(..., description="Sequential 1-indexed hop count")
    from_entity: str = Field(..., description="Source entity/stage (e.g. 'QUERY', 'GATEWAY', 'BANK', 'LEDGER')")
    to_entity: str = Field(..., description="Destination entity/stage (e.g. 'GATEWAY', 'BANK', 'LEDGER', 'PRIMARY_KEY')")
    lookup_key: str = Field(..., description="Index key field used for the lookup")
    lookup_value: str = Field(..., description="Value used to query the index")
    matched: bool = Field(..., description="True if a corresponding record was found in the index")
    description: str = Field(..., description="Human-readable description of this resolution hop")

    model_config = ConfigDict(frozen=True)


class ResolutionPath(BaseModel):
    """Complete provenance of the graph traversal steps used to resolve the trace."""
    steps: List[ResolutionStep] = Field(default_factory=list, description="Ordered resolution steps")
    resolved_gateway_transaction_id: Optional[str] = Field(default=None, description="Resolved cross-system anchor ID")
    path_summary: str = Field(..., description="Summary string of the traversal route (e.g. 'order_id -> Gateway -> gateway_transaction_id -> Bank, Ledger')")

    model_config = ConfigDict(frozen=True)


class TraceResult(BaseModel):
    """
    Factual result of reference resolution and cross-system record retrieval.
    Phase 3 boundary:
    - Contains factual presence/absence of records
    - Contains linkage and graph traversal evidence
    - Contains source provenance
    - Does NOT contain financial reconciliation calculations
    - Does NOT contain settlement state diagnoses
    """
    query: TraceQuery = Field(..., description="The original query specification")
    resolution: ResolutionPath = Field(..., description="Audit path of how records were resolved")
    resolved_gateway_transaction_id: Optional[str] = Field(default=None, description="Anchor transaction ID connecting records")
    gateway_record: Optional[GatewayRecord] = Field(default=None, description="Associated Gateway record if present")
    bank_record: Optional[BankRecord] = Field(default=None, description="Associated Bank record if present")
    ledger_record: Optional[LedgerRecord] = Field(default=None, description="Associated Ledger record if present")
    records_found: List[Literal["GATEWAY", "BANK", "LEDGER"]] = Field(default_factory=list, description="Systems where records exist")
    missing_records: List[Literal["GATEWAY", "BANK", "LEDGER"]] = Field(default_factory=list, description="Expected systems where records were not found")
    is_complete_chain: bool = Field(..., description="True if records were found in all 3 systems (Gateway, Bank, Ledger)")
    is_orphan: bool = Field(..., description="True if Bank or Ledger records exist while Gateway record is absent")
    has_conflicting_statuses: bool = Field(default=False, description="Factual flag indicating if present records have differing statuses. Does not diagnose root cause.")
    is_duplicate: bool = Field(default=False, description="Factual flag indicating if duplicate records were detected.")

    model_config = ConfigDict(frozen=True)
