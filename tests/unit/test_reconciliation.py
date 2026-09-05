"""
tests/unit/test_reconciliation.py

Comprehensive unit tests for PS-8 Deterministic Reconciliation Engine (Phase 4).
Covers:
- Case 1: Complete normal transaction (pay_Gz8x1001)
- Case 2: Gateway-only (pay_Gz8x1000)
- Case 3: Missing Ledger (pay_Gz8x1038)
- Case 4: Bank rejection (pay_Gz8x1042)
- Case 5: Conflicting evidence (pay_Gz8x1052, pay_Gz8x1061, pay_Gz8x1066)
- Case 6: Orphan Bank + Ledger (pay_Gz8x1100)
- Dataset-wide invariants:
  1. All 88 Bank/Ledger pairs match exactly
  2. Gateway gross vs Bank net is NEVER classified as an unexplained amount mismatch
  3. Missing records remain None (no manufactured zeroes)
  4. Zero float conversions across all monetary arithmetic
  5. Status conflicts are deterministic
  6. Orphan records remain identifiable
  7. Deterministic idempotency (repeated calls yield identical results)
  8. Raw CSV files remain untouched
  9. Invalid input handling
"""

from datetime import datetime, timezone
import hashlib
from decimal import Decimal
from pathlib import Path
import pytest

from server.models.domain import GatewayRecord, BankRecord, SourceProvenance
from server.ingestion.data_store import DataStore
from server.tracing.models import TraceResult, TraceQuery, IdentifierType, ResolutionPath
from server.tracing.trace_engine import TraceEngine
from server.reconciliation.engine import ReconciliationEngine, reconcile_trace
from server.reconciliation.models import (
    BankLedgerComparisonStatus,
    GatewayBankComparisonStatus,
    StatusConsistencyStatus,
    ReconciliationResult,
)
from server.reconciliation.exceptions import InvalidTraceResultError

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

EXPECTED_HASHES = {
    "gateway.csv": "8945186e3ded7e81b21834e1c5312656fdb3da1af0fd011d7768a2758f24bcff",
    "bank.csv": "6db6886b96b1fd642a0a3df1d009bcbf93750090aaea8180a7cc4386c358edc4",
    "ledger.csv": "89c5bfb92be8a81f45abfe07975affe711b54009daf59453951c54251722f504",
}


@pytest.fixture(scope="module")
def loaded_store():
    store = DataStore()
    store.load_from_directory(DATA_DIR)
    return store


@pytest.fixture(scope="module")
def tracer(loaded_store):
    return TraceEngine(data_store=loaded_store)


@pytest.fixture(scope="module")
def engine():
    return ReconciliationEngine()


# Case 1 — Complete normal transaction (pay_Gz8x1001)
def test_reconcile_complete_normal_transaction(tracer, engine):
    trace = tracer.trace("pay_Gz8x1001")
    res = engine.reconcile(trace)

    assert isinstance(res, ReconciliationResult)
    assert res.transaction_id == "pay_Gz8x1001"
    assert res.gateway_present is True
    assert res.bank_present is True
    assert res.ledger_present is True
    assert res.evidence_complete is True
    assert res.missing_evidence == []
    assert res.is_orphan is False

    # Amounts: Gateway gross, Bank net, Ledger amount
    assert res.gateway_gross_amount == Decimal("111358")
    assert res.bank_net_settlement_amount == Decimal("38261")
    assert res.ledger_amount == Decimal("38261")

    # Bank vs Ledger must match exactly
    assert res.bank_ledger_comparison.status == BankLedgerComparisonStatus.MATCH
    assert res.bank_ledger_comparison.is_match is True
    assert res.bank_ledger_comparison.numeric_difference == Decimal("0")

    # Gateway gross vs Bank net reflects distinct financial semantics, NOT unexplained mismatch
    assert res.gateway_bank_comparison.status == GatewayBankComparisonStatus.NOT_COMPARABLE_GROSS_VS_NET
    assert res.gateway_bank_comparison.gross_minus_net_variance == Decimal("73097")
    assert "distinct financial semantics" in res.gateway_bank_comparison.message

    # Status consistency
    assert res.status_comparison.is_consistent is True
    assert res.status_comparison.has_conflict is False
    assert res.status_comparison.status_consistency == StatusConsistencyStatus.CONSISTENT


