"""
tests/unit/test_tracing.py

Comprehensive unit tests for PS-8 Reference Resolution & Transaction Trace Engine (Phase 3).
Covers all 20 required verification points:
1. Gateway transaction ID -> complete trace
2. Order ID -> complete trace
3. Settlement ID -> complete trace
4. Bank UTR -> complete trace
5. Ledger entry ID -> complete trace
6. Gateway-only transaction
7. Gateway + Bank, Ledger missing
8. Bank + Ledger, Gateway missing
9. Gateway failed + Bank processed + Ledger present
10. Unknown identifier
11. Empty identifier
12. Unsupported identifier type
13. Exact identifier matching
14. Resolution path correctness
15. Missing record semantics
16. Orphan record semantics
17. Provenance preservation
18. Deterministic repeated resolution
19. No financial diagnosis performed by tracing
20. No raw CSV mutation
21. Ambiguous identifier handling (defensive)
"""

import hashlib
import pytest
from pathlib import Path

from server.ingestion.data_store import DataStore
from server.tracing.models import IdentifierType, TraceResult
from server.tracing.exceptions import (
    InvalidQueryError,
    UnsupportedIdentifierTypeError,
    TransactionNotFoundError,
    AmbiguousIdentifierError,
)
from server.tracing.trace_engine import TraceEngine, trace_transaction

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
def engine(loaded_store):
    return TraceEngine(data_store=loaded_store)


# 1. Gateway transaction ID -> complete trace
def test_trace_by_gateway_transaction_id_complete(engine):
    res = engine.trace("pay_Gz8x1001")
    assert isinstance(res, TraceResult)
    assert res.resolved_gateway_transaction_id == "pay_Gz8x1001"
    assert res.gateway_record is not None
    assert res.bank_record is not None
    assert res.ledger_record is not None
    assert res.is_complete_chain is True
    assert res.is_orphan is False
    assert set(res.records_found) == {"GATEWAY", "BANK", "LEDGER"}
    assert res.missing_records == []


# 2. Order ID -> complete trace
def test_trace_by_order_id_complete(engine):
    res = engine.trace("order_Odx1001")
    assert res.query.identifier_type == IdentifierType.ORDER_ID
    assert res.resolved_gateway_transaction_id == "pay_Gz8x1001"
    assert res.gateway_record is not None
    assert res.bank_record is not None
    assert res.ledger_record is not None
    assert res.is_complete_chain is True
    assert "order_id -> Gateway -> gateway_transaction_id -> Bank, Ledger" in res.resolution.path_summary


# 3. Settlement ID -> complete trace
def test_trace_by_settlement_id_complete(engine):
    res = engine.trace("set_Bnk9x2001")
    assert res.query.identifier_type == IdentifierType.SETTLEMENT_ID
    assert res.resolved_gateway_transaction_id == "pay_Gz8x1001"
    assert res.gateway_record is not None
    assert res.bank_record is not None
    assert res.ledger_record is not None
    assert res.is_complete_chain is True
    assert "settlement_id -> Bank -> gateway_transaction_id -> Gateway, Ledger" in res.resolution.path_summary


# 4. Bank UTR -> complete trace
def test_trace_by_bank_reference_number_complete(engine):
    res = engine.trace("UTR721609600")
    assert res.query.identifier_type == IdentifierType.BANK_REFERENCE_NUMBER
    assert res.resolved_gateway_transaction_id == "pay_Gz8x1001"
    assert res.gateway_record is not None
    assert res.bank_record is not None
    assert res.ledger_record is not None
    assert res.is_complete_chain is True
    assert "bank_reference_number -> Bank -> gateway_transaction_id -> Gateway, Ledger" in res.resolution.path_summary


# 5. Ledger entry ID -> complete trace
def test_trace_by_ledger_entry_id_complete(engine):
    res = engine.trace("led_Lgr1x3001")
    assert res.query.identifier_type == IdentifierType.LEDGER_ENTRY_ID
    assert res.resolved_gateway_transaction_id == "pay_Gz8x1001"
    assert res.gateway_record is not None
    assert res.bank_record is not None
    assert res.ledger_record is not None
    assert res.is_complete_chain is True
    assert "ledger_entry_id -> Ledger -> gateway_transaction_id -> Gateway, Bank" in res.resolution.path_summary


# 6. Gateway-only transaction
def test_trace_gateway_only_transaction(engine):
    res = engine.trace("pay_Gz8x1000")
    assert res.resolved_gateway_transaction_id == "pay_Gz8x1000"
    assert res.gateway_record is not None
    assert res.bank_record is None
    assert res.ledger_record is None
    assert res.is_complete_chain is False
    assert res.is_orphan is False
    assert res.records_found == ["GATEWAY"]
    assert set(res.missing_records) == {"BANK", "LEDGER"}


