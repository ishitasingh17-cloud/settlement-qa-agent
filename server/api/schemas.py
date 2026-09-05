"""
server/api/schemas.py

Pydantic request and response schemas for PS-8 Backend Investigation API (Phase 7).
Strictly enforces:
- Explicit distinction between user query and canonical transaction ID
- Full preservation of the VerifiedEvidencePack (VEO) contract
- Zero float precision: Decimal monetary figures
- Actionable error envelopes
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

from server.diagnosis.models import (
    SettlementDiagnosis,
    ConfidenceLevel,
    InvestigationStatus,
)
from server.exceptions.models import ExceptionSeverity
from server.evidence.models import VerifiedEvidencePack
from server.validation.models import ResponseValidationResult


class InvestigationRequest(BaseModel):
    """Request payload for investigating a single transaction by identifier."""
    query: str = Field(
        ...,
        description="Query identifier string (e.g. transaction ID, order ID, settlement ID, UTR, ledger entry ID)"
    )
    query_type: Optional[str] = Field(
        default=None,
        description="Optional explicit identifier type (gateway_transaction_id, order_id, settlement_id, bank_reference_number, ledger_entry_id)"
    )

    model_config = ConfigDict(extra="forbid")


class UnifiedQueryRequest(BaseModel):
    """Universal search request payload supporting ID lookup or date query."""
    query: str = Field(
        ...,
        description="Unified query string: identifier, ISO date (YYYY-MM-DD), or keyword"
    )

    model_config = ConfigDict(extra="forbid")


class ExplanationResponse(BaseModel):
    """
    Dual-channel explanation container.
    In Phase 7, uses deterministic fallback templates based on the verified VEO.
    Phase 8 will integrate generative AI explanation.
    """
    internal_summary: str = Field(
        ...,
        description="Technical, highly factual breakdown for payment operations and support engineers"
    )
    merchant_friendly_response: str = Field(
        ...,
        description="Courteous, safe, non-technical explanation suitable for merchants"
    )
    merchant_explanation: Optional[str] = Field(
        default=None,
        description="Alias for merchant_friendly_response"
    )
    answer: Optional[str] = Field(
        default=None,
        description="Direct answer to user question if asked"
    )
    known_facts: Optional[List[str]] = Field(
        default=None,
        description="Verified facts from evidence"
    )
    inferred_facts: Optional[List[str]] = Field(
        default=None,
        description="Inferred facts from evidence"
    )
    unknown_facts: Optional[List[str]] = Field(
        default=None,
        description="Unknown facts from evidence"
    )
    provider: Optional[str] = Field(
        default=None,
        description="Provider used"
    )
    model: Optional[str] = Field(
        default=None,
        description="Model used"
    )
    validated: bool = Field(
        default=True,
        description="True if explanation adheres strictly to VEO facts"
    )
    validation_result: Optional[ResponseValidationResult] = Field(
        default=None,
        description="Audit result from Phase 9 ResponseValidator"
    )

    model_config = ConfigDict(frozen=True)


class AskQuestionRequest(BaseModel):
    """Request payload for asking a natural-language question about an investigated transaction."""
    identifier: str = Field(..., description="Transaction ID or supported query identifier")
    question: str = Field(..., description="Natural language question about this transaction")
    query_type: Optional[str] = Field(default=None, description="Optional identifier type hint")
    conversation_id: Optional[str] = Field(default=None, description="Optional session conversation ID for multi-turn thread")


class FollowUpRequest(AskQuestionRequest):
    """Alias for AskQuestionRequest adhering to Phase 11 specification."""
    pass


class ResetConversationRequest(BaseModel):
    """Request payload to reset an active conversation thread."""
    conversation_id: str = Field(..., description="Conversation session ID to reset")


class ResetConversationResponse(BaseModel):
    """Response payload for conversation reset."""
    conversation_id: str = Field(..., description="Reset conversation session ID")
    success: bool = Field(default=True, description="True if conversation was reset")
    message: str = Field(default="Conversation reset successfully", description="Status message")


class InvestigationResponse(BaseModel):
    """
    Authoritative investigation API response.
    Packages the complete VerifiedEvidencePack (VEO) alongside deterministic explanations.
    """
    success: bool = Field(default=True, description="True if investigation completed successfully")
    investigation_id: str = Field(..., description="Deterministic unique investigation ID (veo_pay_...)")
    query: str = Field(..., description="Original user query identifier")
    query_type: str = Field(..., description="Resolved identifier type")
    transaction_id: str = Field(..., description="Canonical anchor transaction ID")
    diagnosis: SettlementDiagnosis = Field(..., description="Controlled 11-state settlement diagnosis enum")
    confidence: ConfidenceLevel = Field(..., description="Rule-based confidence rating (HIGH, MEDIUM, LOW)")
    confidence_reason: str = Field(..., description="Heuristic rationale for assigned confidence")
    severity: ExceptionSeverity = Field(..., description="Highest operational severity")
    status: InvestigationStatus = Field(..., description="Operational lifecycle status")
    summary: str = Field(..., description="Deterministic factual summary")
    recommended_next_action: str = Field(..., description="Actionable next step for operations or support")
    evidence_pack: VerifiedEvidencePack = Field(..., description="Full canonical Verified Evidence Pack (VEO)")
    explanation: ExplanationResponse = Field(..., description="Dual-channel operational explanation")
    llm_used: bool = Field(default=False, description="False in Phase 7 (deterministic template fallback used)")

    model_config = ConfigDict(frozen=True)


class SettlementListItem(BaseModel):
    """Summary item for batch settlement listings and exception dashboards."""
    transaction_id: str = Field(..., description="Canonical transaction identifier")
    order_id: Optional[str] = Field(default=None, description="Merchant order ID")
    diagnosis: SettlementDiagnosis = Field(..., description="Settlement diagnosis code")
    confidence: ConfidenceLevel = Field(..., description="Confidence rating")
    status: InvestigationStatus = Field(..., description="Lifecycle status")
    severity: ExceptionSeverity = Field(..., description="Operational severity")
    gross_amount: Optional[Decimal] = Field(default=None, description="Gateway gross amount")
    net_amount: Optional[Decimal] = Field(default=None, description="Bank net settlement amount")
    utr: Optional[str] = Field(default=None, description="Bank UTR reference")
    captured_at: Optional[datetime] = Field(default=None, description="Capture timestamp")
    exception_type: Optional[str] = Field(default=None, description="Primary exception code (ERR_...)")
    summary: Optional[str] = Field(default=None, description="Brief exception summary")
    remediation: Optional[str] = Field(default=None, description="Operational remediation recommendation")

    model_config = ConfigDict(frozen=True)


class BatchInvestigationSummary(BaseModel):
    """Batch investigation results envelope."""
    total_count: int = Field(..., description="Total records matching criteria")
    filtered_count: int = Field(..., description="Returned item count")
    items: List[SettlementListItem] = Field(default_factory=list, description="List of settlement summaries")
    settlements: Optional[List[SettlementListItem]] = Field(default=None, description="Alias for items")

    model_config = ConfigDict(frozen=True)


class ExceptionDashboardSummary(BaseModel):
    """Macro exception metrics and flagged transactions for operations dashboard."""
    total_transactions: int = Field(..., description="Total investigated transactions")
    settled_count: int = Field(..., description="Successfully settled count")
    pending_count: int = Field(..., description="In-flight pending count")
    bank_rejected_count: int = Field(..., description="Bank rejected count")
    amount_mismatch_count: int = Field(..., description="Amount mismatch count")
    missing_bank_count: int = Field(..., description="Missing bank record count")
    missing_ledger_count: int = Field(..., description="Missing ledger record count")
    conflicting_evidence_count: int = Field(..., description="Conflicting evidence count")
    insufficient_evidence_count: int = Field(..., description="Insufficient evidence count")
    actionable_exceptions_count: int = Field(..., description="Total exceptions requiring manual review")
    flagged_transactions: List[SettlementListItem] = Field(
        default_factory=list,
        description="Transactions requiring operational triage"
    )
    total_exceptions: Optional[int] = Field(default=None, description="Total exceptional transactions")
    critical_count: Optional[int] = Field(default=None, description="Critical severity exceptions")
    error_count: Optional[int] = Field(default=None, description="Error severity exceptions")
    warning_count: Optional[int] = Field(default=None, description="Warning severity exceptions")
    by_type: Optional[Dict[str, int]] = Field(default=None, description="Exception counts keyed by type")
    by_severity: Optional[Dict[str, int]] = Field(default=None, description="Exception counts keyed by severity")
    exceptions: Optional[List[SettlementListItem]] = Field(default=None, description="Alias for flagged_transactions")

    model_config = ConfigDict(frozen=True)


class ErrorResponse(BaseModel):
    """Standardized error envelope for API errors."""
    error: str = Field(..., description="Machine-readable error code")
    error_code: Optional[str] = Field(default=None, description="Alias for error")
    message: str = Field(..., description="Human-readable explanation of error")
    status_code: Optional[int] = Field(default=None, description="HTTP status code")
    details: Optional[Any] = Field(default=None, description="Contextual validation details if applicable")

    model_config = ConfigDict(frozen=True)
