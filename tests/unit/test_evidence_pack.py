"""
tests/unit/test_evidence_pack.py

Comprehensive unit, edge-case, integrity, and serialization tests for PS-8 Verified Evidence Pack (Phase 6).
Covers:
- Scenario 1: Clean resolved settlement (pay_Gz8x1001)
- Scenario 2: Gateway-only missing bank and ledger (pay_Gz8x1000)
- Scenario 3: Missing Ledger entry (pay_Gz8x1038)
- Scenario 4: Bank rejection (pay_Gz8x1042)
- Scenario 5: Conflicting evidence (pay_Gz8x1052, pay_Gz8x1061, pay_Gz8x1066)
- Scenario 6: Orphan Bank + Ledger insufficient evidence (pay_Gz8x1100)
- Scenario 7: Isolated Gateway failure (terminal authorization failure)
- Scenario 8: Isolated Settlement pending (bank clearing in-flight)
- Scenario 9: Isolated Amount mismatch (disbursement != ledger booking)
- Scenario 10: Isolated Duplicate record detection
- Scenario 11: Isolated Reference mismatch detection
- Evidence preservation: Gateway, Bank, and Ledger records survive without modification
- Epistemic preservation: strict separation of KNOWN vs INFERRED vs UNKNOWN
- Physical evidence reference linkage to 1-based CSV line numbers (>= 2)
- Chronological timeline assembly and event ordering
- Cryptographic integrity fingerprint (SHA-256) and tamper detection
- Deterministic idempotency across repeated builds
- JSON serialization and deserialization round-trip
- Negative tests: invalid inputs, mismatched transaction IDs, tampered evidence
- Dataset-wide verification across all 101 transactions in data/
- Raw CSV file immutability verification
"""

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest

from server.models.domain import GatewayRecord, BankRecord, LedgerRecord, SourceProvenance
from server.ingestion.data_store import DataStore
from server.tracing.models import TraceResult, TraceQuery, IdentifierType, ResolutionPath
from server.tracing.trace_engine import TraceEngine
from server.reconciliation.engine import reconcile_trace
from server.reconciliation.models import ReconciliationResult
from server.diagnosis.models import (
    SettlementDiagnosis,
    ConfidenceLevel,
    InvestigationStatus,
    DiagnosisResult,
)
from server.exceptions.models import (
    ExceptionType,
    ExceptionSeverity,
    SettlementException,
    EpistemicBreakdown,
    EvidenceReference,
)
from server.diagnosis.engine import diagnose_transaction
from server.evidence.models import (
    TimelineEvent,
    GatewayEvidence,
    BankEvidence,
    LedgerEvidence,
    ReconciliationSummary,
    VerifiedEvidencePack,
    EvidencePack,
)
from server.evidence.builder import EvidencePackBuilder, build_evidence_pack
from server.evidence.validator import EvidenceValidator
from server.evidence.exceptions import (
    InvalidEvidenceInputError,
    EvidenceIntegrityError,
)

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
def builder():
    return EvidencePackBuilder()


# --- Case 1: Clean resolved settlement (pay_Gz8x1001) ---
def test_build_veo_clean_settlement(tracer, builder):
    trace = tracer.trace("pay_Gz8x1001")
    veo = builder.build(trace)

    assert isinstance(veo, VerifiedEvidencePack)
    assert veo.schema_version == "1.0.0"
    assert veo.veo_id == "veo_pay_Gz8x1001"
    assert veo.transaction_id == "pay_Gz8x1001"
    assert veo.query_identifier == "pay_Gz8x1001"
    assert veo.query_type == "gateway_transaction_id"

    # Diagnosis preservation
    assert veo.diagnosis == SettlementDiagnosis.SUCCESSFULLY_SETTLED
    assert veo.confidence == ConfidenceLevel.HIGH
    assert veo.severity == ExceptionSeverity.NONE
    assert veo.status == InvestigationStatus.RESOLVED
    assert "fully settled and reconciled" in veo.summary
    assert "No operational action required" in veo.recommended_next_action
    assert len(veo.exceptions) == 0
    assert veo.primary_exception is None

    # Multi-system evidence preservation
    assert veo.gateway.present is True
    assert veo.gateway.transaction_id == "pay_Gz8x1001"
    assert veo.gateway.gross_amount == Decimal("111358")
    assert veo.gateway.status == "captured"
    assert veo.gateway.provenance.source_row_index >= 2

    assert veo.bank.present is True
    assert veo.bank.net_settlement_amount == Decimal("38261")
    assert veo.bank.settlement_status == "processed"
    assert veo.bank.bank_reference_number is not None

    assert veo.ledger.present is True
    assert veo.ledger.ledger_amount == Decimal("38261")
    assert veo.ledger.entry_type == "credit"

    # Reconciliation facts
    assert veo.reconciliation.bank_ledger_match is True
    assert veo.reconciliation.has_status_conflict is False

    # Epistemic facts
    assert len(veo.epistemic_model.known_facts) >= 3
    assert len(veo.epistemic_model.inferred_facts) >= 2
    assert len(veo.epistemic_model.unknown_facts) >= 1

    # Physical evidence references
    assert len(veo.evidence_refs) >= 5
    for ref in veo.evidence_refs:
        assert ref.source_row_index >= 2
        assert Path(ref.source_file).name in ["gateway.csv", "bank.csv", "ledger.csv"]

    # Timeline reconstruction
    assert len(veo.timeline) >= 3
    assert any(ev.system == "GATEWAY" for ev in veo.timeline)
    assert any(ev.system == "BANK" for ev in veo.timeline)
    assert any(ev.system == "LEDGER" for ev in veo.timeline)

    # Integrity hash verification
    assert len(veo.integrity_hash) == 64
    assert veo.integrity_hash == EvidenceValidator.compute_integrity_hash(veo)


