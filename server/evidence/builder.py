"""
server/evidence/builder.py

Builder engine for PS-8 Verified Evidence Packs (Phase 6).
Aggregates deterministic outputs from Phases 2-5 into an immutable VerifiedEvidencePack (VEO):
- Consumes TraceResult (Phase 3), ReconciliationResult (Phase 4), and DiagnosisResult (Phase 5)
- Reconstructs chronological multi-system event timeline
- Preserves all physical evidence references with 1-based CSV line numbers
- Preserves multi-exception lists and the Tri-State Epistemic Model
- Generates a deterministic SHA-256 cryptographic integrity hash
- Guarantees zero float conversions and zero fabricated facts
"""

import json
from decimal import Decimal
from typing import List, Optional

from server.tracing.models import TraceResult
from server.reconciliation.models import ReconciliationResult
from server.reconciliation.engine import reconcile_trace
from server.diagnosis.models import DiagnosisResult
from server.diagnosis.engine import diagnose_transaction
from server.evidence.models import (
    TimelineEvent,
    GatewayEvidence,
    BankEvidence,
    LedgerEvidence,
    ReconciliationSummary,
    VerifiedEvidencePack,
)
from server.evidence.validator import EvidenceValidator
from server.evidence.exceptions import InvalidEvidenceInputError


