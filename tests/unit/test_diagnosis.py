"""
tests/unit/test_diagnosis.py

Comprehensive unit and edge-case tests for PS-8 Diagnosis & Exception Engine (Phase 5).
Covers:
- Scenario 1: Clean resolved settlement (pay_Gz8x1001)
- Scenario 2: Gateway-only missing bank (pay_Gz8x1000)
- Scenario 3: Missing Ledger entry (pay_Gz8x1038)
- Scenario 4: Bank rejection (pay_Gz8x1042)
- Scenario 5: Conflicting evidence (pay_Gz8x1052, pay_Gz8x1061, pay_Gz8x1066)
- Scenario 6: Orphan Bank + Ledger insufficient evidence (pay_Gz8x1100)
- Scenario 7: Isolated Gateway failure (terminal authorization failure)
- Scenario 8: Isolated Settlement pending (bank clearing in-flight)
- Scenario 9: Isolated Amount mismatch (disbursement != ledger booking)
- Scenario 10: Isolated Duplicate record detection
- Scenario 11: Isolated Reference mismatch detection
- Epistemic honesty: strict separation of KNOWN vs INFERRED vs UNKNOWN
- Physical evidence reference linkage to 1-based CSV line numbers
- Multiple coexisting exceptions preservation
- Dataset-wide distribution and determinism across all 101 transactions
- Idempotency and functional interface parity
- Invalid input error handling
- Raw CSV file immutability verification
"""

import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest

from server.models.domain import GatewayRecord, BankRecord, LedgerRecord, SourceProvenance
from server.ingestion.data_store import DataStore
from server.tracing.models import TraceResult, TraceQuery, IdentifierType, ResolutionPath
from server.tracing.trace_engine import TraceEngine
from server.reconciliation.engine import ReconciliationEngine, reconcile_trace
from server.reconciliation.models import (
    ReconciliationResult,
    BankLedgerComparison,
    GatewayBankComparison,
    StatusComparison,
    BankLedgerComparisonStatus,
    GatewayBankComparisonStatus,
    StatusConsistencyStatus,
)
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
from server.diagnosis.engine import DiagnosisEngine, diagnose_transaction
from server.diagnosis.exceptions import InvalidDiagnosisInputError

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
def diag_engine():
    return DiagnosisEngine()


# --- Case 1: Clean resolved settlement (pay_Gz8x1001) ---
def test_diagnose_complete_settled_transaction(tracer, diag_engine):
    trace = tracer.trace("pay_Gz8x1001")
    res = diag_engine.diagnose(trace)

    assert isinstance(res, DiagnosisResult)
    assert res.transaction_id == "pay_Gz8x1001"
    assert res.diagnosis_code == SettlementDiagnosis.SUCCESSFULLY_SETTLED
    assert res.confidence == ConfidenceLevel.HIGH
    assert res.severity == ExceptionSeverity.NONE
    assert res.status == InvestigationStatus.RESOLVED
    assert res.exception_type == ExceptionType.NONE
    assert res.primary_exception is None
    assert len(res.exceptions) == 0
    assert "fully settled and reconciled" in res.summary
    assert "No operational action required" in res.recommended_next_action

    # Epistemic facts
    assert len(res.known_facts) >= 3
    assert len(res.inferences) >= 2
    assert len(res.unknowns) >= 1
    # Evidence refs
    assert len(res.evidence_refs) >= 5
    assert any(ref.source_system == "GATEWAY" for ref in res.evidence_refs)
    assert any(ref.source_system == "BANK" for ref in res.evidence_refs)
    assert any(ref.source_system == "LEDGER" for ref in res.evidence_refs)


# --- Case 2: Gateway-only missing bank (pay_Gz8x1000) ---
def test_diagnose_gateway_only_missing_bank(tracer, diag_engine):
    trace = tracer.trace("pay_Gz8x1000")
    res = diag_engine.diagnose(trace)

    assert res.diagnosis_code == SettlementDiagnosis.MISSING_BANK_RECORD
    assert res.confidence == ConfidenceLevel.LOW
    assert res.severity == ExceptionSeverity.HIGH
    assert res.status == InvestigationStatus.EXCEPTION
    assert res.primary_exception is not None
    assert res.primary_exception.exception_type == ExceptionType.MISSING_BANK

    # Multiple exceptions: both Bank and Ledger are absent
    exception_types = [e.exception_type for e in res.exceptions]
    assert ExceptionType.MISSING_BANK in exception_types
    assert ExceptionType.MISSING_LEDGER in exception_types
    assert "MISSING_BANK" in res.primary_exception.exception_type.value
    assert "query partner bank clearing file" in res.recommended_next_action