# Case 2 — Gateway-only transaction (pay_Gz8x1000)
def test_reconcile_gateway_only_transaction(tracer, engine):
    trace = tracer.trace("pay_Gz8x1000")
    res = engine.reconcile(trace)

    assert res.gateway_present is True
    assert res.bank_present is False
    assert res.ledger_present is False
    assert res.evidence_complete is False
    assert set(res.missing_evidence) == {"BANK", "LEDGER"}
    assert res.is_orphan is False

    # Critical rule: Missing evidence is NOT manufactured as zero
    assert res.gateway_gross_amount == Decimal("17588")
    assert res.bank_net_settlement_amount is None
    assert res.ledger_amount is None

    # Comparisons requiring missing records become MISSING_EVIDENCE
    assert res.bank_ledger_comparison.status == BankLedgerComparisonStatus.MISSING_EVIDENCE
    assert res.bank_ledger_comparison.is_match is False
    assert res.bank_ledger_comparison.numeric_difference is None

    assert res.gateway_bank_comparison.status == GatewayBankComparisonStatus.MISSING_EVIDENCE
    assert res.gateway_bank_comparison.gross_minus_net_variance is None

    # Status consistency for single record
    assert res.status_comparison.status_consistency == StatusConsistencyStatus.INSUFFICIENT_DATA
    assert res.status_comparison.has_conflict is False


# Case 3 — Missing Ledger (pay_Gz8x1038)
def test_reconcile_missing_ledger_transaction(tracer, engine):
    trace = tracer.trace("pay_Gz8x1038")
    res = engine.reconcile(trace)

    assert res.gateway_present is True
    assert res.bank_present is True
    assert res.ledger_present is False
    assert res.evidence_complete is False
    assert res.missing_evidence == ["LEDGER"]
    assert res.is_orphan is False

    assert res.gateway_gross_amount == Decimal("57466")
    assert res.bank_net_settlement_amount == Decimal("45171")
    assert res.ledger_amount is None

    # Gateway gross vs Bank net reflects distinct financial semantics
    assert res.gateway_bank_comparison.status == GatewayBankComparisonStatus.NOT_COMPARABLE_GROSS_VS_NET
    assert res.gateway_bank_comparison.gross_minus_net_variance == Decimal("12295")

    # Bank/Ledger comparison is MISSING_EVIDENCE (not a monetary mismatch)
    assert res.bank_ledger_comparison.status == BankLedgerComparisonStatus.MISSING_EVIDENCE
    assert res.bank_ledger_comparison.is_match is False

    # Status consistency
    assert res.status_comparison.is_consistent is True
    assert res.status_comparison.has_conflict is False


# Case 4 — Bank rejection (pay_Gz8x1042)
def test_reconcile_bank_rejection(tracer, engine):
    trace = tracer.trace("pay_Gz8x1042")
    res = engine.reconcile(trace)

    assert res.gateway_present is True
    assert res.bank_present is True
    assert res.ledger_present is False
    assert res.missing_evidence == ["LEDGER"]

    # Bank status is failed while Gateway status is captured -> conflict
    assert res.status_comparison.gateway_status == "captured"
    assert res.status_comparison.bank_status == "failed"
    assert res.status_comparison.has_conflict is True
    assert res.status_comparison.is_consistent is False
    assert res.status_comparison.status_consistency == StatusConsistencyStatus.CONFLICT
    assert "Gateway records transaction as 'captured', but Bank records settlement as 'failed'" in res.status_comparison.conflict_details

    # Reconciler does not assign root cause diagnosis
    assert not hasattr(res, "diagnosis")