# 7. Gateway + Bank, Ledger missing
def test_trace_gateway_and_bank_ledger_missing(engine):
    res = engine.trace("pay_Gz8x1038")
    assert res.resolved_gateway_transaction_id == "pay_Gz8x1038"
    assert res.gateway_record is not None
    assert res.bank_record is not None
    assert res.ledger_record is None
    assert res.is_complete_chain is False
    assert res.is_orphan is False
    assert set(res.records_found) == {"GATEWAY", "BANK"}
    assert res.missing_records == ["LEDGER"]
    assert res.bank_record.settlement_id == "set_Bnk9x2038"
    assert res.bank_record.bank_reference_number == "UTR677280546"


# 8. Bank + Ledger, Gateway missing (Orphan)
def test_trace_orphan_bank_and_ledger_gateway_missing(engine):
    # Lookup by gateway_transaction_id
    res_txn = engine.trace("pay_Gz8x1100")
    assert res_txn.resolved_gateway_transaction_id == "pay_Gz8x1100"
    assert res_txn.gateway_record is None
    assert res_txn.bank_record is not None
    assert res_txn.ledger_record is not None
    assert res_txn.is_orphan is True
    assert res_txn.is_complete_chain is False
    assert set(res_txn.records_found) == {"BANK", "LEDGER"}
    assert res_txn.missing_records == ["GATEWAY"]

    # Lookup by Bank settlement_id for the orphan
    res_set = engine.trace("set_Bnk9x2100")
    assert res_set.resolved_gateway_transaction_id == "pay_Gz8x1100"
    assert res_set.gateway_record is None
    assert res_set.bank_record is not None
    assert res_set.is_orphan is True

    # Lookup by UTR for the orphan
    res_utr = engine.trace("UTR927982963")
    assert res_utr.resolved_gateway_transaction_id == "pay_Gz8x1100"
    assert res_utr.gateway_record is None
    assert res_utr.is_orphan is True


# 9. Gateway failed + Bank processed + Ledger present (Conflicting source statuses)
def test_trace_conflicting_source_statuses(engine):
    for txn_id in ["pay_Gz8x1052", "pay_Gz8x1061", "pay_Gz8x1066"]:
        res = engine.trace(txn_id)
        assert res.gateway_record is not None
        assert res.bank_record is not None
        assert res.ledger_record is not None
        assert res.gateway_record.status == "failed"
        assert res.bank_record.settlement_status == "processed"
        assert res.ledger_record.entry_type == "credit"
        assert res.has_conflicting_statuses is True
        # Ensure tracing does NOT assign a financial diagnosis or override records
        assert not hasattr(res, "diagnosis")


# 10. Unknown identifier
def test_trace_unknown_identifier_raises_not_found(engine):
    with pytest.raises(TransactionNotFoundError) as exc_info:
        engine.trace("pay_UNKNOWN_9999")
    assert "No records found" in exc_info.value.message
    assert exc_info.value.error_code == "TRANSACTION_NOT_FOUND"

    with pytest.raises(TransactionNotFoundError):
        engine.trace("order_UNKNOWN_9999")

    with pytest.raises(TransactionNotFoundError):
        engine.trace("set_UNKNOWN_9999")

    with pytest.raises(TransactionNotFoundError):
        engine.trace("UTR999999999")

    with pytest.raises(TransactionNotFoundError):
        engine.trace("led_UNKNOWN_9999")


# 11. Empty identifier
def test_trace_empty_query_raises_invalid_query(engine):
    with pytest.raises(InvalidQueryError) as exc_info:
        engine.trace("")
    assert exc_info.value.error_code == "INVALID_QUERY"

    with pytest.raises(InvalidQueryError):
        engine.trace("   ")

    with pytest.raises(InvalidQueryError):
        engine.trace(None)


# 12. Unsupported identifier type
def test_trace_unsupported_identifier_type_raises_error(engine):
    with pytest.raises(UnsupportedIdentifierTypeError) as exc_info:
        engine.trace("random_unrecognized_identifier_123")
    assert exc_info.value.error_code == "UNSUPPORTED_IDENTIFIER_TYPE"

    with pytest.raises(UnsupportedIdentifierTypeError):
        engine.trace("pay_Gz8x1001", identifier_type="invalid_custom_type")


# 13. Exact identifier matching
def test_trace_exact_identifier_matching(engine):
    # Whitespace trimmed
    res = engine.trace("  pay_Gz8x1001  ")
    assert res.resolved_gateway_transaction_id == "pay_Gz8x1001"

    # Substring is not matched
    with pytest.raises(TransactionNotFoundError):
        engine.trace("pay_Gz8x100")  # Missing last digit