# --- Case 2: Gateway-only missing bank and ledger (pay_Gz8x1000) ---
def test_build_veo_missing_bank_and_ledger(tracer, builder):
    trace = tracer.trace("pay_Gz8x1000")
    veo = builder.build(trace)

    assert veo.diagnosis == SettlementDiagnosis.MISSING_BANK_RECORD
    assert veo.confidence == ConfidenceLevel.LOW
    assert veo.severity == ExceptionSeverity.HIGH
    assert veo.status == InvestigationStatus.EXCEPTION

    # Gateway present, Bank and Ledger absent
    assert veo.gateway.present is True
    assert veo.gateway.gross_amount == Decimal("17588")

    assert veo.bank.present is False
    assert veo.bank.record is None
    assert veo.bank.net_settlement_amount is None

    assert veo.ledger.present is False
    assert veo.ledger.record is None
    assert veo.ledger.ledger_amount is None

    # Multi-exception preservation
    exception_types = [e.exception_type for e in veo.exceptions]
    assert ExceptionType.MISSING_BANK in exception_types
    assert ExceptionType.MISSING_LEDGER in exception_types
    assert len(veo.exceptions) >= 2

    # Missing records
    assert "BANK" in veo.missing_records
    assert "LEDGER" in veo.missing_records

    # Timeline has missing entries flagged
    assert any("Missing" in ev.event for ev in veo.timeline)


# --- Case 3: Missing Ledger entry (pay_Gz8x1038) ---
def test_build_veo_missing_ledger(tracer, builder):
    trace = tracer.trace("pay_Gz8x1038")
    veo = builder.build(trace)

    assert veo.diagnosis == SettlementDiagnosis.MISSING_LEDGER_RECORD
    assert veo.gateway.present is True
    assert veo.bank.present is True
    assert veo.ledger.present is False
    assert veo.ledger.record is None

    assert "LEDGER" in veo.missing_records
    assert veo.primary_exception.exception_type == ExceptionType.MISSING_LEDGER
    assert "double-entry" in veo.recommended_next_action.lower()


# --- Case 4: Bank rejection (pay_Gz8x1042) ---
def test_build_veo_bank_rejection(tracer, builder):
    trace = tracer.trace("pay_Gz8x1042")
    veo = builder.build(trace)

    assert veo.diagnosis == SettlementDiagnosis.BANK_REJECTED
    assert veo.gateway.present is True
    assert veo.bank.present is True
    assert veo.bank.settlement_status == "failed"

    # Multi-exception: Bank rejection + missing ledger
    exception_types = [e.exception_type for e in veo.exceptions]
    assert ExceptionType.BANK_REJECTION in exception_types
    assert ExceptionType.MISSING_LEDGER in exception_types

    # Epistemic model preserves unknown bank rejection reason
    assert any("failure reason" in unk.lower() or "unrecorded" in unk.lower() for unk in veo.epistemic_model.unknowns)