# --- Case 3: Missing Ledger entry (pay_Gz8x1038) ---
def test_diagnose_missing_ledger_entry(tracer, diag_engine):
    trace = tracer.trace("pay_Gz8x1038")
    res = diag_engine.diagnose(trace)

    assert res.diagnosis_code == SettlementDiagnosis.MISSING_LEDGER_RECORD
    assert res.confidence == ConfidenceLevel.LOW
    assert res.severity == ExceptionSeverity.HIGH
    assert res.status == InvestigationStatus.EXCEPTION
    assert res.primary_exception.exception_type == ExceptionType.MISSING_LEDGER
    assert "double-entry" in res.recommended_next_action.lower()


# --- Case 4: Bank rejection (pay_Gz8x1042) ---
def test_diagnose_bank_rejection(tracer, diag_engine):
    trace = tracer.trace("pay_Gz8x1042")
    res = diag_engine.diagnose(trace)

    assert res.diagnosis_code == SettlementDiagnosis.BANK_REJECTED
    assert res.severity == ExceptionSeverity.HIGH
    assert res.status == InvestigationStatus.EXCEPTION
    assert res.primary_exception.exception_type == ExceptionType.BANK_REJECTION

    # Multiple exceptions: Bank rejected AND Ledger missing
    exception_types = [e.exception_type for e in res.exceptions]
    assert ExceptionType.BANK_REJECTION in exception_types
    assert ExceptionType.MISSING_LEDGER in exception_types
    assert "re-dispatch payout" in res.recommended_next_action or "payout retry" in res.recommended_next_action


# --- Case 5: Conflicting evidence (pay_Gz8x1052, pay_Gz8x1061, pay_Gz8x1066) ---
def test_diagnose_conflicting_evidence(tracer, diag_engine):
    for txn_id in ["pay_Gz8x1052", "pay_Gz8x1061", "pay_Gz8x1066"]:
        trace = tracer.trace(txn_id)
        res = diag_engine.diagnose(trace)

        assert res.diagnosis_code == SettlementDiagnosis.CONFLICTING_EVIDENCE
        assert res.confidence == ConfidenceLevel.LOW
        assert res.severity == ExceptionSeverity.CRITICAL
        assert res.status == InvestigationStatus.EXCEPTION
        assert res.primary_exception.exception_type == ExceptionType.CONFLICTING_EVIDENCE
        assert len(res.conflicts) > 0
        assert "fraud and operations audit" in res.recommended_next_action


# --- Case 6: Orphan Bank + Ledger insufficient evidence (pay_Gz8x1100) ---
def test_diagnose_orphan_insufficient_evidence(tracer, diag_engine):
    trace = tracer.trace("pay_Gz8x1100")
    res = diag_engine.diagnose(trace)

    assert res.diagnosis_code == SettlementDiagnosis.INSUFFICIENT_EVIDENCE
    assert res.confidence == ConfidenceLevel.LOW
    assert res.severity == ExceptionSeverity.CRITICAL
    assert res.status == InvestigationStatus.INSUFFICIENT_DATA
    assert res.primary_exception.exception_type == ExceptionType.MISSING_GATEWAY
    assert "cannot establish settlement state" in res.summary