# 14. Resolution path correctness
def test_trace_resolution_path_correctness(engine):
    res = engine.trace("order_Odx1001")
    path = res.resolution
    assert len(path.steps) == 4
    assert path.steps[0].from_entity == "QUERY"
    assert path.steps[0].to_entity == "GATEWAY"
    assert path.steps[0].matched is True
    assert path.steps[1].from_entity == "GATEWAY"
    assert path.steps[1].to_entity == "PRIMARY_KEY"
    assert path.steps[1].lookup_value == "pay_Gz8x1001"
    assert path.resolved_gateway_transaction_id == "pay_Gz8x1001"


# 15. Missing record semantics
def test_trace_missing_record_semantics(engine):
    res = engine.trace("pay_Gz8x1000")
    # Missing records must be explicitly listed without guessing root cause
    assert "BANK" in res.missing_records
    assert "LEDGER" in res.missing_records
    assert "GATEWAY" not in res.missing_records


# 16. Orphan record semantics
def test_trace_orphan_record_semantics(engine):
    res = engine.trace("pay_Gz8x1100")
    assert res.is_orphan is True
    assert res.gateway_record is None
    assert res.bank_record is not None
    assert res.ledger_record is not None
    assert res.missing_records == ["GATEWAY"]


# 17. Provenance preservation
def test_trace_provenance_preservation(engine):
    res = engine.trace("pay_Gz8x1001")
    assert res.gateway_record.provenance.source_system == "GATEWAY"
    assert res.gateway_record.provenance.source_file.endswith("gateway.csv")
    assert res.gateway_record.provenance.source_row_index == 3  # Physical line 3 in gateway.csv (second data row)
    assert res.bank_record.provenance.source_system == "BANK"
    assert res.bank_record.provenance.source_file.endswith("bank.csv")
    assert res.bank_record.provenance.source_row_index == 2  # Physical line 2 in bank.csv (first data row)
    assert res.ledger_record.provenance.source_system == "LEDGER"
    assert res.ledger_record.provenance.source_file.endswith("ledger.csv")
    assert res.ledger_record.provenance.source_row_index == 2  # Physical line 2 in ledger.csv (first data row)

    # First data row in gateway.csv is physical line 2
    res_gw0 = engine.trace("pay_Gz8x1000")
    assert res_gw0.gateway_record.provenance.source_row_index == 2

    # Orphan record in bank.csv and ledger.csv
    res_orphan = engine.trace("pay_Gz8x1100")
    assert res_orphan.bank_record.provenance.source_row_index == 91
    assert res_orphan.ledger_record.provenance.source_row_index == 89


# 18. Deterministic repeated resolution
def test_trace_deterministic_repeated_resolution(engine):
    res1 = engine.trace("pay_Gz8x1001")
    res2 = engine.trace("pay_Gz8x1001")
    assert res1.model_dump() == res2.model_dump()

    # Functional interface matches instance interface
    res_func = trace_transaction("pay_Gz8x1001", data_store=engine.data_store)
    assert res1.model_dump() == res_func.model_dump()


# 19. No financial diagnosis performed by tracing
def test_trace_no_financial_diagnosis_performed(engine):
    res = engine.trace("pay_Gz8x1001")
    # Verify no reconciliation or diagnosis fields are attached
    assert not hasattr(res, "discrepancy")
    assert not hasattr(res, "settlement_diagnosis")
    assert not hasattr(res, "amount_difference")
    assert not hasattr(res, "veo")


# 20. No raw CSV mutation
def test_trace_raw_csv_immutability(engine):
    for filename, expected_hash in EXPECTED_HASHES.items():
        filepath = DATA_DIR / filename
        assert filepath.exists(), f"File missing: {filepath}"
        content = filepath.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {filename}!"


# 21. Ambiguous identifier handling (defensive)
def test_trace_ambiguous_identifier_handling():
    # Construct a mock DataStore that returns ambiguous records
    class AmbiguousDataStore(DataStore):
        def get_gateway_by_order_id(self, order_id: str):
            raise AmbiguousIdentifierError(
                f"Multiple conflicting Gateway records found for order_id '{order_id}'.",
                query_value=order_id,
                match_count=2,
            )

    ambig_store = AmbiguousDataStore()
    ambig_engine = TraceEngine(data_store=ambig_store)
    with pytest.raises(AmbiguousIdentifierError) as exc_info:
        ambig_engine.trace("order_Odx1001")
    assert exc_info.value.error_code == "AMBIGUOUS_IDENTIFIER"
    assert exc_info.value.match_count == 2
