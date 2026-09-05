"""
server/api/service.py

Orchestration service for PS-8 Backend Investigation API (Phase 7).
Coordinates:
  Query Resolution -> TraceEngine -> ReconciliationEngine -> DiagnosisEngine -> EvidencePackBuilder
Constructs VerifiedEvidencePack (VEO) and wraps it with deterministic dual-channel explanations.
Strictly adheres to:
- No duplicated diagnosis or reconciliation logic
- Complete preservation of the VEO contract
- Pure Decimal monetary precision
- Deterministic execution with zero external AI calls
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union, List

from server.ingestion.data_store import DataStore
from server.tracing.models import IdentifierType
from server.tracing.trace_engine import TraceEngine
from server.tracing.exceptions import (
    TraceEngineException,
    TransactionNotFoundException,
    InvalidQueryException,
    UnsupportedIdentifierTypeException,
    AmbiguousIdentifierException,
)
from server.evidence.builder import EvidencePackBuilder
from server.evidence.models import VerifiedEvidencePack
from server.evidence.exceptions import EvidencePackError, EvidenceIntegrityError
from server.diagnosis.models import SettlementDiagnosis, InvestigationStatus
from server.api.schemas import (
    InvestigationResponse,
    ExplanationResponse,
    SettlementListItem,
    BatchInvestigationSummary,
    ExceptionDashboardSummary,
)
from server.agent.models import AIAnalystRequest, AIAnalystResponse
from server.agent.analyst import SettlementAnalyst
from server.agent.conversation import ConversationManager

logger = logging.getLogger("settlement_qa_agent.api")


class InvestigationService:
    """
    Orchestration service exposing the deterministic investigation pipeline to the API transport layer.
    Integrates the AI Settlement Analyst for natural-language explanations with deterministic fallback.
    """

    def __init__(
        self,
        data_store: DataStore,
        trace_engine: TraceEngine,
        evidence_builder: EvidencePackBuilder,
        settlement_analyst: Optional[SettlementAnalyst] = None,
        conversation_manager: Optional[ConversationManager] = None,
    ):
        self.data_store = data_store
        self.trace_engine = trace_engine
        self.evidence_builder = evidence_builder
        self.settlement_analyst = settlement_analyst
        self.conversation_manager = conversation_manager or ConversationManager()

    async def investigate(
        self,
        query: str,
        query_type: Optional[str] = None,
    ) -> InvestigationResponse:
        """
        Executes an end-to-end investigation for a query identifier.
        1. Validates query input
        2. Resolves and traces records across Gateway, Bank, and Ledger
        3. Reconciles and diagnoses transaction state deterministically
        4. Assembles canonical VerifiedEvidencePack (VEO)
        5. Formats grounded explanation (AI Analyst if available, else deterministic template)
        """
        clean_query = query.strip() if query else ""
        if not clean_query:
            raise InvalidQueryException("Investigation query cannot be empty or whitespace.")

        # Map optional query_type string to IdentifierType enum
        id_type = None
        if query_type:
            try:
                id_type = IdentifierType(query_type)
            except ValueError:
                valid_types = [t.value for t in IdentifierType]
                raise UnsupportedIdentifierTypeException(
                    f"Unsupported query_type '{query_type}'. Supported types: {valid_types}"
                )

        # 1. Execute deterministic trace (Phases 2-3)
        trace = self.trace_engine.trace(clean_query, id_type)

        # 2. Build canonical VerifiedEvidencePack (Phases 4-6)
        veo = self.evidence_builder.build(trace)

        # 3. Format explanation via AI Settlement Analyst (or fallback)
        if self.settlement_analyst:
            ai_resp = await self.settlement_analyst.explain(veo)
            explanation = ExplanationResponse(
                internal_summary=ai_resp.internal_summary,
                merchant_friendly_response=ai_resp.merchant_friendly_response,
                merchant_explanation=ai_resp.merchant_explanation,
                validated=ai_resp.validated,
                validation_result=ai_resp.validation_result,
                answer=ai_resp.answer,
                known_facts=ai_resp.known_facts,
                inferred_facts=ai_resp.inferred_facts,
                unknown_facts=ai_resp.unknown_facts,
                provider=ai_resp.provider,
                model=ai_resp.model,
            )
            llm_used = ai_resp.llm_used
        else:
            explanation = self._build_deterministic_explanation(veo)
            llm_used = False

        return InvestigationResponse(
            success=True,
            investigation_id=veo.veo_id,
            query=clean_query,
            query_type=veo.query_type,
            transaction_id=veo.transaction_id,
            diagnosis=veo.diagnosis,
            confidence=veo.confidence,
            confidence_reason=veo.confidence_reason,
            severity=veo.severity,
            status=veo.status,
            summary=veo.summary,
            recommended_next_action=veo.recommended_next_action,
            evidence_pack=veo,
            explanation=explanation,
            llm_used=llm_used,
        )

    async def ask_question(
        self,
        identifier: str,
        question: str,
        query_type: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AIAnalystResponse:
        """
        Executes a targeted natural-language Q&A inquiry grounded strictly in the verified VEO.
        Maintains conversational continuity across multiple turns while preserving VEO authority.
        Enforces Context Isolation: switching identifiers isolates/resets the conversation context.
        """
        clean_id = identifier.strip() if identifier else ""
        if not clean_id:
            raise InvalidQueryException("Investigation query identifier cannot be empty.")
        clean_q = question.strip() if question else ""
        if not clean_q:
            raise InvalidQueryException("Question cannot be empty.")

        id_type = None
        if query_type:
            try:
                id_type = IdentifierType(query_type)
            except ValueError:
                valid_types = [t.value for t in IdentifierType]
                raise UnsupportedIdentifierTypeException(
                    f"Unsupported query_type '{query_type}'. Supported types: {valid_types}"
                )

        trace = self.trace_engine.trace(clean_id, id_type)
        veo = self.evidence_builder.build(trace)

        # Retrieve or initialize conversation context (enforces context isolation)
        conv = self.conversation_manager.get_or_create(
            conversation_id=conversation_id,
            transaction_id=veo.transaction_id,
            investigation_id=veo.veo_id,
        )

        # Record user message turn in session
        self.conversation_manager.add_user_message(conv.conversation_id, clean_q)

        req = AIAnalystRequest(
            evidence_pack=veo,
            question=clean_q,
            query_identifier=clean_id,
            conversation_id=conv.conversation_id,
            history=conv.messages,
        )

        analyst = self.settlement_analyst or SettlementAnalyst(enable_llm=False)
        analyst_resp = await analyst.answer_question(req)

        # Record assistant answer turn in session
        msg_text = analyst_resp.answer or analyst_resp.internal_summary
        asst_msg = self.conversation_manager.add_assistant_message(
            conversation_id=conv.conversation_id,
            content=msg_text,
            validated=analyst_resp.validated,
            llm_used=analyst_resp.llm_used,
            is_fallback=(analyst_resp.provider == "deterministic_fallback"),
            validation_result=analyst_resp.validation_result,
        )

        return analyst_resp.model_copy(
            update={
                "conversation_id": conv.conversation_id,
                "message_id": asst_msg.message_id,
            }
        )

    def reset_conversation(self, conversation_id: str) -> bool:
        """Resets messages in an active conversation session."""
        return self.conversation_manager.reset(conversation_id)

    async def query(self, query_str: str) -> Union[InvestigationResponse, BatchInvestigationSummary]:
        """
        Unified search endpoint:
        - If query matches a date format (YYYY-MM-DD or DD-MM-YYYY), returns batch settlements for that date.
        - Otherwise, performs a single transaction investigation.
        """
        clean_query = query_str.strip() if query_str else ""
        if not clean_query:
            raise InvalidQueryException("Query string cannot be empty.")

        # Check if query is a date pattern
        is_date = False
        for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
            try:
                datetime.strptime(clean_query, fmt)
                is_date = True
                break
            except ValueError:
                continue

        if is_date:
            return self.list_settlements(date=clean_query)
        else:
            return await self.investigate(clean_query)

    def list_settlements(
        self,
        date: Optional[str] = None,
        status: Optional[str] = None,
    ) -> BatchInvestigationSummary:
        """
        Returns batch settlement listings across loaded transactions, optionally filtered by date or status.
        """
        all_txns = sorted(list(self.data_store.get_all_transaction_ids()))
        items: List[SettlementListItem] = []

        # Optional date filter validation
        clean_date = date.strip() if date else None
        if clean_date:
            try:
                datetime.strptime(clean_date, "%Y-%m-%d")
            except ValueError:
                raise InvalidQueryException(f"Invalid date format '{date}'. Expected YYYY-MM-DD.")

        for txn_id in all_txns:
            trace = self.trace_engine.trace(txn_id)
            gw = trace.gateway_record
            bnk = trace.bank_record
            led = trace.ledger_record

            # Optional date filter: checks if any recorded timestamp matches date string
            if clean_date:
                date_match = False
                if gw and gw.created_at and clean_date == gw.created_at.strftime("%Y-%m-%d"):
                    date_match = True
                elif bnk and bnk.settled_at and clean_date == bnk.settled_at.strftime("%Y-%m-%d"):
                    date_match = True
                elif led and led.booked_at and clean_date == led.booked_at.strftime("%Y-%m-%d"):
                    date_match = True
                if not date_match:
                    continue

            # Build item summary
            veo = self.evidence_builder.build(trace)

            # Optional status filter
            if status and status.upper() != veo.diagnosis.value and status.upper() != veo.status.value:
                continue

            items.append(
                SettlementListItem(
                    transaction_id=txn_id,
                    order_id=gw.order_id if gw else None,
                    diagnosis=veo.diagnosis,
                    confidence=veo.confidence,
                    status=veo.status,
                    severity=veo.severity,
                    gross_amount=gw.gross_amount if gw else None,
                    net_amount=bnk.net_settlement_amount if bnk else None,
                    utr=bnk.bank_reference_number if bnk else None,
                    captured_at=gw.created_at if gw else None,
                )
            )

        return BatchInvestigationSummary(
            total_count=len(all_txns),
            filtered_count=len(items),
            items=items,
            settlements=items,
        )

    def get_exceptions_dashboard(
        self,
        date: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
    ) -> ExceptionDashboardSummary:
        """
        Aggregates macro exception statistics across all transactions in dataset.
        Identifies all transactions requiring operational triage with optional date/severity/status filtering.
        """
        clean_date = None
        if date:
            clean_date = date.strip()
            try:
                datetime.strptime(clean_date, "%Y-%m-%d")
            except ValueError:
                raise InvalidQueryException(f"Invalid date format '{date}'. Expected YYYY-MM-DD.")

        all_txns = sorted(list(self.data_store.get_all_transaction_ids()))
        
        settled_count = 0
        pending_count = 0
        bank_rejected_count = 0
        amount_mismatch_count = 0
        missing_bank_count = 0
        missing_ledger_count = 0
        conflicting_evidence_count = 0
        insufficient_evidence_count = 0
        flagged_items: List[SettlementListItem] = []
        matching_total = 0

        for txn_id in all_txns:
            trace = self.trace_engine.trace(txn_id)
            gw = trace.gateway_record
            bnk = trace.bank_record
            led = trace.ledger_record

            # Date filtering: check if any recorded system timestamp matches the query date
            if clean_date:
                date_match = False
                if gw and gw.created_at and clean_date == gw.created_at.strftime("%Y-%m-%d"):
                    date_match = True
                elif bnk and bnk.settled_at and clean_date == bnk.settled_at.strftime("%Y-%m-%d"):
                    date_match = True
                elif led and led.booked_at and clean_date == led.booked_at.strftime("%Y-%m-%d"):
                    date_match = True
                if not date_match:
                    continue

            matching_total += 1
            veo = self.evidence_builder.build(trace)
            diag = veo.diagnosis

            if diag == SettlementDiagnosis.SUCCESSFULLY_SETTLED:
                settled_count += 1
            elif diag == SettlementDiagnosis.SETTLEMENT_PENDING:
                pending_count += 1
            elif diag == SettlementDiagnosis.BANK_REJECTED:
                bank_rejected_count += 1
            elif diag == SettlementDiagnosis.AMOUNT_MISMATCH:
                amount_mismatch_count += 1
            elif diag == SettlementDiagnosis.MISSING_BANK_RECORD:
                missing_bank_count += 1
            elif diag == SettlementDiagnosis.MISSING_LEDGER_RECORD:
                missing_ledger_count += 1
            elif diag == SettlementDiagnosis.CONFLICTING_EVIDENCE:
                conflicting_evidence_count += 1
            elif diag == SettlementDiagnosis.INSUFFICIENT_EVIDENCE:
                insufficient_evidence_count += 1

            # If not successfully settled, check severity and status filters
            if diag != SettlementDiagnosis.SUCCESSFULLY_SETTLED:
                if severity:
                    req_sev = severity.upper()
                    if req_sev in ("HIGH", "ERROR"):
                        if veo.severity.value not in ("HIGH", "ERROR"):
                            continue
                    elif req_sev in ("MEDIUM", "LOW", "WARNING"):
                        if veo.severity.value not in ("MEDIUM", "LOW", "WARNING"):
                            continue
                    elif veo.severity.value != req_sev:
                        continue
                if status and veo.status.value != status.upper() and veo.diagnosis.value != status.upper():
                    continue

                primary_exc = veo.exceptions[0] if veo.exceptions else None
                flagged_items.append(
                    SettlementListItem(
                        transaction_id=txn_id,
                        order_id=gw.order_id if gw else None,
                        diagnosis=veo.diagnosis,
                        confidence=veo.confidence,
                        status=veo.status,
                        severity=veo.severity,
                        gross_amount=gw.gross_amount if gw else None,
                        net_amount=bnk.net_settlement_amount if bnk else None,
                        utr=bnk.bank_reference_number if bnk else None,
                        captured_at=gw.created_at if gw else None,
                        exception_type=primary_exc.exception_type.value if primary_exc else None,
                        summary=veo.summary,
                        remediation=primary_exc.remediation if primary_exc else veo.recommended_next_action,
                    )
                )

        actionable = len(flagged_items)
        critical_count = conflicting_evidence_count + insufficient_evidence_count
        error_count = bank_rejected_count + amount_mismatch_count + missing_bank_count
        warning_count = missing_ledger_count + pending_count
        by_type = {
            "SETTLEMENT_PENDING": pending_count,
            "BANK_REJECTED": bank_rejected_count,
            "AMOUNT_MISMATCH": amount_mismatch_count,
            "MISSING_BANK_RECORD": missing_bank_count,
            "MISSING_LEDGER_RECORD": missing_ledger_count,
            "CONFLICTING_EVIDENCE": conflicting_evidence_count,
            "INSUFFICIENT_EVIDENCE": insufficient_evidence_count,
        }
        by_severity = {
            "CRITICAL": critical_count,
            "ERROR": error_count,
            "WARNING": warning_count,
        }
        return ExceptionDashboardSummary(
            total_transactions=matching_total,
            settled_count=settled_count,
            pending_count=pending_count,
            bank_rejected_count=bank_rejected_count,
            amount_mismatch_count=amount_mismatch_count,
            missing_bank_count=missing_bank_count,
            missing_ledger_count=missing_ledger_count,
            conflicting_evidence_count=conflicting_evidence_count,
            insufficient_evidence_count=insufficient_evidence_count,
            actionable_exceptions_count=actionable,
            flagged_transactions=flagged_items,
            total_exceptions=actionable,
            critical_count=critical_count,
            error_count=error_count,
            warning_count=warning_count,
            by_type=by_type,
            by_severity=by_severity,
            exceptions=flagged_items,
        )

    def _build_deterministic_explanation(self, veo: VerifiedEvidencePack) -> ExplanationResponse:
        """
        Builds deterministic dual-channel explanations adhering to arch.md Section 10.1:
        - internal_summary: technical, mentioning exact IDs and states
        - merchant_friendly_response: courteous, safe, non-technical
        """
        # Internal Ops Summary
        gw_status = veo.gateway.status or "MISSING"
        gw_amt = f"INR {veo.gateway.gross_amount}" if veo.gateway.gross_amount is not None else "N/A"
        bnk_status = veo.bank.settlement_status or "MISSING"
        led_status = veo.ledger.entry_type or "MISSING"
        internal_summary = (
            f"Deterministic diagnosis is {veo.diagnosis.value}. "
            f"Gateway status is {gw_status} (Gross: {gw_amt}), "
            f"Bank status is {bnk_status}, "
            f"Ledger status is {led_status}. "
            f"Evidence completeness confidence is {veo.confidence.value} ({veo.confidence_reason})."
        )

        # Merchant Friendly Response
        order_ref = veo.gateway.order_id or veo.transaction_id
        if veo.diagnosis == SettlementDiagnosis.SUCCESSFULLY_SETTLED:
            merchant_response = (
                f"Your payment for order {order_ref} is successfully settled and confirmed. "
                f"Bank reference number (UTR): {veo.bank.bank_reference_number}."
            )
        elif veo.diagnosis == SettlementDiagnosis.SETTLEMENT_PENDING:
            merchant_response = (
                f"Your payment for order {order_ref} is in progress. Funds were captured and clearing "
                f"is actively pending within the standard banking window."
            )
        elif veo.diagnosis == SettlementDiagnosis.GATEWAY_FAILED:
            err_msg = veo.gateway.error_description or "declined by card issuer"
            merchant_response = (
                f"Your payment checkout attempt for order {order_ref} was not successful ({err_msg}). "
                f"No funds were debited, and no merchant settlement is due."
            )
        elif veo.diagnosis == SettlementDiagnosis.BANK_REJECTED:
            merchant_response = (
                f"Disbursement for order {order_ref} was rejected by the clearing bank. "
                f"Our operations team is re-verifying merchant bank account details to initiate a payout retry."
            )
        else:
            merchant_response = (
                f"Your transaction {veo.transaction_id} is currently under operational review. "
                f"Next step: {veo.recommended_next_action}"
            )

        return ExplanationResponse(
            internal_summary=internal_summary,
            merchant_friendly_response=merchant_response,
            merchant_explanation=merchant_response,
            validated=True,
        )