# --- Case 7: Isolated Gateway failure ---
def test_diagnose_isolated_gateway_failure(diag_engine):
    mock_prov_gw = SourceProvenance(
        source_system="GATEWAY",
        source_file="gateway.csv",
        source_row_index=15,
    )
    gw_record = GatewayRecord(
        gateway_transaction_id="pay_mock_gw_failed",
        order_id="order_mock_fail",
        gross_amount=Decimal("1200"),
        raw_amount=1200,
        currency="INR",
        method="card",
        status="failed",
        source_status="failed",
        error_code="INSUFFICIENT_FUNDS",
        error_description="Card declined due to insufficient funds.",
        created_at=datetime.now(timezone.utc),
        provenance=mock_prov_gw,
    )
    trace = TraceResult(
        query=TraceQuery(identifier_value="pay_mock_gw_failed", identifier_type=IdentifierType.GATEWAY_TRANSACTION_ID),
        resolution=ResolutionPath(steps=[], resolved_gateway_transaction_id="pay_mock_gw_failed", path_summary="Mock trace"),
        resolved_gateway_transaction_id="pay_mock_gw_failed",
        gateway_record=gw_record,
        bank_record=None,
        ledger_record=None,
        records_found=["GATEWAY"],
        missing_records=["BANK", "LEDGER"],
        is_complete_chain=False,
        is_orphan=False,
        has_conflicting_statuses=False,
    )

    res = diag_engine.diagnose(trace)
    assert res.diagnosis_code == SettlementDiagnosis.GATEWAY_FAILED
    assert res.confidence == ConfidenceLevel.HIGH
    assert res.severity == ExceptionSeverity.HIGH
    assert res.status == InvestigationStatus.EXCEPTION
    assert res.primary_exception.exception_type == ExceptionType.GATEWAY_FAILURE
    assert "No merchant settlement is due" in res.recommended_next_action


# --- Case 8: Isolated Settlement pending (bank clearing in-flight) ---
def test_diagnose_isolated_settlement_pending(diag_engine):
    prov = SourceProvenance(source_system="GATEWAY", source_file="gateway.csv", source_row_index=20)
    gw = GatewayRecord(
        gateway_transaction_id="pay_mock_pending",
        order_id="order_mock_pnd",
        gross_amount=Decimal("5000"),
        raw_amount=5000,
        currency="INR",
        method="upi",
        status="captured",
        source_status="captured",
        created_at=datetime.now(timezone.utc),
        provenance=prov,
    )
    bnk = BankRecord(
        settlement_id="set_mock_pnd",
        gateway_transaction_id="pay_mock_pending",
        net_settlement_amount=Decimal("4900"),
        raw_amount=4900,
        bank_reference_number="UTR_MOCK_PND",
        settlement_status="pending",
        source_status="pending",
        settled_at=None,
        provenance=SourceProvenance(source_system="BANK", source_file="bank.csv", source_row_index=20),
    )
    led = LedgerRecord(
        ledger_entry_id="led_mock_pnd",
        gateway_transaction_id="pay_mock_pending",
        account_type="merchant_payout_pool",
        entry_type="credit",
        ledger_amount=Decimal("4900"),
        raw_amount=4900,
        booked_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="LEDGER", source_file="ledger.csv", source_row_index=20),
    )
    trace = TraceResult(
        query=TraceQuery(identifier_value="pay_mock_pending", identifier_type=IdentifierType.GATEWAY_TRANSACTION_ID),
        resolution=ResolutionPath(steps=[], resolved_gateway_transaction_id="pay_mock_pending", path_summary="Mock trace"),
        resolved_gateway_transaction_id="pay_mock_pending",
        gateway_record=gw,
        bank_record=bnk,
        ledger_record=led,
        records_found=["GATEWAY", "BANK", "LEDGER"],
        missing_records=[],
        is_complete_chain=True,
        is_orphan=False,
        has_conflicting_statuses=False,
    )

    res = diag_engine.diagnose(trace)
    assert res.diagnosis_code == SettlementDiagnosis.SETTLEMENT_PENDING
    assert res.confidence == ConfidenceLevel.MEDIUM
    assert res.severity == ExceptionSeverity.LOW
    assert res.status == InvestigationStatus.PENDING
    assert "in progress" in res.summary.lower()


