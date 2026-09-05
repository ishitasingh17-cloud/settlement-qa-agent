"""
tests/integration/test_exceptions_dashboard_api.py

Integration test suite for Phase 12 Exception Dashboard API.
Verifies operational metrics, date/severity/status filtering, validation error codes,
rich metadata population, drill-down investigation integrity, and raw CSV immutability.
"""

import hashlib
import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from server.main import app

EXPECTED_CSV_HASHES = {
    "data/gateway.csv": "8945186e3ded7e81b21834e1c5312656fdb3da1af0fd011d7768a2758f24bcff",
    "data/bank.csv": "6db6886b96b1fd642a0a3df1d009bcbf93750090aaea8180a7cc4386c358edc4",
    "data/ledger.csv": "89c5bfb92be8a81f45abfe07975affe711b54009daf59453951c54251722f504",
}


@pytest.fixture
def client():
    return TestClient(app)


def test_exceptions_dashboard_unfiltered(client):
    """Verify GET /api/exceptions without filters returns complete macro operational metrics."""
    resp = client.get("/api/exceptions")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_transactions"] == 101
    assert data["actionable_exceptions_count"] == 17
    assert data["total_exceptions"] == 17
    assert len(data["flagged_transactions"]) == 17

    # Verify macro breakdown
    assert data["settled_count"] == 84
    assert data["missing_bank_count"] == 11
    assert data["conflicting_evidence_count"] == 3
    assert data["bank_rejected_count"] == 1
    assert data["missing_ledger_count"] == 1
    assert data["insufficient_evidence_count"] == 1

    # Verify severity counts
    assert data["critical_count"] == 4
    assert data["error_count"] == 12
    assert data["warning_count"] == 1


def test_exceptions_dashboard_date_filtering(client):
    """Verify filtering by valid date across system timestamps."""
    # Date 2026-09-01
    resp1 = client.get("/api/exceptions?date=2026-09-01")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["total_transactions"] == 36
    assert data1["actionable_exceptions_count"] == 5
    assert len(data1["flagged_transactions"]) == 5

    # Date 2026-09-02 (T+1 bank settlements + gateway captures)
    resp2 = client.get("/api/exceptions?date=2026-09-02")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["total_transactions"] == 64
    assert data2["actionable_exceptions_count"] == 11
    assert len(data2["flagged_transactions"]) == 11

    # Out of range date
    resp_empty = client.get("/api/exceptions?date=1999-01-01")
    assert resp_empty.status_code == 200
    data_empty = resp_empty.json()
    assert data_empty["total_transactions"] == 0
    assert data_empty["actionable_exceptions_count"] == 0
    assert len(data_empty["flagged_transactions"]) == 0


def test_exceptions_dashboard_invalid_date_format(client):
    """Verify invalid date string triggers HTTP 400 with INVALID_DATE_FORMAT error code."""
    resp = client.get("/api/exceptions?date=invalid-date")
    assert resp.status_code == 400
    err_body = resp.json()
    error_obj = err_body.get("detail", err_body)
    assert error_obj["error"] == "INVALID_DATE_FORMAT"
    assert "YYYY-MM-DD" in error_obj["message"]


def test_exceptions_dashboard_severity_filtering(client):
    """Verify filtering by severity."""
    # Critical
    resp_crit = client.get("/api/exceptions?severity=CRITICAL")
    assert resp_crit.status_code == 200
    data_crit = resp_crit.json()
    assert data_crit["actionable_exceptions_count"] == 4
    assert all(item["severity"] == "CRITICAL" for item in data_crit["flagged_transactions"])

    # High
    resp_high = client.get("/api/exceptions?severity=HIGH")
    assert resp_high.status_code == 200
    data_high = resp_high.json()
    assert data_high["actionable_exceptions_count"] == 13
    assert all(item["severity"] == "HIGH" for item in data_high["flagged_transactions"])


def test_exceptions_dashboard_status_filtering(client):
    """Verify filtering by status / diagnosis code."""
    resp_bank = client.get("/api/exceptions?status=MISSING_BANK_RECORD")
    assert resp_bank.status_code == 200
    data_bank = resp_bank.json()
    assert data_bank["actionable_exceptions_count"] == 11
    assert all(item["diagnosis"] == "MISSING_BANK_RECORD" for item in data_bank["flagged_transactions"])

    resp_conflict = client.get("/api/exceptions?status=CONFLICTING_EVIDENCE")
    assert resp_conflict.status_code == 200
    data_conflict = resp_conflict.json()
    assert data_conflict["actionable_exceptions_count"] == 3
    assert all(item["diagnosis"] == "CONFLICTING_EVIDENCE" for item in data_conflict["flagged_transactions"])


def test_exceptions_dashboard_rich_metadata(client):
    """Verify all flagged items contain rich operational metadata (exception_type, summary, remediation)."""
    resp = client.get("/api/exceptions")
    assert resp.status_code == 200
    data = resp.json()

    for item in data["flagged_transactions"]:
        assert item["exception_type"] is not None
        assert len(item["exception_type"]) > 0
        assert item["summary"] is not None
        assert len(item["summary"]) > 0
        assert item["remediation"] is not None
        assert len(item["remediation"]) > 0
        assert item["severity"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "WARNING", "ERROR")


def test_exceptions_dashboard_drill_down_integrity(client):
    """Verify every flagged exception item can be immediately investigated via POST /api/investigate."""
    resp = client.get("/api/exceptions")
    assert resp.status_code == 200
    data = resp.json()

    flagged_items = data["flagged_transactions"]
    assert len(flagged_items) == 17

    # Check a representative sample of flagged exceptions across categories
    sample_ids = [
        "pay_Gz8x1000",  # Missing bank record
        "pay_Gz8x1038",  # Missing ledger record
        "pay_Gz8x1042",  # Bank rejected
        "pay_Gz8x1052",  # Conflicting evidence
        "pay_Gz8x1100",  # Insufficient evidence
    ]

    for txn_id in sample_ids:
        inv_resp = client.post("/api/investigate", json={"query": txn_id})
        assert inv_resp.status_code == 200, f"Drill-down failed for {txn_id}: {inv_resp.text}"
        inv_data = inv_resp.json()
        assert inv_data["success"] is True
        assert inv_data["transaction_id"] == txn_id
        assert inv_data["evidence_pack"] is not None
        assert "integrity_hash" in inv_data["evidence_pack"]


def test_raw_csv_immutability():
    """Verify that all raw financial CSV files remain 100% bit-for-bit unchanged."""
    root_dir = Path(__file__).resolve().parent.parent.parent

    for rel_path, expected_hash in EXPECTED_CSV_HASHES.items():
        filepath = root_dir / rel_path
        assert filepath.exists(), f"Missing raw CSV: {rel_path}"
        with open(filepath, "rb") as f:
            content = f.read()
            actual_hash = hashlib.sha256(content).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}"