# Case 5 — Conflicting evidence (pay_Gz8x1052, pay_Gz8x1061, pay_Gz8x1066)
def test_reconcile_conflicting_evidence_status_conflict(tracer, engine):
    for txn_id in ["pay_Gz8x1052", "pay_Gz8x1061", "pay_Gz8x1066"]:
        trace = tracer.trace(txn_id)
        res = engine.reconcile(trace)

        assert res.gateway_present is True
        assert res.bank_present is True
        assert res.ledger_present is True
        assert res.status_comparison.gateway_status == "failed"
        assert res.status_comparison.bank_status == "processed"
        assert res.status_comparison.ledger_entry_type == "credit"
        assert res.status_comparison.has_conflict is True
        assert res.status_comparison.is_consistent is False
        assert res.status_comparison.status_consistency == StatusConsistencyStatus.CONFLICT
        assert "Gateway records transaction as 'failed', but Bank records settlement as 'processed'" in res.status_comparison.conflict_details

        # Bank and Ledger still match numerically
        assert res.bank_ledger_comparison.status == BankLedgerComparisonStatus.MATCH
        assert res.bank_ledger_comparison.is_match is True

        # Reconciler does NOT diagnose why conflict occurred
        assert not hasattr(res, "settlement_diagnosis")


# Case 6 — Orphan Bank + Ledger (pay_Gz8x1100)
def test_reconcile_orphan_bank_and_ledger(tracer, engine):
    trace = tracer.trace("pay_Gz8x1100")
    res = engine.reconcile(trace)

    assert res.gateway_present is False
    assert res.bank_present is True
    assert res.ledger_present is True
    assert res.is_orphan is True
    assert res.missing_evidence == ["GATEWAY"]

    # Gateway gross amount is None, not manufactured zero
    assert res.gateway_gross_amount is None
    assert res.bank_net_settlement_amount == Decimal("40450")
    assert res.ledger_amount == Decimal("40450")

    # Bank vs Ledger matches exactly
    assert res.bank_ledger_comparison.status == BankLedgerComparisonStatus.MATCH
    assert res.bank_ledger_comparison.is_match is True
    assert res.bank_ledger_comparison.numeric_difference == Decimal("0")

    # Gateway vs Bank is MISSING_EVIDENCE
    assert res.gateway_bank_comparison.status == GatewayBankComparisonStatus.MISSING_EVIDENCE
    assert res.gateway_bank_comparison.gross_minus_net_variance is None


# Dataset-wide invariant 1: All 88 present Bank/Ledger pairs match exactly
def test_dataset_wide_bank_ledger_exact_equality(tracer, engine, loaded_store):
    all_txn_ids = loaded_store.get_all_transaction_ids()
    compared_count = 0

    for txn_id in all_txn_ids:
        trace = tracer.trace(txn_id)
        res = engine.reconcile(trace)

        if res.bank_present and res.ledger_present:
            compared_count += 1
            assert res.bank_ledger_comparison.status == BankLedgerComparisonStatus.MATCH
            assert res.bank_ledger_comparison.is_match is True
            assert res.bank_ledger_comparison.numeric_difference == Decimal("0")
            assert res.bank_net_settlement_amount == res.ledger_amount

    assert compared_count == 88, f"Expected 88 compared Bank/Ledger pairs, got {compared_count}"


