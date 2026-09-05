"""
server/diagnosis/engine.py

Deterministic Diagnosis Engine for PS-8 Settlement Q&A Agent (Phase 5).
Maps cross-system trace and reconciliation findings into the authoritative 11-state taxonomy
using a strict priority decision tree.
Adheres strictly to docs/rules.md, docs/prd.md, and docs/arch.md:
- Completely deterministic: NO LLM, NO probabilistic inference
- Evaluates rules in strict priority order (arch.md Section 7.2)
- Produces rule-based confidence (HIGH, MEDIUM, LOW) with explainable rationale
- Assembles comprehensive DiagnosisResult containing epistemic breakdown, exceptions, and evidence refs
"""

from decimal import Decimal
from typing import Optional, List, Literal

from server.tracing.models import TraceResult
from server.reconciliation.models import (
    ReconciliationResult,
    BankLedgerComparisonStatus,
    StatusConsistencyStatus,
)
from server.reconciliation.engine import reconcile_trace
from server.diagnosis.models import (
    SettlementDiagnosis,
    ConfidenceLevel,
    InvestigationStatus,
    DiagnosisResult,
    EvidenceReference,
)
from server.exceptions.models import (
    ExceptionType,
    ExceptionSeverity,
    SettlementException,
    EpistemicBreakdown,
)
from server.exceptions.engine import ExceptionEngine
from server.diagnosis.exceptions import InvalidDiagnosisInputError