# --- Case 5: Conflicting evidence (pay_Gz8x1052, pay_Gz8x1061, pay_Gz8x1066) ---
def test_build_veo_conflicting_evidence(tracer, builder):
    for txn_id in ["pay_Gz8x1052", "pay_Gz8x1061", "pay_Gz8x1066"]:
        trace = tracer.trace(txn_id)
        veo = builder.build(trace)

        assert veo.diagnosis == SettlementDiagnosis.CONFLICTING_EVIDENCE
        assert veo.confidence == ConfidenceLevel.LOW
        assert veo.severity == ExceptionSeverity.CRITICAL
        assert veo.status == InvestigationStatus.EXCEPTION
        assert veo.reconciliation.has_status_conflict is True
        assert veo.gateway.status == "failed"
        assert veo.bank.settlement_status == "processed"
        assert "fraud and operations audit" in veo.recommended_next_action


# --- Case 6: Orphan Bank + Ledger insufficient evidence (pay_Gz8x1100) ---
def test_build_veo_orphan_insufficient_evidence(tracer, builder):
    trace = tracer.trace("pay_Gz8x1100")
    veo = builder.build(trace)

    assert veo.diagnosis == SettlementDiagnosis.INSUFFICIENT_EVIDENCE
    assert veo.status == InvestigationStatus.INSUFFICIENT_DATA
    assert veo.is_orphan is True
    assert veo.gateway.present is False
    assert veo.gateway.record is None
    assert "GATEWAY" in veo.missing_records
    assert veo.bank.present is True
    assert veo.ledger.present is True


# --- Case 7: Isolated Gateway failure ---
def test_build_veo_isolated_gateway_failure(builder):
    prov = SourceProvenance(source_system="GATEWAY", source_file="gateway.csv", source_row_index=15)
    gw = GatewayRecord(
        gateway_transaction_id="pay_synth_gw_fail",
        order_id="order_synth_fail",
        gross_amount=Decimal("1200"),
        raw_amount=1200,
        currency="INR",
        method="card",
        status="failed",
        source_status="failed",
        error_code="INSUFFICIENT_FUNDS",
        error_description="Card declined due to insufficient funds.",
        created_at=datetime.now(timezone.utc),
        provenance=prov,
    )
    trace = TraceResult(
        query=TraceQuery(identifier_value="pay_synth_gw_fail", identifier_type=IdentifierType.GATEWAY_TRANSACTION_ID),
        resolution=ResolutionPath(steps=[], resolved_gateway_transaction_id="pay_synth_gw_fail", path_summary="Synthetic trace"),
        resolved_gateway_transaction_id="pay_synth_gw_fail",
        gateway_record=gw,
        bank_record=None,
        ledger_record=None,
        records_found=["GATEWAY"],
        missing_records=["BANK", "LEDGER"],
        is_complete_chain=False,
        is_orphan=False,
        has_conflicting_statuses=False,
    )

    veo = builder.build(trace)
    assert veo.diagnosis == SettlementDiagnosis.GATEWAY_FAILED
    assert veo.confidence == ConfidenceLevel.HIGH
    assert veo.severity == ExceptionSeverity.HIGH
    assert veo.status == InvestigationStatus.EXCEPTION
    assert veo.primary_exception.exception_type == ExceptionType.GATEWAY_FAILURE
    assert "No merchant settlement is due" in veo.recommended_next_action


# --- Case 8: Isolated Settlement pending ---
def test_build_veo_isolated_settlement_pending(builder):
    prov = SourceProvenance(source_system="GATEWAY", source_file="gateway.csv", source_row_index=20)
    gw = GatewayRecord(
        gateway_transaction_id="pay_synth_pending",
        order_id="order_synth_pnd",
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
        settlement_id="set_synth_pnd",
        gateway_transaction_id="pay_synth_pending",
        net_settlement_amount=Decimal("4900"),
        raw_amount=4900,
        bank_reference_number="UTR_SYNTH_PND",
        settlement_status="pending",
        source_status="pending",
        settled_at=None,
        provenance=SourceProvenance(source_system="BANK", source_file="bank.csv", source_row_index=20),
    )
    led = LedgerRecord(
        ledger_entry_id="led_synth_pnd",
        gateway_transaction_id="pay_synth_pending",
        account_type="merchant_payout_pool",
        entry_type="credit",
        ledger_amount=Decimal("4900"),
        raw_amount=4900,
        booked_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="LEDGER", source_file="ledger.csv", source_row_index=20),
    )
    trace = TraceResult(
        query=TraceQuery(identifier_value="pay_synth_pending", identifier_type=IdentifierType.GATEWAY_TRANSACTION_ID),
        resolution=ResolutionPath(steps=[], resolved_gateway_transaction_id="pay_synth_pending", path_summary="Synthetic trace"),
        resolved_gateway_transaction_id="pay_synth_pending",
        gateway_record=gw,
        bank_record=bnk,
        ledger_record=led,
        records_found=["GATEWAY", "BANK", "LEDGER"],
        missing_records=[],
        is_complete_chain=True,
        is_orphan=False,
        has_conflicting_statuses=False,
    )

    veo = builder.build(trace)
    assert veo.diagnosis == SettlementDiagnosis.SETTLEMENT_PENDING
    assert veo.confidence == ConfidenceLevel.MEDIUM
    assert veo.severity == ExceptionSeverity.LOW
    assert veo.status == InvestigationStatus.PENDING
    assert "in progress" in veo.summary.lower()


