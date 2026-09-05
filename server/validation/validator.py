"""
server/validation/validator.py

Deterministic AI Response Validation Engine (Phase 9).
Inspects AI Settlement Analyst responses against authoritative VerifiedEvidencePack (VEO).
Enforces:
- Exact Decimal numeric verification (zero floating point conversions)
- Whitelisted identifier verification (no hallucinated IDs or evidence references)
- Controlled diagnosis alignment and drift detection
- Cross-system status contradiction detection
- Epistemic preservation (rejects conversion of UNKNOWN to asserted KNOWN causes)
- Unsupported causal claims (insufficient funds, server outages, fraud allegations)
- Unsupported temporal / ETA promises (tomorrow, within 2 days, etc.)
- Material omission detection on conflicting or failed transactions
"""

import re
import logging
from decimal import Decimal, InvalidOperation
from typing import List, Set, Optional, Dict, Any, Tuple, Union, TYPE_CHECKING

from server.evidence.models import VerifiedEvidencePack
from server.diagnosis.models import SettlementDiagnosis
from server.validation.models import (
    ValidationDecision,
    ViolationType,
    ClaimType,
    ClaimStatus,
    ExtractedClaim,
    ValidationViolation,
    ResponseValidationResult,
)

if TYPE_CHECKING:
    from server.agent.models import AIAnalystResponse

logger = logging.getLogger("settlement_qa_agent.validation")

# Regex patterns for identifiers
ID_PATTERNS = [
    re.compile(r"\b(pay_[A-Za-z0-9_]+)\b"),
    re.compile(r"\b(order_[A-Za-z0-9_]+)\b"),
    re.compile(r"\b(set_[A-Za-z0-9_]+)\b"),
    re.compile(r"\b(led_[A-Za-z0-9_]+)\b"),
    re.compile(r"\b(UTR[A-Za-z0-9_]+)\b"),
    re.compile(r"\b(TXN_[A-Za-z0-9_]+)\b"),
    re.compile(r"\b(ORD_[A-Za-z0-9_]+)\b"),
    re.compile(r"\b(SET_[A-Za-z0-9_]+)\b"),
    re.compile(r"\b(LED_[A-Za-z0-9_]+)\b"),
    re.compile(r"\b(veo_[A-Za-z0-9_]+)\b"),
    re.compile(r"\b(INV_[A-Za-z0-9_]+)\b"),
]

# Explicit reference patterns like 'bank record #999' or 'record number 42'
FABRICATED_REF_PATTERNS = [
    re.compile(r"\b(?:bank record|ledger record|ledger entry|evidence reference|source record|record)\s*(?:#|no\.?|number)\s*([A-Za-z0-9_\-]+)\b", re.IGNORECASE),
]

# Regex for currency / monetary figures
# Captures numbers with currency symbols or standard currency formatting
CURRENCY_PREFIX_PATTERN = re.compile(
    r"(?:INR|Rs\.?|₹|\$)\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\b",
    re.IGNORECASE,
)
CURRENCY_SUFFIX_PATTERN = re.compile(
    r"\b([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:INR|rupees|rs|dollars)\b",
    re.IGNORECASE,
)

# Common speculative causes when failure reason is unrecorded/unknown
SPECULATIVE_REASONS = [
    ("insufficient funds", "insufficient funds"),
    ("low balance", "low account balance"),
    ("server down", "bank server downtime"),
    ("server outage", "bank server outage"),
    ("network timeout", "network timeout"),
    ("system outage", "system outage"),
    ("fraud suspected", "fraud suspicion"),
    ("fraudulent", "fraud allegation"),
    ("invalid account number", "invalid account number"),
    ("invalid ifsc", "invalid IFSC code"),
    ("exceeded limit", "transaction limit exceeded"),
    ("compliance block", "compliance hold"),
]

# Unsupported temporal / future arrival claims (ETAs)
TEMPORAL_PATTERNS = [
    re.compile(r"\b(?:will|should|is going to)\s+(?:settle|arrive|be credited|reach|be refunded|clear)\s+(?:tomorrow|tonight|within \d+ (?:days?|hours?)|by (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b", re.IGNORECASE),
    re.compile(r"\b(?:refund|disbursement|payout|funds?|money)\s+will\s+(?:arrive|settle|be processed|reach)\s+(?:tomorrow|in \d+ days?)\b", re.IGNORECASE),
    re.compile(r"\b(?:arrive|settle)\s+(?:tomorrow|within 2 days|within \d+ days)\b", re.IGNORECASE),
    re.compile(r"\bwill\s+arrive\s+tomorrow\b", re.IGNORECASE),
    re.compile(r"\bwill\s+settle\s+tomorrow\b", re.IGNORECASE),
]


