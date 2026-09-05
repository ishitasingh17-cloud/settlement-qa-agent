"""
tests/unit/test_dataset_integrity.py

Phase 1 unit tests validating the physical presence, column schemas,
row counts, and structural consistency of the supplied mock financial CSV datasets.
"""

import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

EXPECTED_FILES = {
    "gateway.csv": {
        "min_rows": 100,
        "required_columns": [
            "gateway_transaction_id", "order_id", "amount_in_cents",
            "currency", "status", "method", "email", "contact",
            "error_code", "error_description", "created_at_timestamp"
        ]
    },
    "bank.csv": {
        "min_rows": 90,
        "required_columns": [
            "settlement_id", "gateway_transaction_id", "net_settled_amount",
            "bank_reference_number", "settlement_status", "settled_at"
        ]
    },
    "ledger.csv": {
        "min_rows": 88,
        "required_columns": [
            "ledger_entry_id", "gateway_transaction_id", "account_type",
            "entry_type", "amount", "booked_at"
        ]
    }
}


def test_required_csv_files_exist():
    for filename in EXPECTED_FILES:
        filepath = DATA_DIR / filename
        assert filepath.exists(), f"Expected dataset file missing: {filepath}"
        assert filepath.stat().st_size > 0, f"Dataset file is empty: {filepath}"


def test_csv_column_schemas():
    for filename, meta in EXPECTED_FILES.items():
        filepath = DATA_DIR / filename
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for col in meta["required_columns"]:
                assert col in fieldnames, f"Column '{col}' missing from {filename}"


def test_row_counts_and_no_duplicate_primary_ids():
    for filename, meta in EXPECTED_FILES.items():
        filepath = DATA_DIR / filename
        with open(filepath, mode="r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
            assert len(rows) >= meta["min_rows"], f"{filename} has fewer rows than expected ({len(rows)})"

            # Check identifier uniqueness
            if filename == "gateway.csv":
                ids = [r["gateway_transaction_id"] for r in rows]
                assert len(ids) == len(set(ids)), "Duplicate gateway_transaction_id found in gateway.csv"
            elif filename == "bank.csv":
                ids = [r["settlement_id"] for r in rows]
                assert len(ids) == len(set(ids)), "Duplicate settlement_id found in bank.csv"
            elif filename == "ledger.csv":
                ids = [r["ledger_entry_id"] for r in rows]
                assert len(ids) == len(set(ids)), "Duplicate ledger_entry_id found in ledger.csv"


def test_amount_formats_are_numeric():
    with open(DATA_DIR / "gateway.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            assert r["amount_in_cents"].isdigit(), f"Invalid amount_in_cents: {r['amount_in_cents']}"

    with open(DATA_DIR / "bank.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            assert r["net_settled_amount"].isdigit(), f"Invalid net_settled_amount: {r['net_settled_amount']}"

    with open(DATA_DIR / "ledger.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            assert r["amount"].isdigit(), f"Invalid amount: {r['amount']}"


def test_cross_system_foreign_key_linkage():
    with open(DATA_DIR / "gateway.csv", encoding="utf-8") as f:
        gw_ids = {r["gateway_transaction_id"] for r in csv.DictReader(f)}
    with open(DATA_DIR / "bank.csv", encoding="utf-8") as f:
        bnk_ids = {r["gateway_transaction_id"] for r in csv.DictReader(f)}
    with open(DATA_DIR / "ledger.csv", encoding="utf-8") as f:
        led_ids = {r["gateway_transaction_id"] for r in csv.DictReader(f)}

    # Linkage check: intersection must be substantial (>80 transactions)
    common_ids = gw_ids & bnk_ids & led_ids
    assert len(common_ids) == 87, f"Expected 87 common transaction IDs across all 3 files, found {len(common_ids)}"