class EvidencePackBuilder:
    """
    Deterministic builder for assembling and validating Verified Evidence Packs.
    Packages verified conclusions from Phases 2-5 without altering or recomputing them.
    """

    def __init__(self, validator: Optional[EvidenceValidator] = None):
        self.validator = validator or EvidenceValidator()

    def build(
        self,
        trace: TraceResult,
        recon: Optional[ReconciliationResult] = None,
        diagnosis: Optional[DiagnosisResult] = None,
    ) -> VerifiedEvidencePack:
        """
        Builds a canonical VerifiedEvidencePack from investigation results.
        If recon or diagnosis are omitted, computes them via their canonical deterministic engines.
        """
        if not isinstance(trace, TraceResult):
            raise InvalidEvidenceInputError(
                f"Expected TraceResult instance, got {type(trace).__name__}"
            )

        if recon is None:
            recon = reconcile_trace(trace)
        if diagnosis is None:
            diagnosis = diagnose_transaction(trace, recon)

        # Validate upstream inputs
        self.validator.validate_inputs(trace, recon, diagnosis)

        txn_id = (
            trace.resolved_gateway_transaction_id
            or recon.transaction_id
            or diagnosis.transaction_id
            or trace.query.identifier_value
        )
        veo_id = f"veo_{txn_id}"

        # 1. Gateway Evidence Packaging
        gw = trace.gateway_record
        if gw is not None:
            gateway_evidence = GatewayEvidence(
                present=True,
                transaction_id=gw.gateway_transaction_id,
                order_id=gw.order_id,
                gross_amount=gw.gross_amount,
                currency=gw.currency,
                method=gw.method,
                status=gw.status,
                error_code=gw.error_code,
                error_description=gw.error_description,
                captured_at=gw.created_at,
                provenance=gw.provenance,
                record=gw,
            )
        else:
            gateway_evidence = GatewayEvidence(present=False)

        # 2. Bank Evidence Packaging
        bnk = trace.bank_record
        if bnk is not None:
            bank_evidence = BankEvidence(
                present=True,
                settlement_id=bnk.settlement_id,
                gateway_transaction_id=bnk.gateway_transaction_id,
                net_settlement_amount=bnk.net_settlement_amount,
                bank_reference_number=bnk.bank_reference_number,
                settlement_status=bnk.settlement_status,
                settled_at=bnk.settled_at,
                provenance=bnk.provenance,
                record=bnk,
            )
        else:
            bank_evidence = BankEvidence(present=False)

        # 3. Ledger Evidence Packaging
        led = trace.ledger_record
        if led is not None:
            ledger_evidence = LedgerEvidence(
                present=True,
                ledger_entry_id=led.ledger_entry_id,
                gateway_transaction_id=led.gateway_transaction_id,
                account_type=led.account_type,
                entry_type=led.entry_type,
                ledger_amount=led.ledger_amount,
                booked_at=led.booked_at,
                provenance=led.provenance,
                record=led,
            )
        else:
            ledger_evidence = LedgerEvidence(present=False)

        # 4. Reconciliation Summary Packaging
        reconciliation_summary = ReconciliationSummary(
            bank_ledger_match=recon.bank_ledger_comparison.is_match,
            bank_ledger_status=recon.bank_ledger_comparison.status,
            bank_ledger_numeric_diff=recon.bank_ledger_comparison.numeric_difference,
            gateway_bank_status=recon.gateway_bank_comparison.status,
            gross_minus_net_variance=recon.gateway_bank_comparison.gross_minus_net_variance,
            status_consistency=recon.status_comparison.status_consistency,
            has_status_conflict=recon.status_comparison.has_conflict,
            conflict_details=recon.status_comparison.conflict_details,
            currency=recon.currency or "INR",
            provenance_sources=recon.provenance_sources,
        )

        # 5. Multi-System Chronological Timeline
        timeline = self.build_timeline(trace)

        # 6. Build pre-integrity pack to compute cryptographic hash
        pre_pack = VerifiedEvidencePack(
            schema_version="1.0.0",
            veo_id=veo_id,
            transaction_id=txn_id,
            query_identifier=trace.query.identifier_value,
            query_type=trace.query.identifier_type.value,
            diagnosis=diagnosis.diagnosis_code,
            confidence=diagnosis.confidence,
            confidence_reason=diagnosis.confidence_reason,
            severity=diagnosis.severity,
            status=diagnosis.status,
            summary=diagnosis.summary,
            recommended_next_action=diagnosis.recommended_next_action,
            primary_exception=diagnosis.primary_exception,
            exceptions=diagnosis.exceptions,
            gateway=gateway_evidence,
            bank=bank_evidence,
            ledger=ledger_evidence,
            reconciliation=reconciliation_summary,
            epistemic_model=diagnosis.epistemic_facts,
            resolution_path=trace.resolution,
            records_found=trace.records_found,
            missing_records=trace.missing_records,
            is_complete_chain=trace.is_complete_chain,
            is_orphan=trace.is_orphan,
            evidence_refs=diagnosis.evidence_refs,
            timeline=timeline,
            integrity_hash="PENDING_COMPUTATION",
        )

        # 7. Compute deterministic integrity hash
        integrity_hash = self.validator.compute_integrity_hash(pre_pack)

        # 8. Return final frozen VerifiedEvidencePack
        final_pack = pre_pack.model_copy(update={"integrity_hash": integrity_hash})

        # 9. Perform post-construction integrity check
        self.validator.validate_pack(final_pack, trace)

        return final_pack

    def build_timeline(self, trace: TraceResult) -> List[TimelineEvent]:
        """
        Reconstructs a deterministic chronological timeline of cross-system events.
        Events with timestamps are ordered sequentially; missing/pending events follow deterministically.
        """
        events: List[TimelineEvent] = []
        gw = trace.gateway_record
        bnk = trace.bank_record
        led = trace.ledger_record

        # Gateway Event
        if gw is not None:
            gw_time = gw.created_at.isoformat() if gw.created_at else "UNRECORDED"
            gw_title = f"Payment {gw.status.capitalize()} (INR {gw.gross_amount})"
            gw_details = f"Order ID: {gw.order_id}, Method: {gw.method}"
            if gw.error_code:
                gw_details += f", Error: {gw.error_code}"
            events.append(
                TimelineEvent(
                    timestamp=gw_time,
                    system="GATEWAY",
                    event=gw_title,
                    details=gw_details,
                    source_row_index=gw.provenance.source_row_index,
                )
            )

        # Ledger Event
        if led is not None:
            led_time = led.booked_at.isoformat() if led.booked_at else "UNRECORDED"
            led_title = f"Ledger Journal Posted ({led.entry_type.upper()}: INR {led.ledger_amount})"
            led_details = f"Entry ID: {led.ledger_entry_id}, Account: {led.account_type}"
            events.append(
                TimelineEvent(
                    timestamp=led_time,
                    system="LEDGER",
                    event=led_title,
                    details=led_details,
                    source_row_index=led.provenance.source_row_index,
                )
            )
        elif gw is not None and gw.status == "captured":
            events.append(
                TimelineEvent(
                    timestamp="UNRECORDED",
                    system="LEDGER",
                    event="Ledger Journal Entry Missing",
                    details="No double-entry journal posting found in ledger dataset.",
                    source_row_index=None,
                )
            )

        # Bank Event
        if bnk is not None:
            if bnk.settled_at is not None:
                bnk_time = bnk.settled_at.isoformat()
            elif bnk.settlement_status == "pending":
                bnk_time = "PENDING"
            else:
                bnk_time = "UNRECORDED"

            bnk_title = f"Bank Settlement {bnk.settlement_status.capitalize()}"
            if bnk.net_settlement_amount is not None:
                bnk_title += f" (INR {bnk.net_settlement_amount})"
            bnk_details = f"Settlement ID: {bnk.settlement_id}, UTR: {bnk.bank_reference_number or 'UNASSIGNED'}"
            events.append(
                TimelineEvent(
                    timestamp=bnk_time,
                    system="BANK",
                    event=bnk_title,
                    details=bnk_details,
                    source_row_index=bnk.provenance.source_row_index,
                )
            )
        elif gw is not None and gw.status == "captured":
            events.append(
                TimelineEvent(
                    timestamp="UNRECORDED",
                    system="BANK",
                    event="Bank Settlement Record Missing",
                    details="No clearing record found in bank dataset for this transaction.",
                    source_row_index=None,
                )
            )

        # Deterministic chronological sort:
        # 1. Events with valid ISO timestamps sorted chronologically
        # 2. Events with "PENDING" or "UNRECORDED" timestamps placed deterministically at the end
        def sort_key(e: TimelineEvent):
            if e.timestamp and e.timestamp not in ["PENDING", "UNRECORDED"]:
                return (0, e.timestamp, e.system)
            elif e.timestamp == "PENDING":
                return (1, "PENDING", e.system)
            else:
                return (2, "UNRECORDED", e.system)

        events.sort(key=sort_key)
        return events


def build_evidence_pack(
    trace: TraceResult,
    recon: Optional[ReconciliationResult] = None,
    diagnosis: Optional[DiagnosisResult] = None,
) -> VerifiedEvidencePack:
    """Convenience functional interface for building a verified evidence pack."""
    builder = EvidencePackBuilder()
    return builder.build(trace, recon, diagnosis)