# --- Case 9: Isolated Amount mismatch (disbursement != ledger booking) ---
def test_diagnose_isolated_amount_mismatch(diag_engine):
    prov = SourceProvenance(source_system="GATEWAY", source_file="gateway.csv", source_row_index=30)
    gw = GatewayRecord(
        gateway_transaction_id="pay_mock_amt_mismatch",
        order_id="order_mock_amt",
        gross_amount=Decimal("10000"),
        raw_amount=10000,
        currency="INR",
        method="netbanking",
        status="captured",
        source_status="captured",
        created_at=datetime.now(timezone.utc),
        provenance=prov,
    )
    bnk = BankRecord(
        settlement_id="set_mock_amt",
        gateway_transaction_id="pay_mock_amt_mismatch",
        net_settlement_amount=Decimal("9500"),
        raw_amount=9500,
        bank_reference_number="UTR_MOCK_AMT",
        settlement_status="processed",
        source_status="processed",
        settled_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="BANK", source_file="bank.csv", source_row_index=30),
    )
    # Ledger booked 9800 instead of 9500 -> 300 discrepancy
    led = LedgerRecord(
        ledger_entry_id="led_mock_amt",
        gateway_transaction_id="pay_mock_amt_mismatch",
        account_type="merchant_payout_pool",
        entry_type="credit",
        ledger_amount=Decimal("9800"),
        raw_amount=9800,
        booked_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="LEDGER", source_file="ledger.csv", source_row_index=30),
    )
    trace = TraceResult(
        query=TraceQuery(identifier_value="pay_mock_amt_mismatch", identifier_type=IdentifierType.GATEWAY_TRANSACTION_ID),
        resolution=ResolutionPath(steps=[], resolved_gateway_transaction_id="pay_mock_amt_mismatch", path_summary="Mock trace"),
        resolved_gateway_transaction_id="pay_mock_amt_mismatch",
        gateway_record=gw,
        bank_record=bnk,
        ledger_record=led,
        records_found=["GATEWAY", "BANK", "LEDGER"],
        missing_records=[],
        is_complete_chain=True,
        is_orphan=False,
        has_conflicting_statuses=False,
    )

    res = diag_engine.diagnose(trace)
    assert res.diagnosis_code == SettlementDiagnosis.AMOUNT_MISMATCH
    assert res.confidence == ConfidenceLevel.LOW
    assert res.severity == ExceptionSeverity.CRITICAL
    assert res.status == InvestigationStatus.EXCEPTION
    assert res.primary_exception.exception_type == ExceptionType.AMOUNT_MISMATCH
    assert "Halt automated settlement disbursement" in res.recommended_next_action


# --- Case 10: Isolated Duplicate record detection ---
def test_diagnose_isolated_duplicate_record(diag_engine):
    prov = SourceProvenance(source_system="GATEWAY", source_file="gateway.csv", source_row_index=40)
    gw = GatewayRecord(
        gateway_transaction_id="pay_mock_dup",
        order_id="order_mock_dup",
        gross_amount=Decimal("3000"),
        raw_amount=3000,
        currency="INR",
        method="card",
        status="captured",
        source_status="captured",
        created_at=datetime.now(timezone.utc),
        provenance=prov,
    )
    bnk = BankRecord(
        settlement_id="set_mock_dup",
        gateway_transaction_id="pay_mock_dup",
        net_settlement_amount=Decimal("2900"),
        raw_amount=2900,
        bank_reference_number="UTR_MOCK_DUP",
        settlement_status="processed",
        source_status="processed",
        settled_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="BANK", source_file="bank.csv", source_row_index=40),
    )
    led = LedgerRecord(
        ledger_entry_id="led_mock_dup",
        gateway_transaction_id="pay_mock_dup",
        account_type="merchant_payout_pool",
        entry_type="credit",
        ledger_amount=Decimal("2900"),
        raw_amount=2900,
        booked_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="LEDGER", source_file="ledger.csv", source_row_index=40),
    )
    trace = TraceResult(
        query=TraceQuery(identifier_value="pay_mock_dup", identifier_type=IdentifierType.GATEWAY_TRANSACTION_ID),
        resolution=ResolutionPath(steps=[], resolved_gateway_transaction_id="pay_mock_dup", path_summary="Mock trace"),
        resolved_gateway_transaction_id="pay_mock_dup",
        gateway_record=gw,
        bank_record=bnk,
        ledger_record=led,
        records_found=["GATEWAY", "BANK", "LEDGER"],
        missing_records=[],
        is_complete_chain=True,
        is_orphan=False,
        has_conflicting_statuses=False,
        is_duplicate=True,
    )

    res = diag_engine.diagnose(trace)
    assert res.diagnosis_code == SettlementDiagnosis.DUPLICATE_RECORD
    assert res.confidence == ConfidenceLevel.LOW
    assert res.severity == ExceptionSeverity.HIGH
    assert res.status == InvestigationStatus.EXCEPTION
    assert res.primary_exception.exception_type == ExceptionType.DUPLICATE_RECORD
    assert "Duplicate entity record detected" in res.summary