# Dataset-wide invariant 2: Gateway gross vs Bank net is positively classified as NOT_COMPARABLE_GROSS_VS_NET
def test_dataset_wide_no_gross_net_mismatch_misclassification(tracer, engine, loaded_store):
    all_txn_ids = loaded_store.get_all_transaction_ids()
    both_present_count = 0
    missing_evidence_count = 0

    for txn_id in all_txn_ids:
        trace = tracer.trace(txn_id)
        res = engine.reconcile(trace)

        if res.gateway_present and res.bank_present:
            both_present_count += 1
            # Positive assertion: MUST be NOT_COMPARABLE_GROSS_VS_NET
            assert res.gateway_bank_comparison.status == GatewayBankComparisonStatus.NOT_COMPARABLE_GROSS_VS_NET
            # Variance must be exact Decimal difference: gross - net
            expected_variance = res.gateway_gross_amount - res.bank_net_settlement_amount
            assert res.gateway_bank_comparison.gross_minus_net_variance == expected_variance
            assert isinstance(res.gateway_bank_comparison.gross_minus_net_variance, Decimal)
        else:
            missing_evidence_count += 1
            assert res.gateway_bank_comparison.status == GatewayBankComparisonStatus.MISSING_EVIDENCE
            assert res.gateway_bank_comparison.gross_minus_net_variance is None

    assert both_present_count == 89, f"Expected 89 transactions with both Gateway and Bank, got {both_present_count}"
    assert missing_evidence_count == 12, f"Expected 12 transactions with missing Gateway or Bank, got {missing_evidence_count}"


# Equal numeric gross/net edge case: 500 gross == 500 net remains NOT_COMPARABLE_GROSS_VS_NET
def test_equal_numeric_gross_net_remains_not_comparable(engine):
    """
    Critical regression test:
    Gateway gross and Bank net remain distinct financial semantics even when
    numerically equal (e.g. 500 gross == 500 net).
    Numerical equality does NOT constitute financial reconciliation.
    Status must be NOT_COMPARABLE_GROSS_VS_NET with gross_minus_net_variance == Decimal("0").
    """
    # 1. Test direct engine helper method
    comp = engine._compare_gateway_and_bank(Decimal("500"), Decimal("500"))
    assert comp.status == GatewayBankComparisonStatus.NOT_COMPARABLE_GROSS_VS_NET
    assert comp.gross_minus_net_variance == Decimal("0")
    assert isinstance(comp.gross_minus_net_variance, Decimal)
    assert "numerically equal" in comp.message
    assert "distinct financial semantics" in comp.message

    # 2. Test via full engine.reconcile() with a constructed TraceResult
    mock_query = TraceQuery(
        identifier_value="pay_mock_equal_500",
        identifier_type=IdentifierType.GATEWAY_TRANSACTION_ID,
    )
    mock_resolution = ResolutionPath(
        steps=[],
        resolved_gateway_transaction_id="pay_mock_equal_500",
        path_summary="Direct mock resolution",
    )
    mock_prov_gw = SourceProvenance(
        source_system="GATEWAY",
        source_file="gateway.csv",
        source_row_index=2,
    )
    mock_prov_bnk = SourceProvenance(
        source_system="BANK",
        source_file="bank.csv",
        source_row_index=2,
    )
    gw_record = GatewayRecord(
        gateway_transaction_id="pay_mock_equal_500",
        order_id="order_mock_1",
        gross_amount=Decimal("500"),
        raw_amount=500,
        currency="INR",
        method="upi",
        status="captured",
        source_status="captured",
        created_at=datetime.now(timezone.utc),
        provenance=mock_prov_gw,
    )
    bnk_record = BankRecord(
        settlement_id="set_mock_1",
        gateway_transaction_id="pay_mock_equal_500",
        net_settlement_amount=Decimal("500"),
        raw_amount=500,
        bank_reference_number="UTR_MOCK_500",
        settlement_status="processed",
        source_status="processed",
        settled_at=datetime.now(timezone.utc),
        provenance=mock_prov_bnk,
    )
    trace = TraceResult(
        query=mock_query,
        resolution=mock_resolution,
        resolved_gateway_transaction_id="pay_mock_equal_500",
        gateway_record=gw_record,
        bank_record=bnk_record,
        ledger_record=None,
        records_found=["GATEWAY", "BANK"],
        missing_records=["LEDGER"],
        is_complete_chain=False,
        is_orphan=False,
        has_conflicting_statuses=False,
    )

    res = engine.reconcile(trace)
    assert res.gateway_gross_amount == Decimal("500")
    assert res.bank_net_settlement_amount == Decimal("500")
    assert res.gateway_bank_comparison.status == GatewayBankComparisonStatus.NOT_COMPARABLE_GROSS_VS_NET
    assert res.gateway_bank_comparison.gross_minus_net_variance == Decimal("0")
    assert isinstance(res.gateway_bank_comparison.gross_minus_net_variance, Decimal)
    assert "distinct financial semantics" in res.gateway_bank_comparison.message