# --- Case 9: Isolated Amount mismatch ---
def test_build_veo_isolated_amount_mismatch(builder):
    prov = SourceProvenance(source_system="GATEWAY", source_file="gateway.csv", source_row_index=30)
    gw = GatewayRecord(
        gateway_transaction_id="pay_synth_amt_mismatch",
        order_id="order_synth_amt",
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
        settlement_id="set_synth_amt",
        gateway_transaction_id="pay_synth_amt_mismatch",
        net_settlement_amount=Decimal("9500"),
        raw_amount=9500,
        bank_reference_number="UTR_SYNTH_AMT",
        settlement_status="processed",
        source_status="processed",
        settled_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="BANK", source_file="bank.csv", source_row_index=30),
    )
    led = LedgerRecord(
        ledger_entry_id="led_synth_amt",
        gateway_transaction_id="pay_synth_amt_mismatch",
        account_type="merchant_payout_pool",
        entry_type="credit",
        ledger_amount=Decimal("9800"),
        raw_amount=9800,
        booked_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="LEDGER", source_file="ledger.csv", source_row_index=30),
    )
    trace = TraceResult(
        query=TraceQuery(identifier_value="pay_synth_amt_mismatch", identifier_type=IdentifierType.GATEWAY_TRANSACTION_ID),
        resolution=ResolutionPath(steps=[], resolved_gateway_transaction_id="pay_synth_amt_mismatch", path_summary="Synthetic trace"),
        resolved_gateway_transaction_id="pay_synth_amt_mismatch",
        gateway_record=gw,
        bank_record=bnk,
        ledger_record=led,
        records_found=["GATEWAY", "BANK", "LEDGER"],
        missing_records=[],
        is_complete_chain=True,
        is_orphan=False,
        has_conflicting_statuses=False,
    )

    veo = builder.build(trace)
    assert veo.diagnosis == SettlementDiagnosis.AMOUNT_MISMATCH
    assert veo.confidence == ConfidenceLevel.LOW
    assert veo.severity == ExceptionSeverity.CRITICAL
    assert veo.status == InvestigationStatus.EXCEPTION
    assert veo.primary_exception.exception_type == ExceptionType.AMOUNT_MISMATCH
    assert "Halt automated settlement disbursement" in veo.recommended_next_action