# --- Case 11: Isolated Reference mismatch detection ---
def test_diagnose_isolated_reference_mismatch(diag_engine):
    prov = SourceProvenance(source_system="GATEWAY", source_file="gateway.csv", source_row_index=50)
    gw = GatewayRecord(
        gateway_transaction_id="pay_mock_ref_orig",
        order_id="order_mock_ref",
        gross_amount=Decimal("4000"),
        raw_amount=4000,
        currency="INR",
        method="card",
        status="captured",
        source_status="captured",
        created_at=datetime.now(timezone.utc),
        provenance=prov,
    )
    # Bank record links to a DIFFERENT gateway_transaction_id
    bnk = BankRecord(
        settlement_id="set_mock_ref",
        gateway_transaction_id="pay_mock_ref_DIFFERENT",
        net_settlement_amount=Decimal("3900"),
        raw_amount=3900,
        bank_reference_number="UTR_MOCK_REF",
        settlement_status="processed",
        source_status="processed",
        settled_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="BANK", source_file="bank.csv", source_row_index=50),
    )
    led = LedgerRecord(
        ledger_entry_id="led_mock_ref",
        gateway_transaction_id="pay_mock_ref_orig",
        account_type="merchant_payout_pool",
        entry_type="credit",
        ledger_amount=Decimal("3900"),
        raw_amount=3900,
        booked_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="LEDGER", source_file="ledger.csv", source_row_index=50),
    )
    trace = TraceResult(
        query=TraceQuery(identifier_value="pay_mock_ref_orig", identifier_type=IdentifierType.GATEWAY_TRANSACTION_ID),
        resolution=ResolutionPath(steps=[], resolved_gateway_transaction_id="pay_mock_ref_orig", path_summary="Mock trace"),
        resolved_gateway_transaction_id="pay_mock_ref_orig",
        gateway_record=gw,
        bank_record=bnk,
        ledger_record=led,
        records_found=["GATEWAY", "BANK", "LEDGER"],
        missing_records=[],
        is_complete_chain=True,
        is_orphan=False,
        has_conflicting_statuses=False,
    )

    res = diag_engine.diagnose(trace)
    assert res.diagnosis_code == SettlementDiagnosis.REFERENCE_MISMATCH
    assert res.confidence == ConfidenceLevel.LOW
    assert res.severity == ExceptionSeverity.CRITICAL
    assert res.status == InvestigationStatus.EXCEPTION
    assert res.primary_exception.exception_type == ExceptionType.REFERENCE_MISMATCH
    assert "Reference mismatch detected" in res.summary


# --- Case 12: Multi-exception preservation ---
def test_multi_exception_preservation_real_and_synthetic(tracer, diag_engine):
    # Real dataset transaction pay_Gz8x1042: bank rejected AND missing ledger
    trace_1042 = tracer.trace("pay_Gz8x1042")
    res_1042 = diag_engine.diagnose(trace_1042)
    assert res_1042.diagnosis_code == SettlementDiagnosis.BANK_REJECTED
    exception_types_1042 = [e.exception_type for e in res_1042.exceptions]
    assert ExceptionType.BANK_REJECTION in exception_types_1042
    assert ExceptionType.MISSING_LEDGER in exception_types_1042
    assert len(res_1042.exceptions) >= 2

    # Real dataset transaction pay_Gz8x1000: gateway captured, bank missing AND ledger missing
    trace_1000 = tracer.trace("pay_Gz8x1000")
    res_1000 = diag_engine.diagnose(trace_1000)
    assert res_1000.diagnosis_code == SettlementDiagnosis.MISSING_BANK_RECORD
    exception_types_1000 = [e.exception_type for e in res_1000.exceptions]
    assert ExceptionType.MISSING_BANK in exception_types_1000
    assert ExceptionType.MISSING_LEDGER in exception_types_1000
    assert len(res_1000.exceptions) >= 2


