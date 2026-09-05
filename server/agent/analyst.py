"""
server/agent/analyst.py

AI Settlement Analyst service for PS-8 (Phase 8 & 11).
Synthesizes dual-channel natural language explanations (Internal Support + Merchant-Friendly)
and answers conversational follow-up inquiries strictly bounded by the Verified Evidence Pack (VEO).
Integrated with Phase 9 ResponseValidator and Phase 11 multi-turn conversation context.
"""

import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal

from server.evidence.models import VerifiedEvidencePack
from server.diagnosis.models import SettlementDiagnosis
from server.agent.models import AIAnalystRequest, AIAnalystResponse
from server.agent.providers import MultiProviderRouter, LLMProviderError
from server.agent.prompts import build_analyst_prompt, PROMPT_VERSION
from server.validation.validator import ResponseValidator
from server.models.conversation import ChatMessage

logger = logging.getLogger("settlement_qa_agent.analyst")


class SettlementAnalyst:
    """
    Financial Explanation & Q&A Generation service.
    Translates canonical VEOs into structured, dual-channel explanations.
    Guarantees that financial facts never contradict the VEO.
    """

    def __init__(
        self,
        router: Optional[MultiProviderRouter] = None,
        enable_llm: bool = True,
        timeout_seconds: float = 4.0,
        validator: Optional[ResponseValidator] = None,
    ):
        self._router = router or MultiProviderRouter()
        self._enable_llm = enable_llm
        self._timeout_seconds = timeout_seconds
        self._validator = validator or ResponseValidator()

    @property
    def validator(self) -> ResponseValidator:
        return self._validator

    async def explain(self, evidence_pack: VerifiedEvidencePack) -> AIAnalystResponse:
        """
        Generates standard dual-channel explanations (internal + merchant) for an investigated transaction.
        If LLM is disabled, unconfigured, fails, or fails validation, gracefully falls back to deterministic templates.
        """
        return await self._generate_explanation(evidence_pack=evidence_pack, question=None)

    async def answer_question(self, request: AIAnalystRequest) -> AIAnalystResponse:
        """
        Answers a specific natural-language user question grounded strictly in the supplied VEO.
        Supports multi-turn conversational context while keeping VEO as the sole financial authority.
        If LLM is unavailable or fails validation, returns deterministic fallback explicitly addressing the diagnosis.
        """
        return await self._generate_explanation(
            evidence_pack=request.evidence_pack,
            question=request.question,
            query_identifier=request.query_identifier,
            history=request.history,
            conversation_id=request.conversation_id,
        )

    async def _generate_explanation(
        self,
        evidence_pack: VerifiedEvidencePack,
        question: Optional[str] = None,
        query_identifier: Optional[str] = None,
        history: Optional[List[ChatMessage]] = None,
        conversation_id: Optional[str] = None,
    ) -> AIAnalystResponse:
        """Internal execution flow with Phase 9 ResponseValidator and deterministic fallback guardrail."""
        
        # 1. Check if LLM is enabled and configured
        if self._enable_llm and self._router.has_configured_provider():
            system_instruction, user_content = build_analyst_prompt(
                evidence_pack,
                question=question,
                history=history,
            )
            try:
                raw_json, meta = await self._router.generate_json(
                    system_instruction=system_instruction,
                    user_content=user_content,
                    timeout_seconds=self._timeout_seconds,
                )
                candidate = self._parse_llm_response(
                    raw_json,
                    meta,
                    evidence_pack,
                    question=question,
                    conversation_id=conversation_id,
                )
                
                # Phase 9: Algorithmic Post-Generation Safety Validation
                val_result = self._validator.validate(candidate, evidence_pack)
                if val_result.is_valid:
                    logger.info(f"AI response successfully passed Phase 9 validation (Decision: {val_result.decision.value}).")
                    return candidate.model_copy(update={"validation_result": val_result, "validated": True})
                else:
                    logger.warning(
                        f"Phase 9 ResponseValidator REJECTED AI response: {len(val_result.violations)} violation(s). "
                        f"Violations: {[v.description for v in val_result.violations]}. "
                        f"Safely substituting deterministic fallback template."
                    )
                    fallback = self._build_deterministic_fallback(
                        evidence_pack,
                        question=question,
                        conversation_id=conversation_id,
                    )
                    return fallback.model_copy(update={"validation_result": val_result, "validated": True})

            except LLMProviderError as e:
                logger.warning(f"LLM generation failed ({e}). Falling back to deterministic explanation.")
            except Exception as e:
                logger.error(f"Unexpected error during LLM generation ({e}). Falling back to deterministic explanation.")

        # 2. Deterministic Fallback Flow (llm_used=False)
        fallback = self._build_deterministic_fallback(
            evidence_pack,
            question=question,
            conversation_id=conversation_id,
        )
        val_result = self._validator.validate(fallback, evidence_pack)
        return fallback.model_copy(update={"validation_result": val_result, "validated": True})

    def _parse_llm_response(
        self,
        data: Dict[str, Any],
        meta: Any,
        veo: VerifiedEvidencePack,
        question: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AIAnalystResponse:
        """
        Strictly parses model JSON output.
        Fills missing fields safely from VEO epistemic facts if model omitted them.
        """
        internal = str(data.get("internal_summary") or "").strip()
        merchant = str(data.get("merchant_friendly_response") or "").strip()
        answer = data.get("answer")
        if answer is not None:
            answer = str(answer).strip()

        # If model returned empty explanations, reject and fallback
        if not internal or not merchant:
            logger.warning("Model JSON lacked non-empty internal or merchant explanation. Falling back.")
            return self._build_deterministic_fallback(veo, question=question, conversation_id=conversation_id)

        # Epistemic facts: extract or fallback to VEO breakdown
        known_facts = data.get("known_facts")
        if not isinstance(known_facts, list) or not known_facts:
            known_facts = list(veo.epistemic_model.known_facts)
        else:
            known_facts = [str(k) for k in known_facts]

        inferred_facts = data.get("inferred_facts")
        if not isinstance(inferred_facts, list):
            inferred_facts = list(veo.epistemic_model.inferences)
        else:
            inferred_facts = [str(i) for i in inferred_facts]

        unknown_facts = data.get("unknown_facts")
        if not isinstance(unknown_facts, list) or not unknown_facts:
            unknown_facts = list(veo.epistemic_model.unknowns)
        else:
            unknown_facts = [str(u) for u in unknown_facts]

        return AIAnalystResponse(
            internal_summary=internal,
            merchant_friendly_response=merchant,
            merchant_explanation=merchant,
            answer=answer,
            known_facts=known_facts,
            inferred_facts=inferred_facts,
            unknown_facts=unknown_facts,
            llm_used=True,
            provider=meta.provider,
            model=meta.model,
            prompt_version=PROMPT_VERSION,
            validated=True,
            conversation_id=conversation_id,
        )

    def _build_deterministic_fallback(
        self,
        veo: VerifiedEvidencePack,
        question: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AIAnalystResponse:
        """
        Constructs a safe, deterministic template explanation directly derived from VEO facts.
        Always available even when providers are disabled, offline, timed out, or rejected by validator.
        """
        diag = veo.diagnosis
        gw_status = veo.gateway.status if veo.gateway.present else "missing"
        bk_status = veo.bank.settlement_status if veo.bank.present else "missing"
        lg_status = veo.ledger.entry_type if veo.ledger.present else "missing"
        
        # Exact amounts as formatted strings
        gross = f"{veo.gateway.currency} {veo.gateway.gross_amount}" if veo.gateway.present else "None"
        net = f"INR {veo.bank.net_settlement_amount}" if veo.bank.present else "None"
        
        internal = (
            f"Deterministic diagnosis is {diag.value}. "
            f"Gateway status is {gw_status} (Gross: {gross}), "
            f"Bank status is {bk_status}, Ledger status is {lg_status}. "
            f"Evidence completeness confidence is {veo.confidence.value} ({veo.confidence_reason})."
        )
        
        # Construct merchant friendly message based on diagnosis
        if diag == SettlementDiagnosis.SUCCESSFULLY_SETTLED:
            utr = f" Bank reference number (UTR): {veo.bank.bank_reference_number}." if (veo.bank.present and veo.bank.bank_reference_number) else ""
            merchant = f"Your payment for order {veo.gateway.order_id or veo.transaction_id} is successfully settled and confirmed.{utr}"
        elif diag == SettlementDiagnosis.SETTLEMENT_PENDING:
            merchant = f"Your payment for order {veo.gateway.order_id or veo.transaction_id} was successfully received and is currently processing through bank clearing rails."
        elif diag == SettlementDiagnosis.BANK_REJECTED:
            reason = f" Reason provided: {veo.bank.settlement_status}." if veo.bank.present else ""
            merchant = f"The settlement for order {veo.gateway.order_id or veo.transaction_id} was rejected by the clearing bank.{reason} Please contact merchant operations for resolution."
        elif diag == SettlementDiagnosis.GATEWAY_FAILED:
            merchant = f"The payment for order {veo.gateway.order_id or veo.transaction_id} could not be authorized. No funds were collected."
        elif diag == SettlementDiagnosis.AMOUNT_MISMATCH:
            merchant = f"A settlement amount variance was detected for order {veo.gateway.order_id or veo.transaction_id}. Our finance team is reviewing the disbursement records."
        elif diag == SettlementDiagnosis.MISSING_BANK_RECORD:
            merchant = f"Your payment of {gross} for order {veo.gateway.order_id or veo.transaction_id} was received. Bank nodal clearing confirmation is currently pending in clearing files."
        elif diag == SettlementDiagnosis.MISSING_LEDGER_RECORD:
            merchant = f"Your payment for order {veo.gateway.order_id or veo.transaction_id} was processed on banking rails. Internal journal entry booking is undergoing routine reconciliation."
        elif diag == SettlementDiagnosis.CONFLICTING_EVIDENCE:
            merchant = f"Payment records for order {veo.gateway.order_id or veo.transaction_id} show cross-system reporting differences. A manual review has been initiated to ensure accurate payout."
        elif diag == SettlementDiagnosis.INSUFFICIENT_EVIDENCE:
            merchant = f"We are currently consolidating upstream payment records for transaction reference {veo.transaction_id}. Support has flagged this for operational verification."
        else:
            merchant = f"The transaction {veo.transaction_id} is currently under investigation with operational status {diag.value}."

        answer = None
        if question:
            # Deterministic answer strictly grounded in VEO facts
            answer = (
                f"According to verified system records, the transaction diagnosis is {diag.value}. "
                f"{merchant} (Note: Detailed natural-language Q&A is currently operating in deterministic fallback mode.)"
            )

        return AIAnalystResponse(
            internal_summary=internal,
            merchant_friendly_response=merchant,
            merchant_explanation=merchant,
            answer=answer,
            known_facts=list(veo.epistemic_model.known_facts),
            inferred_facts=list(veo.epistemic_model.inferences),
            unknown_facts=list(veo.epistemic_model.unknowns),
            llm_used=False,
            provider="deterministic_fallback",
            model="deterministic_template",
            prompt_version=PROMPT_VERSION,
            validated=True,
            conversation_id=conversation_id,
        )