# Dataset-wide invariant 3: Missing records remain None (no manufactured zeroes)
def test_dataset_wide_no_manufactured_zeroes(tracer, engine, loaded_store):
    all_txn_ids = loaded_store.get_all_transaction_ids()

    for txn_id in all_txn_ids:
        trace = tracer.trace(txn_id)
        res = engine.reconcile(trace)

        if not res.gateway_present:
            assert res.gateway_gross_amount is None
        if not res.bank_present:
            assert res.bank_net_settlement_amount is None
        if not res.ledger_present:
            assert res.ledger_amount is None


# Dataset-wide invariant 4: Zero float conversions across all monetary arithmetic
def test_dataset_wide_zero_float_conversions(tracer, engine, loaded_store):
    all_txn_ids = loaded_store.get_all_transaction_ids()

    for txn_id in all_txn_ids:
        trace = tracer.trace(txn_id)
        res = engine.reconcile(trace)

        for amt in [res.gateway_gross_amount, res.bank_net_settlement_amount, res.ledger_amount]:
            if amt is not None:
                assert isinstance(amt, Decimal), f"Expected Decimal, got {type(amt)}"
                assert not isinstance(amt, float)

        if res.bank_ledger_comparison.numeric_difference is not None:
            assert isinstance(res.bank_ledger_comparison.numeric_difference, Decimal)

        if res.gateway_bank_comparison.gross_minus_net_variance is not None:
            assert isinstance(res.gateway_bank_comparison.gross_minus_net_variance, Decimal)


# Dataset-wide invariant 5: Status conflicts are deterministic
def test_dataset_wide_status_conflicts_deterministic(tracer, engine, loaded_store):
    all_txn_ids = loaded_store.get_all_transaction_ids()
    conflicts = []

    for txn_id in sorted(list(all_txn_ids)):
        trace = tracer.trace(txn_id)
        res = engine.reconcile(trace)
        if res.status_comparison.has_conflict:
            conflicts.append(txn_id)

    # In current dataset: 3 conflicts where GW failed + Bank processed, plus 1 where GW captured + Bank failed
    assert "pay_Gz8x1052" in conflicts
    assert "pay_Gz8x1061" in conflicts
    assert "pay_Gz8x1066" in conflicts
    assert "pay_Gz8x1042" in conflicts
    assert len(conflicts) == 4


# Dataset-wide invariant 6: Deterministic repeated reconciliation (idempotency)
def test_reconciliation_idempotency(tracer, engine):
    trace = tracer.trace("pay_Gz8x1001")
    res1 = engine.reconcile(trace)
    res2 = engine.reconcile(trace)
    assert res1.model_dump() == res2.model_dump()

    # Functional interface matches class interface
    res_func = reconcile_trace(trace)
    assert res1.model_dump() == res_func.model_dump()


# Error handling: Invalid trace input
def test_reconciliation_invalid_input(engine):
    with pytest.raises(InvalidTraceResultError):
        engine.reconcile(None)

    with pytest.raises(InvalidTraceResultError):
        engine.reconcile("not_a_trace_result")


# Raw CSV immutability verification
def test_raw_csv_immutability_after_reconciliation():
    for filename, expected_hash in EXPECTED_HASHES.items():
        filepath = DATA_DIR / filename
        assert filepath.exists(), f"File missing: {filepath}"
        content = filepath.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {filename}!"