# --- Case 13: Epistemic breakdown strict separation ---
def test_epistemic_facts_strict_separation(tracer, diag_engine):
    trace = tracer.trace("pay_Gz8x1001")
    res = diag_engine.diagnose(trace)

    epistemic = res.epistemic_facts
    assert isinstance(epistemic, EpistemicBreakdown)

    # 1. KNOWN facts: directly recorded attributes
    for fact in epistemic.known_facts:
        assert any(term in fact for term in ["Gateway transaction", "Bank settlement", "Internal ledger entry"])

    # 2. INFERRED: multi-record comparisons
    for inf in epistemic.inferences:
        assert any(term in inf for term in ["match exactly", "differ by arithmetic variance", "variance", "disbursement"])

    # 3. UNKNOWN: acknowledged gaps without fabrication
    for unk in epistemic.unknowns:
        assert any(term in unk for term in ["fee schedule", "absent", "unrecorded", "timezone"])


# --- Case 11: Physical evidence reference linkage ---
def test_evidence_references_physical_linkage(tracer, diag_engine):
    trace = tracer.trace("pay_Gz8x1001")
    res = diag_engine.diagnose(trace)

    assert len(res.evidence_refs) > 0
    for ref in res.evidence_refs:
        assert isinstance(ref, EvidenceReference)
        assert ref.source_system in ["GATEWAY", "BANK", "LEDGER"]
        assert ref.source_file.endswith(".csv")
        assert ref.source_row_index >= 2  # 1-based, header is 1
        assert len(ref.record_id) > 0
        assert len(ref.field_name) > 0
        assert len(ref.field_value) > 0


# --- Case 12: Dataset-wide distribution and determinism ---
def test_dataset_wide_diagnosis_distribution(tracer, diag_engine, loaded_store):
    all_txns = sorted(list(loaded_store.get_all_transaction_ids()))
    assert len(all_txns) == 101

    diagnoses = {}
    for txn_id in all_txns:
        trace = tracer.trace(txn_id)
        res = diag_engine.diagnose(trace)
        diagnoses[txn_id] = res.diagnosis_code
        # Validate that every transaction produces an authoritative enum
        assert isinstance(res.diagnosis_code, SettlementDiagnosis)
        assert isinstance(res.confidence, ConfidenceLevel)
        assert isinstance(res.status, InvestigationStatus)
        assert isinstance(res.severity, ExceptionSeverity)

    from collections import Counter
    counts = Counter(diagnoses.values())

    # Verify exact deterministic counts across all 101 transactions
    assert counts[SettlementDiagnosis.SUCCESSFULLY_SETTLED] == 84
    assert counts[SettlementDiagnosis.MISSING_BANK_RECORD] == 11
    assert counts[SettlementDiagnosis.CONFLICTING_EVIDENCE] == 3
    assert counts[SettlementDiagnosis.BANK_REJECTED] == 1
    assert counts[SettlementDiagnosis.MISSING_LEDGER_RECORD] == 1
    assert counts[SettlementDiagnosis.INSUFFICIENT_EVIDENCE] == 1
    assert sum(counts.values()) == 101


# --- Case 13: Deterministic idempotency ---
def test_diagnosis_idempotency(tracer, diag_engine):
    trace = tracer.trace("pay_Gz8x1001")
    res1 = diag_engine.diagnose(trace)
    res2 = diag_engine.diagnose(trace)
    assert res1.model_dump() == res2.model_dump()


# --- Case 14: Functional interface parity ---
def test_functional_interface_parity(tracer, diag_engine):
    trace = tracer.trace("pay_Gz8x1038")
    res_engine = diag_engine.diagnose(trace)
    res_func = diagnose_transaction(trace)
    assert res_engine.model_dump() == res_func.model_dump()


# --- Case 15: Invalid input handling ---
def test_diagnosis_invalid_input(diag_engine):
    with pytest.raises(InvalidDiagnosisInputError):
        diag_engine.diagnose(None)

    with pytest.raises(InvalidDiagnosisInputError):
        diag_engine.diagnose("not_a_trace_result")


# --- Case 16: Raw CSV immutability verification ---
def test_raw_csv_immutability_after_diagnosis():
    for filename, expected_hash in EXPECTED_HASHES.items():
        filepath = DATA_DIR / filename
        assert filepath.exists(), f"File missing: {filepath}"
        content = filepath.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {filename}!"
