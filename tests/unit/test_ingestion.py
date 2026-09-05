"""
tests/unit/test_ingestion.py

Comprehensive Phase 2 unit tests covering:
- Gateway CSV parsing & timestamp conversion
- Bank CSV parsing & failed record null handling
- Ledger CSV parsing & entry type validation
- Cross-system foreign key preservation & indexing
- Explicit structured error handling for malformed data
- Raw dataset immutability verification (SHA-256 hash preservation)
"""

import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import pytest

from server.models.domain import GatewayRecord, BankRecord, LedgerRecord
from server.ingestion.csv_loader import (
    parse_gateway_csv,
    parse_bank_csv,
    parse_ledger_csv,
)
from server.ingestion.data_store import DataStore
from server.ingestion.exceptions import (
    DatasetNotFoundError,
    EmptyDatasetError,
    SchemaValidationError,
    RowValidationError,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

EXPECTED_HASHES = {
    "gateway.csv": "8945186e3ded7e81b21834e1c5312656fdb3da1af0fd011d7768a2758f24bcff",
    "bank.csv": "6db6886b96b1fd642a0a3df1d009bcbf93750090aaea8180a7cc4386c358edc4",
    "ledger.csv": "89c5bfb92be8a81f45abfe07975affe711b54009daf59453951c54251722f504",
}


def test_raw_csv_immutability():
    """Verifies that source CSV files were not modified during or after ingestion."""
    for filename, expected_hash in EXPECTED_HASHES.items():
        filepath = DATA_DIR / filename
        data = filepath.read_bytes()
        actual_hash = hashlib.sha256(data).hexdigest()
        assert actual_hash == expected_hash, f"Source CSV {filename} was modified!"


def test_parse_gateway_csv_success():
    records = parse_gateway_csv(DATA_DIR / "gateway.csv")
    assert len(records) == 100

    # Test sample record
    r1 = records[0]
    assert r1.gateway_transaction_id == "pay_Gz8x1000"
    assert r1.order_id == "order_Odx1000"
    assert r1.gross_amount == Decimal("17588")
    assert r1.raw_amount == 17588
    assert r1.currency == "INR"
    assert r1.status == "captured"
    assert r1.method == "netbanking"
    assert r1.created_at == datetime(2026, 9, 1, 9, 0, 0)
    assert r1.provenance.source_system == "GATEWAY"
    assert r1.provenance.source_row_index == 2  # Physical line 2 (line 1 is header)
    assert records[-1].provenance.source_row_index == 101  # Physical line 101 (100th data row)
    assert r1.error_code is None
    assert r1.error_description is None

    # Test failed record error retention
    failed_recs = [r for r in records if r.status == "failed"]
    assert len(failed_recs) == 3
    for f in failed_recs:
        assert f.error_code == "BAD_REQUEST_ERROR"
        assert "Payment failed" in f.error_description


def test_parse_bank_csv_success():
    records = parse_bank_csv(DATA_DIR / "bank.csv")
    assert len(records) == 90

    # Test sample processed record
    r1 = records[0]
    assert r1.settlement_id == "set_Bnk9x2001"
    assert r1.gateway_transaction_id == "pay_Gz8x1001"
    assert r1.net_settlement_amount == Decimal("38261")
    assert r1.raw_amount == 38261
    assert r1.bank_reference_number == "UTR721609600"
    assert r1.settlement_status == "processed"
    assert r1.settled_at == datetime(2026, 9, 2, 12, 0)
    assert r1.provenance.source_system == "BANK"
    assert r1.provenance.source_row_index == 2  # Physical line 2 (line 1 is header)
    assert records[-1].provenance.source_row_index == 91  # Physical line 91 (90th data row)

    # Test failed record null timestamp handling
    failed_recs = [r for r in records if r.settlement_status == "failed"]
    assert len(failed_recs) == 1
    failed_rec = failed_recs[0]
    assert failed_rec.settlement_id == "set_Bnk9x2042"
    assert failed_rec.gateway_transaction_id == "pay_Gz8x1042"
    assert failed_rec.settled_at is None  # Must remain None, not fabricated


def test_parse_ledger_csv_success():
    records = parse_ledger_csv(DATA_DIR / "ledger.csv")
    assert len(records) == 88

    # Test sample record
    r1 = records[0]
    assert r1.ledger_entry_id == "led_Lgr1x3001"
    assert r1.gateway_transaction_id == "pay_Gz8x1001"
    assert r1.account_type == "merchant_payout_pool"
    assert r1.entry_type == "credit"
    assert r1.ledger_amount == Decimal("38261")
    assert r1.raw_amount == 38261
    assert r1.booked_at == datetime(2026, 9, 2, 14, 0)
    assert r1.provenance.source_system == "LEDGER"
    assert r1.provenance.source_row_index == 2  # Physical line 2 (line 1 is header)
    assert records[-1].provenance.source_row_index == 89  # Physical line 89 (88th data row)


def test_provenance_row_index_is_one_based_physical_line_number():
    """
    Explicitly tests that source_row_index adheres to the Phase 2 contract:
    1-based physical CSV line number, including header (line 1 = header, line 2 = first data row).
    """
    gw_records = parse_gateway_csv(DATA_DIR / "gateway.csv")
    bank_records = parse_bank_csv(DATA_DIR / "bank.csv")
    ledger_records = parse_ledger_csv(DATA_DIR / "ledger.csv")

    # Gateway: 100 data rows -> lines 2 to 101
    for expected_line, rec in enumerate(gw_records, start=2):
        assert rec.provenance.source_row_index == expected_line

    # Bank: 90 data rows -> lines 2 to 91
    for expected_line, rec in enumerate(bank_records, start=2):
        assert rec.provenance.source_row_index == expected_line

    # Ledger: 88 data rows -> lines 2 to 89
    for expected_line, rec in enumerate(ledger_records, start=2):
        assert rec.provenance.source_row_index == expected_line


def test_datastore_indexing_and_lookup():
    store = DataStore()
    store.load_from_directory(DATA_DIR)

    assert store.total_gateway_records == 100
    assert store.total_bank_records == 90
    assert store.total_ledger_records == 88

    # Check common transaction lookup
    common_id = "pay_Gz8x1001"
    gw = store.get_gateway_by_txn_id(common_id)
    bnk = store.get_bank_by_txn_id(common_id)
    led = store.get_ledger_by_txn_id(common_id)

    assert gw is not None
    assert bnk is not None
    assert led is not None
    assert gw.order_id == "order_Odx1001"
    assert bnk.settlement_id == "set_Bnk9x2001"
    assert bnk.bank_reference_number == "UTR721609600"
    assert led.ledger_entry_id == "led_Lgr1x3001"

    # Secondary index lookups
    assert store.get_gateway_by_order_id("order_Odx1001") == gw
    assert store.get_bank_by_settlement_id("set_Bnk9x2001") == bnk
    assert store.get_bank_by_utr("UTR721609600") == bnk
    assert store.get_ledger_by_entry_id("led_Lgr1x3001") == led

    # Missing records representability
    gw_only_id = "pay_Gz8x1000"
    assert store.get_gateway_by_txn_id(gw_only_id) is not None
    assert store.get_bank_by_txn_id(gw_only_id) is None
    assert store.get_ledger_by_txn_id(gw_only_id) is None

    # Orphan bank/ledger record (missing from Gateway)
    orphan_id = "pay_Gz8x1100"
    assert store.get_gateway_by_txn_id(orphan_id) is None
    assert store.get_bank_by_txn_id(orphan_id) is not None
    assert store.get_ledger_by_txn_id(orphan_id) is not None

    # Global transaction registry
    all_ids = store.get_all_transaction_ids()
    assert len(all_ids) == 101


def test_schema_validation_error_handling(tmp_path):
    # CSV missing required columns
    bad_csv = tmp_path / "bad_gateway.csv"
    bad_csv.write_text("wrong_id,wrong_order\n1,2", encoding="utf-8")

    with pytest.raises(SchemaValidationError) as exc:
        parse_gateway_csv(bad_csv)
    assert "Missing required columns" in str(exc.value)


def test_missing_dataset_error_handling():
    with pytest.raises(DatasetNotFoundError):
        parse_gateway_csv(Path("data/non_existent_file.csv"))


def test_row_validation_invalid_amount(tmp_path):
    bad_csv = tmp_path / "gateway.csv"
    content = """gateway_transaction_id,order_id,amount_in_cents,currency,status,method,email,contact,error_code,error_description,created_at_timestamp
pay_1,ord_1,NOT_A_NUMBER,INR,captured,card,u@e.com,+91,,,1788253200"""
    bad_csv.write_text(content, encoding="utf-8")

    with pytest.raises(RowValidationError) as exc:
        parse_gateway_csv(bad_csv)
    assert "amount_in_cents" in str(exc.value)
    assert "NOT_A_NUMBER" in str(exc.value)


def test_row_validation_invalid_status(tmp_path):
    bad_csv = tmp_path / "gateway.csv"
    content = """gateway_transaction_id,order_id,amount_in_cents,currency,status,method,email,contact,error_code,error_description,created_at_timestamp
pay_1,ord_1,5000,INR,UNRECOGNIZED_STATUS,card,u@e.com,+91,,,1788253200"""
    bad_csv.write_text(content, encoding="utf-8")

    with pytest.raises(RowValidationError) as exc:
        parse_gateway_csv(bad_csv)
    assert "status" in str(exc.value)


def test_timestamp_semantics_and_unspecified_timezone():
    """
    Verifies that Bank and Ledger timestamps are parsed as naive clock times
    without silently acquiring an unjustified timezone (tzinfo is None),
    and that provenance explicitly communicates that source timezone is unspecified.
    Verifies Gateway preserves Unix epoch semantics.
    """
    store = DataStore()
    store.load_from_directory(DATA_DIR)

    # Gateway: Unix epoch seconds with documented UTC-reference definition
    gw = store.get_gateway_by_txn_id("pay_Gz8x1000")
    assert gw is not None
    assert gw.provenance.raw_timestamp == "1788253200"
    assert "Unix epoch" in gw.provenance.timezone_note

    # Bank: Unspecified source timezone, naive clock datetime (tzinfo is None)
    bnk = store.get_bank_by_txn_id("pay_Gz8x1001")
    assert bnk is not None
    assert bnk.settled_at is not None
    assert bnk.settled_at.tzinfo is None, "Bank timestamp must not silently acquire an unjustified timezone!"
    assert bnk.provenance.raw_timestamp == "02-09-2026 12:00"
    assert "unspecified" in bnk.provenance.timezone_note.lower()

    # Ledger: Unspecified source timezone, naive clock datetime (tzinfo is None)
    led = store.get_ledger_by_txn_id("pay_Gz8x1001")
    assert led is not None
    assert led.booked_at.tzinfo is None, "Ledger timestamp must not silently acquire an unjustified timezone!"
    assert led.provenance.raw_timestamp == "02-09-2026 14:00"
    assert "unspecified" in led.provenance.timezone_note.lower()