class DiagnosisEngine:
    """
    Deterministic Diagnosis Engine mapping verified financial evidence into 11 system states.
    Executes Section 7.2 priority decision tree from docs/arch.md.
    """

    def __init__(self, exception_engine: Optional[ExceptionEngine] = None):
        self.exception_engine = exception_engine or ExceptionEngine()

    def diagnose(
        self,
        trace: TraceResult,
        recon: Optional[ReconciliationResult] = None,
    ) -> DiagnosisResult:
        """
        Evaluates a TraceResult and ReconciliationResult to generate a deterministic DiagnosisResult.
        If recon is not provided, automatically reconciles the trace.
        """
        if not isinstance(trace, TraceResult):
            raise InvalidDiagnosisInputError(
                f"Expected instance of TraceResult, got {type(trace).__name__}"
            )

        if recon is None:
            recon = reconcile_trace(trace)
        elif not isinstance(recon, ReconciliationResult):
            raise InvalidDiagnosisInputError(
                f"Expected instance of ReconciliationResult, got {type(recon).__name__}"
            )

        txn_id = (
            trace.resolved_gateway_transaction_id
            or recon.transaction_id
            or trace.query.identifier_value
        )

        gw = trace.gateway_record
        bnk = trace.bank_record
        led = trace.ledger_record

        is_dup = (
            getattr(trace, "is_duplicate", False)
            or getattr(recon, "is_duplicate", False)
            or bool(getattr(trace, "duplicate_records", None))
            or bool(getattr(recon, "duplicate_records", None))
        )
        has_ref_mismatch = (
            (bnk and gw and bnk.gateway_transaction_id != gw.gateway_transaction_id)
            or (led and gw and led.gateway_transaction_id != gw.gateway_transaction_id)
            or getattr(recon, "has_reference_mismatch", False)
            or getattr(trace, "has_reference_mismatch", False)
        )

        # -------------------------------------------------------------
        # STRICT PRIORITY DECISION TREE (docs/arch.md Section 7.2)
        # -------------------------------------------------------------

        # Priority 1: Insufficient Evidence / Missing Gateway record
        if gw is None:
            diagnosis_code = SettlementDiagnosis.INSUFFICIENT_EVIDENCE
            confidence = ConfidenceLevel.LOW
            confidence_reason = "Critical gateway transaction capture record is missing or could not be resolved."
            severity = ExceptionSeverity.CRITICAL
            status = InvestigationStatus.INSUFFICIENT_DATA
            summary = (
                f"Investigation for '{txn_id}' cannot establish settlement state because no Gateway capture "
                f"record was found in the dataset. Bank and/or Ledger records cannot be anchored without gateway origin."
            )
            recommendation = "Search manual banking portal logs and secondary archives to locate missing gateway capture reference."

        # Priority 2: Conflicting Evidence (Gateway FAILED, Bank PROCESSED/SETTLED)
        elif gw.status == "failed" and bnk and bnk.settlement_status in ["processed", "settled"]:
            diagnosis_code = SettlementDiagnosis.CONFLICTING_EVIDENCE
            confidence = ConfidenceLevel.LOW
            confidence_reason = "Irreconcilable cross-system contradiction: Gateway authorization failed, but Bank clearing recorded processed disbursement."
            severity = ExceptionSeverity.CRITICAL
            status = InvestigationStatus.EXCEPTION
            summary = (
                f"Transaction '{txn_id}' contains irreconcilable conflicting evidence: Gateway records payment as 'failed', "
                f"yet Bank clearing file records settlement disbursement as '{bnk.settlement_status}' (UTR: {bnk.bank_reference_number})."
            )
            recommendation = "Flag transaction for urgent fraud and operations audit. Determine whether customer was debited despite gateway failure, or if bank file was misattributed."

        # Priority 3: Gateway Failed (Terminal authorization failure without bank processing)
        elif gw.status == "failed":
            diagnosis_code = SettlementDiagnosis.GATEWAY_FAILED
            confidence = ConfidenceLevel.HIGH
            confidence_reason = "Gateway payment definitively failed during authorization; no merchant settlement was ever due."
            severity = ExceptionSeverity.HIGH
            status = InvestigationStatus.EXCEPTION
            err_msg = gw.error_description or gw.error_code or "declined by issuer"
            summary = (
                f"Customer payment for transaction '{txn_id}' failed at the gateway authorization stage ({err_msg}). "
                f"No funds were captured, and no merchant settlement is due."
            )
            recommendation = "Advise customer to re-attempt checkout with an alternative payment method. No merchant settlement is due."

        # Priority 4: Duplicate Record
        elif is_dup:
            diagnosis_code = SettlementDiagnosis.DUPLICATE_RECORD
            confidence = ConfidenceLevel.LOW
            confidence_reason = "Multiple entity records detected for the same anchor transaction identifier."
            severity = ExceptionSeverity.HIGH
            status = InvestigationStatus.EXCEPTION
            summary = f"Duplicate entity record detected for transaction '{txn_id}'."
            recommendation = "Review deduplication pipeline and check for duplicate submission or multi-posting."

        # Priority 5: Bank Rejection (Gateway captured, but Bank settlement failed)
        elif bnk and bnk.settlement_status == "failed":
            diagnosis_code = SettlementDiagnosis.BANK_REJECTED
            confidence = ConfidenceLevel.HIGH if (gw.error_code or gw.error_description) else ConfidenceLevel.MEDIUM
            confidence_reason = "Bank clearing network returned an explicit failed/rejected settlement status for the payment instruction."
            severity = ExceptionSeverity.HIGH
            status = InvestigationStatus.EXCEPTION
            summary = (
                f"Payment for transaction '{txn_id}' was captured at gateway (gross INR {gw.gross_amount}), but the clearing "
                f"bank rejected settlement disbursement (reference: {bnk.bank_reference_number})."
            )
            recommendation = "Clearing bank rejected settlement disbursement. Verify merchant bank account details (IFSC/account number/active status) and initiate payout retry."

        # Priority 6: Amount Mismatch (Bank net settlement != Ledger booked amount)
        elif recon.bank_ledger_comparison.status == BankLedgerComparisonStatus.MISMATCH:
            diagnosis_code = SettlementDiagnosis.AMOUNT_MISMATCH
            confidence = ConfidenceLevel.LOW
            confidence_reason = "Discrepancy detected between Bank net disbursement amount and internal Ledger booked amount."
            severity = ExceptionSeverity.CRITICAL
            status = InvestigationStatus.EXCEPTION
            diff = recon.bank_ledger_comparison.numeric_difference
            summary = (
                f"Amount mismatch detected for transaction '{txn_id}': Bank net settlement disbursement is INR {recon.bank_net_settlement_amount}, "
                f"but internal Ledger booked amount is INR {recon.ledger_amount} (variance: INR {diff})."
            )
            recommendation = "Halt automated settlement disbursement. Escalate to Payment Operations and Treasury to investigate net disbursement vs ledger discrepancy."

        # Priority 7: Reference Mismatch
        elif has_ref_mismatch:
            diagnosis_code = SettlementDiagnosis.REFERENCE_MISMATCH
            confidence = ConfidenceLevel.LOW
            confidence_reason = "Cross-system identifier linkage inconsistency detected between gateway and downstream records."
            severity = ExceptionSeverity.CRITICAL
            status = InvestigationStatus.EXCEPTION
            summary = f"Reference mismatch detected for transaction '{txn_id}': entity records do not share consistent cross-system identifiers."
            recommendation = "Audit foreign key linkage and reference translation tables to repair misattributed records."

        # Priority 6: Missing Bank Record (Gateway captured, Bank missing)
        elif bnk is None:
            diagnosis_code = SettlementDiagnosis.MISSING_BANK_RECORD
            confidence = ConfidenceLevel.LOW
            confidence_reason = "Transaction captured at gateway, but no corresponding clearing record exists in partner bank settlement file."
            severity = ExceptionSeverity.HIGH
            status = InvestigationStatus.EXCEPTION
            summary = (
                f"Transaction '{txn_id}' was successfully captured at gateway for gross amount INR {gw.gross_amount}, "
                f"but clearing bank dataset contains no matching settlement record."
            )
            recommendation = "Escalate to Payment Operations to query partner bank clearing file for settlement instruction and confirm nodal credit status."

        # Priority 7: Missing Ledger Record (Gateway captured, Bank present, Ledger missing)
        elif led is None:
            diagnosis_code = SettlementDiagnosis.MISSING_LEDGER_RECORD
            confidence = ConfidenceLevel.LOW
            confidence_reason = "Gateway captured and Bank clearing record exists, but internal accounting ledger journal entry is absent."
            severity = ExceptionSeverity.HIGH
            status = InvestigationStatus.EXCEPTION
            summary = (
                f"Transaction '{txn_id}' was captured at gateway and processed by bank (net INR {bnk.net_settlement_amount}), "
                f"but internal double-entry accounting ledger has no record of the transaction."
            )
            recommendation = "Escalate to Finance / Accounting Ops to post missing double-entry journal entry for the verified bank disbursement."

        # Priority 8: In-flight / Settlement Pending (Bank pending)
        elif bnk.settlement_status == "pending":
            diagnosis_code = SettlementDiagnosis.SETTLEMENT_PENDING
            confidence = ConfidenceLevel.MEDIUM
            confidence_reason = "Payment captured and posted; bank clearing is actively pending within standard banking window."
            severity = ExceptionSeverity.LOW
            status = InvestigationStatus.PENDING
            summary = (
                f"Payment for transaction '{txn_id}' is in progress. Funds were captured at gateway and booked in ledger; "
                f"clearing bank transfer is currently pending nodal settlement."
            )
            recommendation = "Transaction settlement is in progress. Allow standard banking SLA window (T+1 to T+2 banking days) for nodal clearing before manual escalation."

        # Priority 9: Successfully Settled (Happy path)
        elif (
            gw.status == "captured"
            and bnk.settlement_status in ["processed", "settled"]
            and led.entry_type == "credit"
            and recon.bank_ledger_comparison.status == BankLedgerComparisonStatus.MATCH
            and not recon.status_comparison.has_conflict
        ):
            diagnosis_code = SettlementDiagnosis.SUCCESSFULLY_SETTLED
            confidence = ConfidenceLevel.HIGH
            confidence_reason = "Complete 3-system evidence chain verified: Gateway captured, Bank cleared with UTR, Ledger credited, and net amounts match exactly."
            severity = ExceptionSeverity.NONE
            status = InvestigationStatus.RESOLVED
            summary = (
                f"Transaction '{txn_id}' is fully settled and reconciled. Gateway captured gross INR {gw.gross_amount}, "
                f"Bank disbursed net INR {bnk.net_settlement_amount} (UTR: {bnk.bank_reference_number}), and internal Ledger credited INR {led.ledger_amount}."
            )
            recommendation = "Transaction is fully settled and reconciled across Gateway, Bank, and Ledger. No operational action required. Provide UTR reference to merchant if requested."

        # Fallback: Insufficient Evidence
        else:
            diagnosis_code = SettlementDiagnosis.INSUFFICIENT_EVIDENCE
            confidence = ConfidenceLevel.LOW
            confidence_reason = "Available evidence is incomplete or inconclusive to assign a definitive settlement state."
            severity = ExceptionSeverity.HIGH
            status = InvestigationStatus.INSUFFICIENT_DATA
            summary = f"Investigation for transaction '{txn_id}' is inconclusive due to partial or unrecognized cross-system evidence."
            recommendation = "Review source logs manually across Gateway, Bank, and Ledger systems."

        # -------------------------------------------------------------
        # ASSEMBLE EXCEPTIONS & EPISTEMIC FACTS
        # -------------------------------------------------------------
        exceptions = self.exception_engine.classify_exceptions(trace, recon)
        primary_exception = exceptions[0] if exceptions else None

        epistemic = self.exception_engine.classify_epistemic_facts(trace, recon, diagnosis_code)
        evidence_refs = self.exception_engine.extract_evidence_references(trace)

        conflicts = [recon.status_comparison.conflict_details] if recon.status_comparison.conflict_details else []

        return DiagnosisResult(
            transaction_id=txn_id,
            diagnosis_code=diagnosis_code,
            confidence=confidence,
            confidence_reason=confidence_reason,
            severity=severity,
            status=status,
            summary=summary,
            primary_exception=primary_exception,
            exceptions=exceptions,
            epistemic_facts=epistemic,
            evidence_refs=evidence_refs,
            missing_records=recon.missing_evidence,
            conflicts=conflicts,
            recommended_next_action=recommendation,
        )


def diagnose_transaction(
    trace: TraceResult,
    recon: Optional[ReconciliationResult] = None,
) -> DiagnosisResult:
    """Convenience functional interface for running deterministic transaction diagnosis."""
    engine = DiagnosisEngine()
    return engine.diagnose(trace, recon)