# --- Case 10: Isolated Duplicate record ---
def test_build_veo_isolated_duplicate_record(builder):
    prov = SourceProvenance(source_system="GATEWAY", source_file="gateway.csv", source_row_index=40)
    gw = GatewayRecord(
        gateway_transaction_id="pay_synth_dup",
        order_id="order_synth_dup",
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
        settlement_id="set_synth_dup",
        gateway_transaction_id="pay_synth_dup",
        net_settlement_amount=Decimal("2900"),
        raw_amount=2900,
        bank_reference_number="UTR_SYNTH_DUP",
        settlement_status="processed",
        source_status="processed",
        settled_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="BANK", source_file="bank.csv", source_row_index=40),
    )
    led = LedgerRecord(
        ledger_entry_id="led_synth_dup",
        gateway_transaction_id="pay_synth_dup",
        account_type="merchant_payout_pool",
        entry_type="credit",
        ledger_amount=Decimal("2900"),
        raw_amount=2900,
        booked_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="LEDGER", source_file="ledger.csv", source_row_index=40),
    )
    trace = TraceResult(
        query=TraceQuery(identifier_value="pay_synth_dup", identifier_type=IdentifierType.GATEWAY_TRANSACTION_ID),
        resolution=ResolutionPath(steps=[], resolved_gateway_transaction_id="pay_synth_dup", path_summary="Synthetic trace"),
        resolved_gateway_transaction_id="pay_synth_dup",
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

    veo = builder.build(trace)
    assert veo.diagnosis == SettlementDiagnosis.DUPLICATE_RECORD
    assert veo.confidence == ConfidenceLevel.LOW
    assert veo.severity == ExceptionSeverity.HIGH
    assert veo.status == InvestigationStatus.EXCEPTION
    assert veo.primary_exception.exception_type == ExceptionType.DUPLICATE_RECORD


# --- Case 11: Isolated Reference mismatch ---
def test_build_veo_isolated_reference_mismatch(builder):
    prov = SourceProvenance(source_system="GATEWAY", source_file="gateway.csv", source_row_index=50)
    gw = GatewayRecord(
        gateway_transaction_id="pay_synth_ref_orig",
        order_id="order_synth_ref",
        gross_amount=Decimal("4000"),
        raw_amount=4000,
        currency="INR",
        method="card",
        status="captured",
        source_status="captured",
        created_at=datetime.now(timezone.utc),
        provenance=prov,
    )
    bnk = BankRecord(
        settlement_id="set_synth_ref",
        gateway_transaction_id="pay_synth_ref_DIFFERENT",
        net_settlement_amount=Decimal("3900"),
        raw_amount=3900,
        bank_reference_number="UTR_SYNTH_REF",
        settlement_status="processed",
        source_status="processed",
        settled_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="BANK", source_file="bank.csv", source_row_index=50),
    )
    led = LedgerRecord(
        ledger_entry_id="led_synth_ref",
        gateway_transaction_id="pay_synth_ref_orig",
        account_type="merchant_payout_pool",
        entry_type="credit",
        ledger_amount=Decimal("3900"),
        raw_amount=3900,
        booked_at=datetime.now(timezone.utc),
        provenance=SourceProvenance(source_system="LEDGER", source_file="ledger.csv", source_row_index=50),
    )
    trace = TraceResult(
        query=TraceQuery(identifier_value="pay_synth_ref_orig", identifier_type=IdentifierType.GATEWAY_TRANSACTION_ID),
        resolution=ResolutionPath(steps=[], resolved_gateway_transaction_id="pay_synth_ref_orig", path_summary="Synthetic trace"),
        resolved_gateway_transaction_id="pay_synth_ref_orig",
        gateway_record=gw,
        bank_record=bnk,
        ledger_record=led,
        records_found=["GATEWAY", "BANK", "LEDGER"],
        missing_records=[],
        is_complete_chain=True,
        is_orphan=False,
        has_conflicting_statuses=False,
    )

    veo = builder.build(trace)
    assert veo.diagnosis == SettlementDiagnosis.REFERENCE_MISMATCH
    assert veo.confidence == ConfidenceLevel.LOW
    assert veo.severity == ExceptionSeverity.CRITICAL
    assert veo.status == InvestigationStatus.EXCEPTION
    assert veo.primary_exception.exception_type == ExceptionType.REFERENCE_MISMATCH


# --- Case 12: JSON serialization round trip ---
def test_veo_json_serialization_round_trip(tracer, builder):
    trace = tracer.trace("pay_Gz8x1001")
    veo = builder.build(trace)

    json_str = veo.model_dump_json(indent=2)
    assert isinstance(json_str, str)
    assert len(json_str) > 0

    # Ensure no float representation of monetary fields in JSON
    parsed_json = json.loads(json_str)
    assert parsed_json["transaction_id"] == "pay_Gz8x1001"
    assert parsed_json["gateway"]["gross_amount"] == "111358"
    assert parsed_json["bank"]["net_settlement_amount"] == "38261"
    assert parsed_json["ledger"]["ledger_amount"] == "38261"

    # Deserialization round trip
    restored_veo = VerifiedEvidencePack.model_validate_json(json_str)
    assert restored_veo == veo
    assert restored_veo.integrity_hash == veo.integrity_hash


# --- Case 13: Determinism & Idempotency ---
def test_veo_determinism_and_idempotency(tracer, builder):
    trace = tracer.trace("pay_Gz8x1001")
    veo1 = builder.build(trace)
    veo2 = builder.build(trace)

    assert veo1.integrity_hash == veo2.integrity_hash
    assert veo1.model_dump() == veo2.model_dump()


