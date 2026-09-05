"""
server/reconciliation/engine.py

Deterministic Reconciliation Engine for PS-8 Settlement Q&A Agent (Phase 4).
Consumes Phase 3 TraceResult to establish structured financial comparison facts.
Adheres strictly to docs/rules.md:
- Pure Decimal arithmetic, zero float representation
- Preserves distinct monetary semantics: Gateway gross_amount, Bank net_settlement_amount, Ledger ledger_amount
- Does NOT classify Gateway gross != Bank net as an unexplained amount mismatch
- Does NOT manufacture zeroes for missing evidence
- Establishes factual status consistency/conflicts without root-cause diagnosis
"""

from decimal import Decimal
from typing import List, Optional, Literal

from server.tracing.models import TraceResult
from server.reconciliation.models import (
    BankLedgerComparisonStatus,
    GatewayBankComparisonStatus,
    StatusConsistencyStatus,
    BankLedgerComparison,
    GatewayBankComparison,
    StatusComparison,
    ReconciliationResult,
)
from server.reconciliation.exceptions import InvalidTraceResultError


class ReconciliationEngine:
    """Deterministic financial reconciliation engine operating strictly on TraceResult."""

    def reconcile(self, trace_result: TraceResult) -> ReconciliationResult:
        """
        Reconciles financial records from a Phase 3 TraceResult.
        Produces structured, deterministic comparison facts.
        """
        if trace_result is None or not isinstance(trace_result, TraceResult):
            raise InvalidTraceResultError("ReconciliationEngine requires a valid TraceResult instance.")

        gw = trace_result.gateway_record
        bnk = trace_result.bank_record
        led = trace_result.ledger_record

        gateway_present = gw is not None
        bank_present = bnk is not None
        ledger_present = led is not None
        evidence_complete = gateway_present and bank_present and ledger_present

        # Compute missing evidence
        missing_evidence: List[Literal["GATEWAY", "BANK", "LEDGER"]] = []
        if not gateway_present:
            missing_evidence.append("GATEWAY")
        if not bank_present:
            missing_evidence.append("BANK")
        if not ledger_present:
            missing_evidence.append("LEDGER")

        is_orphan = trace_result.is_orphan

        # Extract monetary amounts - NEVER manufacture zero for absent records
        gw_gross: Optional[Decimal] = gw.gross_amount if gw else None
        bnk_net: Optional[Decimal] = bnk.net_settlement_amount if bnk else None
        led_amt: Optional[Decimal] = led.ledger_amount if led else None

        # 1. Bank net settlement vs Ledger amount comparison (Directly Comparable)
        bank_ledger_comp = self._compare_bank_and_ledger(bnk_net, led_amt)

        # 2. Gateway gross vs Bank net comparison (Semantically Distinct)
        gateway_bank_comp = self._compare_gateway_and_bank(gw_gross, bnk_net)

        # 3. Status consistency audit
        status_comp = self._compare_statuses(gw, bnk, led)

        # 4. Currency identification
        currency = gw.currency if gw else "INR"

        return ReconciliationResult(
            transaction_id=trace_result.resolved_gateway_transaction_id or trace_result.query.identifier_value,
            gateway_present=gateway_present,
            bank_present=bank_present,
            ledger_present=ledger_present,
            evidence_complete=evidence_complete,
            missing_evidence=missing_evidence,
            is_orphan=is_orphan,
            gateway_gross_amount=gw_gross,
            bank_net_settlement_amount=bnk_net,
            ledger_amount=led_amt,
            bank_ledger_comparison=bank_ledger_comp,
            gateway_bank_comparison=gateway_bank_comp,
            status_comparison=status_comp,
            currency=currency,
            provenance_sources=trace_result.records_found,
        )

    def _compare_bank_and_ledger(
        self,
        bnk_net: Optional[Decimal],
        led_amt: Optional[Decimal],
    ) -> BankLedgerComparison:
        """Compares Bank net settlement disbursement against Ledger booked amount."""
        if bnk_net is not None and led_amt is not None:
            diff = bnk_net - led_amt
            if diff == Decimal("0"):
                return BankLedgerComparison(
                    bank_net_settlement_amount=bnk_net,
                    ledger_amount=led_amt,
                    status=BankLedgerComparisonStatus.MATCH,
                    numeric_difference=Decimal("0"),
                    is_match=True,
                    message=f"Bank net settlement amount ({bnk_net}) matches Ledger amount ({led_amt}) exactly.",
                )
            else:
                return BankLedgerComparison(
                    bank_net_settlement_amount=bnk_net,
                    ledger_amount=led_amt,
                    status=BankLedgerComparisonStatus.MISMATCH,
                    numeric_difference=diff,
                    is_match=False,
                    message=f"Bank net settlement amount ({bnk_net}) does not equal Ledger amount ({led_amt}). Variance: {diff}.",
                )
        else:
            return BankLedgerComparison(
                bank_net_settlement_amount=bnk_net,
                ledger_amount=led_amt,
                status=BankLedgerComparisonStatus.MISSING_EVIDENCE,
                numeric_difference=None,
                is_match=False,
                message="Bank net settlement amount and Ledger amount cannot be compared due to missing evidence.",
            )

    def _compare_gateway_and_bank(
        self,
        gw_gross: Optional[Decimal],
        bnk_net: Optional[Decimal],
    ) -> GatewayBankComparison:
        """
        Compares Gateway gross amount and Bank net disbursement.
        Crucial rule: Differences between gross and net reflect distinct financial semantics,
        not an unexplained amount mismatch. Even when numerically equal, gross and net
        represent distinct financial stages (gross transaction capture vs net settlement
        disbursement) and cannot be declared semantically equivalent or reconciled without
        explicit fee/deduction schedules.
        """
        if gw_gross is not None and bnk_net is not None:
            variance = gw_gross - bnk_net
            if variance == Decimal("0"):
                message = (
                    f"Gateway gross amount ({gw_gross}) and Bank net settlement amount ({bnk_net}) "
                    f"are numerically equal (variance 0). However, they represent distinct financial semantics "
                    f"(gross transaction capture vs net settlement disbursement); numerical equality does not "
                    f"constitute financial reconciliation because fee/deduction schedules are not present in source data."
                )
            else:
                message = (
                    f"Gateway gross amount ({gw_gross}) and Bank net settlement amount ({bnk_net}) "
                    f"differ by {variance}. This reflects distinct financial semantics (gross transaction capture vs "
                    f"net settlement disbursement); it is not classified as an unexplained amount mismatch "
                    f"because fee/deduction schedules are not present in source data."
                )
            return GatewayBankComparison(
                gateway_gross_amount=gw_gross,
                bank_net_settlement_amount=bnk_net,
                status=GatewayBankComparisonStatus.NOT_COMPARABLE_GROSS_VS_NET,
                gross_minus_net_variance=variance,
                message=message,
            )
        else:
            return GatewayBankComparison(
                gateway_gross_amount=gw_gross,
                bank_net_settlement_amount=bnk_net,
                status=GatewayBankComparisonStatus.MISSING_EVIDENCE,
                gross_minus_net_variance=None,
                message="Gateway gross amount and Bank net settlement amount cannot be compared due to missing evidence.",
            )

    def _compare_statuses(self, gw, bnk, led) -> StatusComparison:
        """Audits cross-system statuses for factual consistency or conflict."""
        gw_status = gw.status if gw else None
        bnk_status = bnk.settlement_status if bnk else None
        led_type = led.entry_type if led else None

        present_count = sum(1 for s in [gw_status, bnk_status, led_type] if s is not None)

        if present_count < 2:
            return StatusComparison(
                gateway_status=gw_status,
                bank_status=bnk_status,
                ledger_entry_type=led_type,
                status_consistency=StatusConsistencyStatus.INSUFFICIENT_DATA,
                is_consistent=True,
                has_conflict=False,
                conflict_details=None,
                message="Single system evidence; cross-system status consistency cannot be evaluated.",
            )

        # Factual conflict detection: Gateway failed while Bank processed
        if gw_status == "failed" and bnk_status == "processed":
            return StatusComparison(
                gateway_status=gw_status,
                bank_status=bnk_status,
                ledger_entry_type=led_type,
                status_consistency=StatusConsistencyStatus.CONFLICT,
                is_consistent=False,
                has_conflict=True,
                conflict_details="Gateway records transaction as 'failed', but Bank records settlement as 'processed'.",
                message="Status conflict: Gateway payment failed but Bank settlement processed.",
            )

        # Factual conflict detection: Gateway captured while Bank failed
        if gw_status == "captured" and bnk_status == "failed":
            return StatusComparison(
                gateway_status=gw_status,
                bank_status=bnk_status,
                ledger_entry_type=led_type,
                status_consistency=StatusConsistencyStatus.CONFLICT,
                is_consistent=False,
                has_conflict=True,
                conflict_details="Gateway records transaction as 'captured', but Bank records settlement as 'failed'.",
                message="Status conflict: Gateway payment captured but Bank settlement failed.",
            )

        # Standard consistent flow
        return StatusComparison(
            gateway_status=gw_status,
            bank_status=bnk_status,
            ledger_entry_type=led_type,
            status_consistency=StatusConsistencyStatus.CONSISTENT,
            is_consistent=True,
            has_conflict=False,
            conflict_details=None,
            message="Statuses are consistent across present records.",
        )


def reconcile_trace(trace_result: TraceResult) -> ReconciliationResult:
    """Convenience functional interface for reconciling a TraceResult."""
    engine = ReconciliationEngine()
    return engine.reconcile(trace_result)