class ResponseValidator:
    """
    Algorithmic Post-Generation Safety Boundary for AI Responses.
    Guarantees that no unsupported financial facts, corrupted amounts, fabricated identifiers,
    unsupported causal reasons, or status contradictions can reach human users.
    """

    def __init__(self, version: str = "1.0.0"):
        self.version = version

    def validate(
        self,
        response: Union["AIAnalystResponse", Dict[str, Any]],
        evidence_pack: VerifiedEvidencePack,
    ) -> ResponseValidationResult:
        """
        Validates an AIAnalystResponse or response dictionary against the authoritative VEO.
        Returns a complete ResponseValidationResult.
        """
        # Extract fields to inspect
        if hasattr(response, "internal_summary"):
            internal_text = str(getattr(response, "internal_summary") or "")
            merchant_text = str(getattr(response, "merchant_friendly_response", None) or getattr(response, "merchant_explanation", None) or "")
            answer_text = str(getattr(response, "answer", None) or "")
            known_facts = [str(k) for k in (getattr(response, "known_facts", None) or [])]
            inferred_facts = [str(i) for i in (getattr(response, "inferred_facts", None) or [])]
            unknown_facts = [str(u) for u in (getattr(response, "unknown_facts", None) or [])]
        elif isinstance(response, dict):
            internal_text = str(response.get("internal_summary") or "")
            merchant_text = str(response.get("merchant_friendly_response") or response.get("merchant_explanation") or "")
            answer_text = str(response.get("answer") or "")
            known_facts = [str(k) for k in response.get("known_facts", [])]
            inferred_facts = [str(i) for i in response.get("inferred_facts", [])]
            unknown_facts = [str(u) for u in response.get("unknown_facts", [])]
        else:
            raise ValueError(f"Unsupported response type: {type(response)}")

        all_texts = [
            ("internal_summary", internal_text),
            ("merchant_friendly_response", merchant_text),
            ("answer", answer_text),
        ]
        combined_text = f"{internal_text} {merchant_text} {answer_text}".strip()

        violations: List[ValidationViolation] = []
        verified_claims: List[str] = []
        unsupported_claims: List[str] = []
        contradictions: List[str] = []
        epistemic_violations: List[str] = []
        numeric_violations: List[str] = []
        fabricated_references: List[str] = []
        diagnosis_drift: Optional[str] = None

        # 1. IDENTIFIER VALIDATION
        auth_ids = self._get_authorized_identifiers(evidence_pack)
        for field_name, text in all_texts:
            for id_token in self._extract_identifiers(text):
                if id_token not in auth_ids:
                    viol = ValidationViolation(
                        violation_type=ViolationType.FABRICATED_IDENTIFIER,
                        claim_text=id_token,
                        expected_evidence=f"Identifier must exist in VEO: {sorted(list(auth_ids))}",
                        severity="CRITICAL",
                        description=f"AI response cited alien/fabricated identifier '{id_token}' in {field_name}.",
                    )
                    violations.append(viol)
                    fabricated_references.append(id_token)
                    unsupported_claims.append(f"Identifier {id_token}")
                else:
                    verified_claims.append(f"Identifier {id_token}")

        # Check explicit reference claims like 'bank record #999'
        for field_name, text in all_texts:
            for pattern in FABRICATED_REF_PATTERNS:
                for match in pattern.finditer(text):
                    ref_token = match.group(1).strip()
                    if ref_token not in auth_ids and not self._matches_evidence_reference(ref_token, evidence_pack):
                        viol = ValidationViolation(
                            violation_type=ViolationType.FABRICATED_EVIDENCE_REF,
                            claim_text=match.group(0),
                            expected_evidence="Evidence reference must match actual VEO records",
                            severity="CRITICAL",
                            description=f"AI fabricated ungrounded evidence citation '{match.group(0)}' in {field_name}.",
                        )
                        violations.append(viol)
                        fabricated_references.append(match.group(0))

        # 2. NUMERIC / MONETARY VALIDATION
        auth_amounts = self._get_authorized_amounts(evidence_pack)
        for field_name, text in all_texts:
            field_amounts = self._extract_monetary_amounts(text)
            for amt_str, dec_val in field_amounts:
                if dec_val not in auth_amounts:
                    viol = ValidationViolation(
                        violation_type=ViolationType.AMOUNT_MISMATCH,
                        claim_text=amt_str,
                        expected_evidence=f"Authorized monetary amounts in VEO: {[str(a) for a in sorted(list(auth_amounts))]}",
                        severity="CRITICAL",
                        description=f"AI cited monetary value '{amt_str}' ({dec_val}) which does not match any authoritative VEO amount.",
                    )
                    violations.append(viol)
                    numeric_violations.append(f"{amt_str} ({dec_val})")
                    unsupported_claims.append(f"Amount {amt_str}")
                else:
                    verified_claims.append(f"Amount {amt_str}")

        # 3. DIAGNOSIS ALIGNMENT & DRIFT
        canonical_diagnosis = evidence_pack.diagnosis.value
        all_diagnoses = {d.value: d for d in SettlementDiagnosis}
        for field_name, text in all_texts:
            for diag_val, diag_enum in all_diagnoses.items():
                if diag_val != canonical_diagnosis:
                    pattern = re.compile(rf"\b(?:diagnos(?:is|ed as)|status is|state is)\s+[:\-]?\s*{re.escape(diag_val)}\b", re.IGNORECASE)
                    if pattern.search(text) or f" {diag_val} " in f" {text} ":
                        if not self._is_negated_or_hypothetical(text, diag_val):
                            viol = ValidationViolation(
                                violation_type=ViolationType.DIAGNOSIS_MISMATCH,
                                claim_text=diag_val,
                                expected_evidence=f"Authoritative VEO diagnosis is '{canonical_diagnosis}'",
                                severity="CRITICAL",
                                description=f"AI response asserted contradictory diagnosis '{diag_val}' in {field_name}.",
                            )
                            violations.append(viol)
                            diagnosis_drift = diag_val
                            contradictions.append(f"Asserted {diag_val} instead of {canonical_diagnosis}")

        # 4. STATUS CONTRADICTIONS
        self._check_status_contradictions(all_texts, evidence_pack, violations, contradictions)

        # 5. EPISTEMIC & UNSUPPORTED CAUSAL CLAIMS
        self._check_epistemic_and_causal_claims(all_texts, evidence_pack, violations, epistemic_violations, unsupported_claims)

        # 6. TEMPORAL / FUTURE CLAIMS (ETAs)
        self._check_temporal_claims(all_texts, evidence_pack, violations, unsupported_claims)

        # 7. MATERIAL OMISSION CHECK
        self._check_material_omissions(all_texts, evidence_pack, violations, contradictions)

        # FINAL DECISION POLICY
        if len(violations) == 0:
            decision = ValidationDecision.PASS
            is_valid = True
        else:
            decision = ValidationDecision.REJECT
            is_valid = False

        return ResponseValidationResult(
            is_valid=is_valid,
            decision=decision,
            violations=violations,
            verified_claims=verified_claims,
            unsupported_claims=unsupported_claims,
            contradictions=contradictions,
            epistemic_violations=epistemic_violations,
            numeric_violations=numeric_violations,
            fabricated_references=fabricated_references,
            diagnosis_drift=diagnosis_drift,
            validation_version=self.version,
        )

    # ------------------------------------------------------------------------
    # Internal Validation Helpers
    # ------------------------------------------------------------------------

    def _get_authorized_identifiers(self, veo: VerifiedEvidencePack) -> Set[str]:
        """Collects all valid canonical identifiers present in the VEO."""
        ids: Set[str] = set()
        if veo.transaction_id:
            ids.add(veo.transaction_id)
        if veo.query_identifier:
            ids.add(veo.query_identifier)
        if veo.veo_id:
            ids.add(veo.veo_id)

        # Gateway identifiers
        gw = veo.gateway
        if gw and gw.present:
            for val in [gw.transaction_id, gw.order_id]:
                if val:
                    ids.add(str(val))

        # Bank identifiers
        bnk = veo.bank
        if bnk and bnk.present:
            for val in [bnk.settlement_id, bnk.bank_reference_number, bnk.gateway_transaction_id]:
                if val:
                    ids.add(str(val))

        # Ledger identifiers
        led = veo.ledger
        if led and led.present:
            for val in [led.ledger_entry_id, led.gateway_transaction_id]:
                if val:
                    ids.add(str(val))

        # Evidence references
        for ref in getattr(veo, "evidence_refs", []):
            if ref.record_id:
                ids.add(str(ref.record_id))

        return ids

    def _extract_identifiers(self, text: str) -> Set[str]:
        """Extracts structured identifier tokens matching canonical schemas."""
        found: Set[str] = set()
        for pattern in ID_PATTERNS:
            for match in pattern.finditer(text):
                found.add(match.group(1).strip())
        return found

    def _matches_evidence_reference(self, ref_token: str, veo: VerifiedEvidencePack) -> bool:
        """Checks if a reference token matches any record or line number in evidence references."""
        for ref in getattr(veo, "evidence_refs", []):
            if ref_token == str(ref.record_id) or ref_token == str(ref.source_row_index):
                return True
        return False

    def _get_authorized_amounts(self, veo: VerifiedEvidencePack) -> Set[Decimal]:
        """Collects all authorized monetary figures in the VEO using Decimal."""
        amounts: Set[Decimal] = set()

        # Gateway amounts
        if veo.gateway and veo.gateway.present:
            if veo.gateway.gross_amount is not None:
                amounts.add(Decimal(str(veo.gateway.gross_amount)))

        # Bank amounts
        if veo.bank and veo.bank.present:
            if veo.bank.net_settlement_amount is not None:
                amounts.add(Decimal(str(veo.bank.net_settlement_amount)))

        # Ledger amounts
        if veo.ledger and veo.ledger.present:
            if veo.ledger.ledger_amount is not None:
                amounts.add(Decimal(str(veo.ledger.ledger_amount)))

        # Reconciliation differences / variances
        if veo.reconciliation:
            rec = veo.reconciliation
            if rec.bank_ledger_numeric_diff is not None:
                amounts.add(abs(Decimal(str(rec.bank_ledger_numeric_diff))))
                amounts.add(Decimal(str(rec.bank_ledger_numeric_diff)))
            if rec.gross_minus_net_variance is not None:
                amounts.add(abs(Decimal(str(rec.gross_minus_net_variance))))
                amounts.add(Decimal(str(rec.gross_minus_net_variance)))

        # Add 0 as a standard neutral figure
        amounts.add(Decimal("0"))
        amounts.add(Decimal("0.00"))

        return amounts

    def _extract_monetary_amounts(self, text: str) -> List[Tuple[str, Decimal]]:
        """
        Extracts currency numbers from text and parses them as Decimal.
        Filters out 4-digit calendar years (2025, 2026) and IDs.
        """
        results: List[Tuple[str, Decimal]] = []

        # 1. Prefix matches (INR 111358, ₹4,850.00)
        for match in CURRENCY_PREFIX_PATTERN.finditer(text):
            raw = match.group(1).strip()
            clean = raw.replace(",", "")
            try:
                val = Decimal(clean)
                results.append((match.group(0).strip(), val))
            except InvalidOperation:
                pass

        # 2. Suffix matches (111358 INR, 4850.00 rupees)
        for match in CURRENCY_SUFFIX_PATTERN.finditer(text):
            raw = match.group(1).strip()
            clean = raw.replace(",", "")
            try:
                val = Decimal(clean)
                results.append((match.group(0).strip(), val))
            except InvalidOperation:
                pass

        # 3. Standalone amounts with decimal places e.g. "111358.00" or comma separated "38,261"
        standalone_pattern = re.compile(r"\b([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+\.[0-9]{2})\b")
        for match in standalone_pattern.finditer(text):
            raw = match.group(1).strip()
            clean = raw.replace(",", "")
            try:
                val = Decimal(clean)
                if not any(r[1] == val for r in results):
                    results.append((raw, val))
            except InvalidOperation:
                pass

        return results

    def _check_status_contradictions(
        self,
        all_texts: List[Tuple[str, str]],
        veo: VerifiedEvidencePack,
        violations: List[ValidationViolation],
        contradictions: List[str],
    ) -> None:
        """Detects contradictions between AI narrative and authoritative system statuses."""
        diag = veo.diagnosis

        for field_name, text in all_texts:
            lower = text.lower()

            # If BANK REJECTED: cannot claim successful settlement or payout credited
            if diag == SettlementDiagnosis.BANK_REJECTED or (veo.bank and veo.bank.settlement_status == "REJECTED"):
                if any(phrase in lower for phrase in [
                    "successfully settled",
                    "settled successfully",
                    "payout was successful",
                    "funds were disbursed",
                    "money has been credited to the merchant",
                    "payment is complete and confirmed",
                ]):
                    viol = ValidationViolation(
                        violation_type=ViolationType.STATUS_CONTRADICTION,
                        claim_text="successfully settled / disbursed",
                        expected_evidence=f"Bank status is REJECTED (diagnosis {diag.value})",
                        severity="CRITICAL",
                        description=f"AI claimed successful settlement in {field_name} when bank status is REJECTED.",
                    )
                    violations.append(viol)
                    contradictions.append("Claimed successful settlement when bank rejected.")

            # If MISSING BANK RECORD: cannot claim bank confirmed or received
            if diag == SettlementDiagnosis.MISSING_BANK_RECORD or (veo.bank and not veo.bank.present):
                if any(phrase in lower for phrase in [
                    "bank has confirmed",
                    "bank confirmed the payment",
                    "bank processed the payment",
                    "bank successfully settled",
                    "bank disbursed",
                ]):
                    viol = ValidationViolation(
                        violation_type=ViolationType.STATUS_CONTRADICTION,
                        claim_text="bank confirmed / processed",
                        expected_evidence="Bank record is missing from evidence",
                        severity="CRITICAL",
                        description=f"AI claimed bank confirmed/processed in {field_name} when bank record is absent.",
                    )
                    violations.append(viol)
                    contradictions.append("Claimed bank confirmed when bank record is absent.")

            # If GATEWAY FAILED: cannot claim payment captured or successful
            if diag == SettlementDiagnosis.GATEWAY_FAILED or (veo.gateway and veo.gateway.status == "FAILED"):
                if any(phrase in lower for phrase in [
                    "captured successfully",
                    "payment succeeded",
                    "funds captured",
                    "payout is due",
                ]):
                    viol = ValidationViolation(
                        violation_type=ViolationType.STATUS_CONTRADICTION,
                        claim_text="captured successfully / payment succeeded",
                        expected_evidence="Gateway status is FAILED",
                        severity="CRITICAL",
                        description=f"AI claimed successful capture in {field_name} when gateway status is FAILED.",
                    )
                    violations.append(viol)
                    contradictions.append("Claimed successful capture when gateway failed.")

            # If MISSING LEDGER: cannot claim ledger posted
            if diag == SettlementDiagnosis.MISSING_LEDGER_RECORD or (veo.ledger and not veo.ledger.present):
                if any(phrase in lower for phrase in [
                    "ledger entry posted",
                    "ledger entry is posted",
                    "internal ledger credited",
                    "ledger has recorded",
                ]):
                    viol = ValidationViolation(
                        violation_type=ViolationType.STATUS_CONTRADICTION,
                        claim_text="ledger entry posted",
                        expected_evidence="Ledger record is missing from evidence",
                        severity="CRITICAL",
                        description=f"AI claimed ledger entry was posted in {field_name} when ledger record is absent.",
                    )
                    violations.append(viol)
                    contradictions.append("Claimed ledger posted when ledger record is absent.")

    def _check_epistemic_and_causal_claims(
        self,
        all_texts: List[Tuple[str, str]],
        veo: VerifiedEvidencePack,
        violations: List[ValidationViolation],
        epistemic_violations: List[str],
        unsupported_claims: List[str],
    ) -> None:
        """
        Validates that UNKNOWN facts are not asserted as KNOWN,
        and that speculative causes (insufficient funds, server down, fraud) are rejected.
        """
        err_desc = (veo.gateway.error_description or "") if veo.gateway else ""
        veo_text = f"{veo.summary} {err_desc}".lower()

        for field_name, text in all_texts:
            lower = text.lower()

            for spec_key, spec_desc in SPECULATIVE_REASONS:
                if spec_key in lower:
                    if spec_key not in veo_text:
                        if not self._is_epistemically_safe_mention(lower, spec_key):
                            viol = ValidationViolation(
                                violation_type=ViolationType.UNSUPPORTED_CAUSAL_CLAIM,
                                claim_text=spec_key,
                                expected_evidence="Causal failure reason must be explicitly recorded in VEO",
                                severity="CRITICAL",
                                description=f"AI asserted unsupported causal claim '{spec_desc}' in {field_name} without evidence.",
                            )
                            violations.append(viol)
                            epistemic_violations.append(f"Unsupported cause: {spec_desc}")
                            unsupported_claims.append(f"Cause '{spec_desc}'")

            # Check for fabricated tax/fee percentages (e.g. 18% GST, 2.5% fee)
            fabricated_fee_pattern = re.compile(r"\b(\d+(?:\.\d+)?%\s*(?:gst|tax|vat|fee|charge))\b", re.IGNORECASE)
            for match in fabricated_fee_pattern.finditer(text):
                fee_claim = match.group(0)
                if fee_claim.lower() not in veo_text:
                    viol = ValidationViolation(
                        violation_type=ViolationType.UNSUPPORTED_CAUSAL_CLAIM,
                        claim_text=fee_claim,
                        expected_evidence="Taxes or fees must be explicitly specified in VEO",
                        severity="HIGH",
                        description=f"AI asserted unbacked tax/fee claim '{fee_claim}' in {field_name}.",
                    )
                    violations.append(viol)
                    epistemic_violations.append(fee_claim)

    def _check_temporal_claims(
        self,
        all_texts: List[Tuple[str, str]],
        veo: VerifiedEvidencePack,
        violations: List[ValidationViolation],
        unsupported_claims: List[str],
    ) -> None:
        """Validates that no unsupported future arrival ETAs (tomorrow, 2 days) are promised."""
        for field_name, text in all_texts:
            for pattern in TEMPORAL_PATTERNS:
                match = pattern.search(text)
                if match:
                    claim = match.group(0)
                    if not self._is_epistemically_safe_mention(text.lower(), claim.lower()):
                        viol = ValidationViolation(
                            violation_type=ViolationType.UNSUPPORTED_TEMPORAL_CLAIM,
                            claim_text=claim,
                            expected_evidence="Historical VEO records cannot verify future settlement arrival dates",
                            severity="CRITICAL",
                            description=f"AI promised unsupported future settlement arrival ETA '{claim}' in {field_name}.",
                        )
                        violations.append(viol)
                        unsupported_claims.append(f"ETA claim: {claim}")

    def _check_material_omissions(
        self,
        all_texts: List[Tuple[str, str]],
        veo: VerifiedEvidencePack,
        violations: List[ValidationViolation],
        contradictions: List[str],
    ) -> None:
        """
        Detects cases where a response makes an absolute statement of normal completion
        while completely omitting an active conflict or failure.
        """
        if veo.diagnosis in (SettlementDiagnosis.CONFLICTING_EVIDENCE, SettlementDiagnosis.BANK_REJECTED, SettlementDiagnosis.GATEWAY_FAILED):
            for field_name, text in all_texts:
                lower = text.lower()
                if "all systems agree" in lower or "completely normal and settled" in lower:
                    viol = ValidationViolation(
                        violation_type=ViolationType.MATERIAL_OMISSION,
                        claim_text="all systems agree / completely normal",
                        expected_evidence=f"Active discrepancy diagnosed as {veo.diagnosis.value}",
                        severity="CRITICAL",
                        description=f"AI omitted active conflict/failure in {field_name} while claiming complete agreement.",
                    )
                    violations.append(viol)
                    contradictions.append(f"Material omission: claimed agreement during {veo.diagnosis.value}")

    def _is_negated_or_hypothetical(self, text: str, token: str) -> bool:
        """Checks if a diagnosis token is mentioned with negation (e.g. 'not BANK_REJECTED')."""
        lower = text.lower()
        token_lower = token.lower()
        patterns = [
            f"not {token_lower}",
            f"rather than {token_lower}",
            f"instead of {token_lower}",
            f"unlike {token_lower}",
            f"is not {token_lower}",
        ]
        return any(p in lower for p in patterns)

    def _is_epistemically_safe_mention(self, text_lower: str, token_lower: str) -> bool:
        """
        Checks if a sensitive term (e.g. 'insufficient funds', 'tomorrow') is mentioned safely,
        e.g., stating that it is unrecorded or not in evidence.
        """
        safe_qualifiers = [
            "not recorded",
            "not present",
            "not specified",
            "unrecorded",
            "absent from",
            "no indication",
            "no evidence",
            "do not specify",
            "does not specify",
            "not contain",
            "does not contain",
            "unknown",
            "no recorded",
        ]
        idx = text_lower.find(token_lower)
        if idx != -1:
            snippet = text_lower[max(0, idx - 60):min(len(text_lower), idx + len(token_lower) + 60)]
            return any(q in snippet for q in safe_qualifiers)
        return False