# --- Case 14: Functional interface parity ---
def test_functional_interface_parity(tracer, builder):
    trace = tracer.trace("pay_Gz8x1038")
    veo_engine = builder.build(trace)
    veo_func = build_evidence_pack(trace)

    assert veo_engine.integrity_hash == veo_func.integrity_hash
    assert veo_engine.model_dump() == veo_func.model_dump()


# --- Case 15: Tamper detection & integrity failure ---
def test_veo_tamper_detection_raises_integrity_error(tracer, builder):
    trace = tracer.trace("pay_Gz8x1001")
    veo = builder.build(trace)

    # Simulate tampered amount: mutate gross_amount from 5000 to 9999
    tampered_gw = veo.gateway.model_copy(update={"gross_amount": Decimal("9999.00")})
    tampered_veo = veo.model_copy(update={"gateway": tampered_gw})

    with pytest.raises(EvidenceIntegrityError) as exc_info:
        EvidenceValidator.validate_pack(tampered_veo, trace)
    assert "integrity hash mismatch" in str(exc_info.value).lower()


# --- Case 16: Negative tests for invalid inputs ---
def test_negative_invalid_inputs(builder):
    with pytest.raises(InvalidEvidenceInputError):
        builder.build(None)

    with pytest.raises(InvalidEvidenceInputError):
        builder.build("not_a_trace_result")


# --- Case 17: Negative tests for identity mismatch ---
def test_negative_transaction_identity_mismatch(tracer, builder):
    trace = tracer.trace("pay_Gz8x1001")
    recon = reconcile_trace(trace)
    # Tamper diagnosis with a different transaction ID
    diag_tampered = DiagnosisResult(
        transaction_id="pay_DIFFERENT_TXN_ID",
        diagnosis_code=SettlementDiagnosis.SUCCESSFULLY_SETTLED,
        confidence=ConfidenceLevel.HIGH,
        confidence_reason="Tampered reason",
        severity=ExceptionSeverity.NONE,
        status=InvestigationStatus.RESOLVED,
        summary="Tampered summary",
        recommended_next_action="None",
        primary_exception=None,
        exceptions=[],
        epistemic_facts=EpistemicBreakdown(known_facts=[], inferences=[], unknowns=[]),
        evidence_refs=[],
        missing_records=[],
        conflicts=[],
    )

    with pytest.raises(EvidenceIntegrityError) as exc_info:
        builder.build(trace, recon, diag_tampered)
    assert "Transaction identity mismatch" in str(exc_info.value)


# --- Case 18: Negative test for fabricated data when marked missing ---
def test_negative_fabricated_data_when_marked_missing(tracer, builder):
    trace = tracer.trace("pay_Gz8x1000")
    veo = builder.build(trace)

    # Inject fabricated bank record into a missing bank pack
    fake_prov = SourceProvenance(source_system="BANK", source_file="bank.csv", source_row_index=99)
    fake_bnk = BankRecord(
        settlement_id="set_fabricated",
        gateway_transaction_id="pay_Gz8x1000",
        net_settlement_amount=Decimal("2500"),
        raw_amount=2500,
        bank_reference_number="UTR_FAKE",
        settlement_status="processed",
        source_status="processed",
        provenance=fake_prov,
    )
    tampered_bnk = veo.bank.model_copy(update={"record": fake_bnk, "net_settlement_amount": Decimal("2500")})
    tampered_veo = veo.model_copy(update={"bank": tampered_bnk})

    with pytest.raises(EvidenceIntegrityError) as exc_info:
        EvidenceValidator.validate_pack(tampered_veo)
    assert "fabricated record data" in str(exc_info.value).lower()


# --- Case 19: Dataset-wide verification (all 101 transactions) ---
def test_dataset_wide_veo_generation_and_integrity(tracer, builder, loaded_store):
    all_txns = sorted(list(loaded_store.get_all_transaction_ids()))
    assert len(all_txns) == 101

    for txn_id in all_txns:
        trace = tracer.trace(txn_id)
        veo = builder.build(trace)

        assert isinstance(veo, VerifiedEvidencePack)
        assert veo.transaction_id == txn_id
        assert veo.veo_id == f"veo_{txn_id}"
        assert len(veo.integrity_hash) == 64
        # Validate integrity check passes for every single transaction
        EvidenceValidator.validate_pack(veo, trace)


# --- Case 20: Raw CSV immutability verification ---
def test_raw_csv_immutability_after_veo():
    for filename, expected_hash in EXPECTED_HASHES.items():
        filepath = DATA_DIR / filename
        assert filepath.exists(), f"File missing: {filepath}"
        content = filepath.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {filename}!"
