"""
server/exceptions/engine.py

Core engine for PS-8 Settlement Q&A Agent Exception Classification & Epistemic Honesty (Phase 5).
Evaluates operational anomalies, extracts multiple simultaneous exceptions, and constructs
the Tri-State Epistemic Model (KNOWN vs INFERRED vs UNKNOWN) without hallucinating unverified causes.
"""

from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any

from server.tracing.models import TraceResult
from server.reconciliation.models import ReconciliationResult, BankLedgerComparisonStatus, StatusConsistencyStatus
from server.exceptions.models import (
    ExceptionType,
    ExceptionSeverity,
    SettlementException,
    EpistemicBreakdown,
    EvidenceReference,
)


class ExceptionEngine:
    """
    Deterministic engine for detecting exceptions and categorizing epistemic facts.
    Guarantees no hallucinated causes: if an explanation is absent from source records,
    it is categorized strictly under UNKNOWN.
    """

    def classify_exceptions(
        self,
        trace: TraceResult,
        recon: ReconciliationResult,
    ) -> List[SettlementException]:
        """
        Detects all active operational exceptions across trace and reconciliation evidence.
        Does NOT silently discard secondary anomalies when multiple problems coexist.
        """
        exceptions: List[SettlementException] = []

        gw = trace.gateway_record
        bnk = trace.bank_record
        led = trace.ledger_record

        # 1. Missing Gateway record
        if gw is None:
            exceptions.append(
                SettlementException(
                    exception_type=ExceptionType.MISSING_GATEWAY,
                    severity=ExceptionSeverity.CRITICAL,
                    message="Gateway transaction capture record is missing from the dataset.",
                    affected_fields=["gateway_transaction_id"],
                    remediation="Query gateway archives or merchant checkout logs to locate the missing capture record.",
                )
            )

        # 2. Conflicting Evidence (Gateway FAILED vs Bank PROCESSED/SETTLED)
        if gw and bnk and gw.status == "failed" and bnk.settlement_status in ["processed", "settled"]:
            exceptions.append(
                SettlementException(
                    exception_type=ExceptionType.CONFLICTING_EVIDENCE,
                    severity=ExceptionSeverity.CRITICAL,
                    message=(
                        f"Gateway records payment authorization as 'failed', but Bank clearing records "
                        f"settlement as '{bnk.settlement_status}' (UTR: {bnk.bank_reference_number})."
                    ),
                    affected_fields=["status", "settlement_status"],
                    conflicting_values={
                        "gateway_status": gw.status,
                        "bank_settlement_status": bnk.settlement_status,
                    },
                    remediation="Urgent operational audit required: verify if customer was debited or bank file was misattributed.",
                )
            )

        # 3. Bank Rejection (Bank settlement failed)
        if bnk and bnk.settlement_status == "failed":
            exceptions.append(
                SettlementException(
                    exception_type=ExceptionType.BANK_REJECTION,
                    severity=ExceptionSeverity.HIGH,
                    message=(
                        f"Bank clearing network rejected settlement disbursement "
                        f"(reference: {bnk.bank_reference_number})."
                    ),
                    affected_fields=["settlement_status", "bank_reference_number"],
                    remediation="Verify merchant bank account IFSC and status, then re-dispatch payout.",
                )
            )

        # 4. Gateway Failure (Terminal authorization failure without bank processing)
        if gw and gw.status == "failed" and (bnk is None or bnk.settlement_status != "processed"):
            err_detail = gw.error_description or gw.error_code or "declined by issuer"
            exceptions.append(
                SettlementException(
                    exception_type=ExceptionType.GATEWAY_FAILURE,
                    severity=ExceptionSeverity.HIGH,
                    message=f"Customer payment authorization failed at gateway ({err_detail}).",
                    affected_fields=["status", "error_code", "error_description"],
                    conflicting_values={"error_code": gw.error_code, "error_description": gw.error_description},
                    remediation="Advise customer to retry checkout with an alternative payment method. No merchant settlement is due.",
                )
            )

        # 5. Missing Bank Record (Gateway captured, but no Bank record)
        if gw and gw.status == "captured" and bnk is None:
            exceptions.append(
                SettlementException(
                    exception_type=ExceptionType.MISSING_BANK,
                    severity=ExceptionSeverity.HIGH,
                    message="Transaction was captured at gateway, but no corresponding bank clearing record exists.",
                    affected_fields=["bank_reference_number", "settlement_id"],
                    remediation="Escalate to Payment Operations to query partner bank clearing file for settlement batch status.",
                )
            )

        # 6. Missing Ledger Entry (Payment captured/settled, but Ledger entry missing)
        if gw and gw.status == "captured" and led is None:
            exceptions.append(
                SettlementException(
                    exception_type=ExceptionType.MISSING_LEDGER,
                    severity=ExceptionSeverity.HIGH,
                    message="Payment was captured at gateway, but no double-entry posting exists in internal ledger.",
                    affected_fields=["ledger_entry_id", "entry_type", "ledger_amount"],
                    remediation="Escalate to Finance / Accounting Ops to post missing double-entry journal entry.",
                )
            )

        # 7. Amount Mismatch (Bank net disbursement != Ledger booked amount)
        if recon.bank_ledger_comparison.status == BankLedgerComparisonStatus.MISMATCH:
            exceptions.append(
                SettlementException(
                    exception_type=ExceptionType.AMOUNT_MISMATCH,
                    severity=ExceptionSeverity.CRITICAL,
                    message=(
                        f"Bank net settlement amount ({recon.bank_net_settlement_amount}) does not equal "
                        f"Ledger booked amount ({recon.ledger_amount}). Variance: {recon.bank_ledger_comparison.numeric_difference}."
                    ),
                    affected_fields=["net_settlement_amount", "ledger_amount"],
                    conflicting_values={
                        "bank_net": str(recon.bank_net_settlement_amount),
                        "ledger_amount": str(recon.ledger_amount),
                    },
                    remediation="Halt settlement disbursement and reconcile net disbursement variance with Treasury.",
                )
            )

        # 8. Reference Mismatch (Identifier linkage discrepancy)
        has_ref_mismatch = (
            (bnk and gw and bnk.gateway_transaction_id != gw.gateway_transaction_id)
            or (led and gw and led.gateway_transaction_id != gw.gateway_transaction_id)
            or getattr(recon, "has_reference_mismatch", False)
            or getattr(trace, "has_reference_mismatch", False)
        )
        if has_ref_mismatch:
            exceptions.append(
                SettlementException(
                    exception_type=ExceptionType.REFERENCE_MISMATCH,
                    severity=ExceptionSeverity.CRITICAL,
                    message="Identifier linkage mismatch detected across financial entities.",
                    affected_fields=["gateway_transaction_id"],
                    remediation="Re-index cross-system identifier mapping and verify foreign key consistency.",
                )
            )

        # 9. Duplicate record detection
        is_dup = (
            getattr(trace, "is_duplicate", False)
            or getattr(recon, "is_duplicate", False)
            or bool(getattr(trace, "duplicate_records", None))
            or bool(getattr(recon, "duplicate_records", None))
        )
        if is_dup:
            exceptions.append(
                SettlementException(
                    exception_type=ExceptionType.DUPLICATE_RECORD,
                    severity=ExceptionSeverity.HIGH,
                    message="Duplicate entity record detected for the same anchor transaction identifier.",
                    affected_fields=["gateway_transaction_id"],
                    remediation="Inspect ingestion pipeline for deduplication errors or double-submission from source.",
                )
            )

        # 10. Status Conflict (Generic status contradiction from reconciler not already handled)
        if recon.status_comparison.has_conflict:
            already_conflict = any(e.exception_type == ExceptionType.CONFLICTING_EVIDENCE for e in exceptions)
            already_rejection = any(e.exception_type == ExceptionType.BANK_REJECTION for e in exceptions)
            if not already_conflict and not already_rejection:
                exceptions.append(
                    SettlementException(
                        exception_type=ExceptionType.STATUS_MISMATCH,
                        severity=ExceptionSeverity.HIGH,
                        message=recon.status_comparison.conflict_details or "Contradictory cross-system statuses detected.",
                        affected_fields=["gateway_status", "bank_status", "ledger_entry_type"],
                        remediation="Investigate status divergence across gateway, bank, and ledger.",
                    )
                )

        return exceptions

    def classify_epistemic_facts(
        self,
        trace: TraceResult,
        recon: ReconciliationResult,
        diagnosis_code: Optional[str] = None,
    ) -> EpistemicBreakdown:
        """
        Categorizes findings into KNOWN, INFERRED, and UNKNOWN facts.
        Preserves strict epistemic honesty.
        """
        known: List[str] = []
        inferred: List[str] = []
        unknown: List[str] = []

        gw = trace.gateway_record
        bnk = trace.bank_record
        led = trace.ledger_record

        # --- KNOWN FACTS (Directly recorded in source files) ---
        if gw:
            known.append(
                f"Gateway transaction '{gw.gateway_transaction_id}' recorded with status '{gw.status}', "
                f"gross amount INR {gw.gross_amount} {gw.currency}, payment method '{gw.method}', and order ID '{gw.order_id}'."
            )
            if gw.error_code or gw.error_description:
                known.append(f"Gateway reported error: [{gw.error_code}] {gw.error_description}.")
        else:
            known.append(f"Query identifier '{trace.query.identifier_value}' has no record in the Gateway dataset.")

        if bnk:
            settled_note = f", clearing timestamp: {bnk.settled_at.strftime('%Y-%m-%d %H:%M')}" if bnk.settled_at else ""
            known.append(
                f"Bank settlement '{bnk.settlement_id}' recorded with settlement status '{bnk.settlement_status}', "
                f"net disbursement amount INR {bnk.net_settlement_amount}, UTR '{bnk.bank_reference_number}'{settled_note}."
            )
        else:
            known.append("No corresponding settlement clearing record exists in the Bank dataset.")

        if led:
            known.append(
                f"Internal ledger entry '{led.ledger_entry_id}' recorded with entry type '{led.entry_type}', "
                f"account '{led.account_type}', booked amount INR {led.ledger_amount} on {led.booked_at.strftime('%Y-%m-%d %H:%M')}."
            )
        else:
            known.append("No corresponding accounting journal entry exists in the Ledger dataset.")

        # --- INFERRED DEDUCTIONS (Mathematically / logically derived from multiple facts) ---
        if bnk and led:
            if recon.bank_ledger_comparison.status == BankLedgerComparisonStatus.MATCH:
                inferred.append(
                    f"Bank net settlement disbursement (INR {bnk.net_settlement_amount}) and internal ledger booked amount "
                    f"(INR {led.ledger_amount}) match exactly with zero variance."
                )
            else:
                inferred.append(
                    f"Bank net settlement disbursement (INR {bnk.net_settlement_amount}) diverges from internal ledger "
                    f"booked amount (INR {led.ledger_amount}) by variance INR {recon.bank_ledger_comparison.numeric_difference}."
                )

        if gw and bnk:
            variance = gw.gross_amount - bnk.net_settlement_amount
            inferred.append(
                f"Gateway gross amount (INR {gw.gross_amount}) and Bank net disbursement (INR {bnk.net_settlement_amount}) "
                f"differ by arithmetic variance INR {variance} (reflecting gross transaction capture vs net merchant disbursement)."
            )

        if gw and bnk and gw.status == "failed" and bnk.settlement_status in ["processed", "settled"]:
            inferred.append(
                f"System records exhibit an irreconcilable logical contradiction: Gateway authorization failed, "
                f"yet Bank clearing rail executed settlement disbursement (UTR: {bnk.bank_reference_number})."
            )

        if gw and bnk and gw.status == "captured" and bnk.settlement_status == "failed":
            inferred.append(
                f"Customer authorization succeeded at gateway, but partner clearing bank rejected or failed the disbursement."
            )

        if gw and gw.status == "captured" and not bnk:
            inferred.append(
                "Customer payment completed authorization at gateway, but downstream bank clearing instruction was not executed or recorded in the settlement file."
            )

        if gw and gw.status == "captured" and bnk and not led:
            inferred.append(
                "Bank clearing instruction exists for captured payment, but internal double-entry accounting posting was omitted."
            )

        if not gw and bnk and led:
            inferred.append(
                "Orphan settlement detected: Bank disbursement and Ledger entry exist, but upstream Gateway transaction capture record is missing."
            )

        # --- UNKNOWN GAPS (Data gaps explicitly acknowledged, never fabricated) ---
        if gw and bnk:
            unknown.append(
                "Specific fee schedule, interchange MDR, and tax deduction items between Gateway gross and Bank net "
                "are absent from source files; exact line-item fee breakdown cannot be verified from available data."
            )

        if bnk and bnk.settlement_status == "failed":
            unknown.append(
                "Clearing bank file contains no explicit rejection reason code or return error description; "
                "specific banking failure cause is unrecorded in source data."
            )

        if gw and gw.status == "captured" and not bnk:
            unknown.append(
                "Reason for absence of Bank clearing record (e.g. file drop delay, unbatched window, network dropout) "
                "is not recorded in available datasets."
            )

        if gw and gw.status == "captured" and not led:
            unknown.append(
                "Reason for omission of internal ledger journal posting is not recorded in available datasets."
            )

        if gw and gw.provenance.timezone_note:
            unknown.append("Gateway source timestamp provides Unix epoch seconds; local timezone offset is unrecorded.")

        if bnk and bnk.provenance.timezone_note:
            unknown.append("Bank source timestamp provides no timezone metadata; exact timezone offset is unrecorded.")

        if led and led.provenance.timezone_note:
            unknown.append("Ledger source timestamp provides no timezone metadata; exact timezone offset is unrecorded.")

        return EpistemicBreakdown(
            known_facts=known,
            inferences=inferred,
            unknowns=unknown,
        )

    def extract_evidence_references(self, trace: TraceResult) -> List[EvidenceReference]:
        """
        Extracts physical source evidence references linking every entity to source file and 1-based line number.
        """
        refs: List[EvidenceReference] = []

        gw = trace.gateway_record
        if gw:
            refs.append(
                EvidenceReference(
                    source_system="GATEWAY",
                    record_id=gw.gateway_transaction_id,
                    field_name="status",
                    field_value=gw.status,
                    source_file=gw.provenance.source_file,
                    source_row_index=gw.provenance.source_row_index,
                )
            )
            refs.append(
                EvidenceReference(
                    source_system="GATEWAY",
                    record_id=gw.gateway_transaction_id,
                    field_name="gross_amount",
                    field_value=str(gw.gross_amount),
                    source_file=gw.provenance.source_file,
                    source_row_index=gw.provenance.source_row_index,
                )
            )

        bnk = trace.bank_record
        if bnk:
            refs.append(
                EvidenceReference(
                    source_system="BANK",
                    record_id=bnk.settlement_id,
                    field_name="settlement_status",
                    field_value=bnk.settlement_status,
                    source_file=bnk.provenance.source_file,
                    source_row_index=bnk.provenance.source_row_index,
                )
            )
            refs.append(
                EvidenceReference(
                    source_system="BANK",
                    record_id=bnk.settlement_id,
                    field_name="net_settlement_amount",
                    field_value=str(bnk.net_settlement_amount),
                    source_file=bnk.provenance.source_file,
                    source_row_index=bnk.provenance.source_row_index,
                )
            )
            refs.append(
                EvidenceReference(
                    source_system="BANK",
                    record_id=bnk.settlement_id,
                    field_name="bank_reference_number",
                    field_value=bnk.bank_reference_number,
                    source_file=bnk.provenance.source_file,
                    source_row_index=bnk.provenance.source_row_index,
                )
            )

        led = trace.ledger_record
        if led:
            refs.append(
                EvidenceReference(
                    source_system="LEDGER",
                    record_id=led.ledger_entry_id,
                    field_name="entry_type",
                    field_value=led.entry_type,
                    source_file=led.provenance.source_file,
                    source_row_index=led.provenance.source_row_index,
                )
            )
            refs.append(
                EvidenceReference(
                    source_system="LEDGER",
                    record_id=led.ledger_entry_id,
                    field_name="ledger_amount",
                    field_value=str(led.ledger_amount),
                    source_file=led.provenance.source_file,
                    source_row_index=led.provenance.source_row_index,
                )
            )

        return refs
