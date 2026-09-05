"""
tests/integration/test_api_investigation.py

Comprehensive integration test suite for PS-8 Backend Investigation API (Phase 7).
Tests end-to-end HTTP interaction using FastAPI TestClient against real dataset.
Covers:
- POST /api/investigate (happy path, all 5 identifier types, all exception types)
- GET /api/investigate/{identifier} convenience route
- Business exceptions returning HTTP 200 with full VEO
- Error handling: HTTP 400 (invalid query, unsupported type), HTTP 404 (not found)
- POST /api/query unified search (by transaction ID and date)
- GET /api/settlements batch listing and filtering
- GET /api/exceptions macro dashboard
- GET /api/health service readiness
- Cross-layer contract verification: API response VEO vs direct pipeline VEO
- Dataset immutability verification (SHA-256 baseline check)
"""

import hashlib
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.api.dependencies import get_data_store, get_evidence_builder, get_trace_engine
from server.evidence.models import VerifiedEvidencePack
from server.diagnosis.models import SettlementDiagnosis, InvestigationStatus
from server.exceptions.models import ExceptionSeverity
from server.tracing.models import IdentifierType


client = TestClient(app)

DATA_DIR = Path("data")
BASELINE_HASHES = {
    "gateway.csv": "8945186e3ded7e81b21834e1c5312656fdb3da1af0fd011d7768a2758f24bcff",
    "bank.csv": "6db6886b96b1fd642a0a3df1d009bcbf93750090aaea8180a7cc4386c358edc4",
    "ledger.csv": "89c5bfb92be8a81f45abfe07975affe711b54009daf59453951c54251722f504",
}


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


# ============================================================================
# 1. Single Investigation: Happy Path & Alternate Identifiers
# ============================================================================

def test_api_investigate_happy_path():
    """Tests POST /api/investigate for a fully settled transaction (pay_Gz8x1001)."""
    response = client.post("/api/investigate", json={"query": "pay_Gz8x1001"})
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["investigation_id"] == "veo_pay_Gz8x1001"
    assert data["query"] == "pay_Gz8x1001"
    assert data["query_type"] == IdentifierType.GATEWAY_TRANSACTION_ID.value
    assert data["transaction_id"] == "pay_Gz8x1001"
    assert data["diagnosis"] == SettlementDiagnosis.SUCCESSFULLY_SETTLED.value
    assert data["confidence"] == "HIGH"
    assert data["severity"] == ExceptionSeverity.NONE.value
    assert data["status"] == InvestigationStatus.RESOLVED.value
    assert "settled" in data["summary"].lower()
    assert data["llm_used"] is False

    # Explanation dual-channel structure
    explanation = data["explanation"]
    assert "internal_summary" in explanation
    assert "merchant_friendly_response" in explanation
    assert len(explanation["internal_summary"]) > 0
    assert len(explanation["merchant_friendly_response"]) > 0

    # Evidence pack integrity
    veo = data["evidence_pack"]
    assert veo["veo_id"] == "veo_pay_Gz8x1001"
    assert veo["transaction_id"] == "pay_Gz8x1001"
    assert veo["gateway"]["gross_amount"] == "111358"
    assert veo["bank"]["net_settlement_amount"] == "38261"
    assert veo["ledger"]["ledger_amount"] == "38261"
    assert veo["reconciliation"]["bank_ledger_match"] is True


def test_api_investigate_convenience_get():
    """Tests GET /api/investigate/{identifier} produces identical results."""
    response = client.get("/api/investigate/pay_Gz8x1001")
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "pay_Gz8x1001"
    assert data["diagnosis"] == SettlementDiagnosis.SUCCESSFULLY_SETTLED.value


def test_api_investigate_alternate_identifiers():
    """
    Tests investigating across all 4 alternate identifier types:
    - Order ID (order_Odx1001)
    - Settlement ID (set_Bnk9x2001)
    - Bank UTR (UTR721609600)
    - Ledger Entry ID (led_Lgr1x3001)
    Verifies query != transaction_id contract.
    """
    cases = [
        ("order_Odx1001", IdentifierType.ORDER_ID.value),
        ("set_Bnk9x2001", IdentifierType.SETTLEMENT_ID.value),
        ("UTR721609600", IdentifierType.BANK_REFERENCE_NUMBER.value),
        ("led_Lgr1x3001", IdentifierType.LEDGER_ENTRY_ID.value),
    ]
    for query_val, expected_type in cases:
        resp = client.post("/api/investigate", json={"query": query_val})
        assert resp.status_code == 200, f"Failed on {query_val}: {resp.text}"
        data = resp.json()
        assert data["success"] is True
        assert data["query"] == query_val
        assert data["query_type"] == expected_type
        assert data["transaction_id"] == "pay_Gz8x1001"
        assert data["diagnosis"] == SettlementDiagnosis.SUCCESSFULLY_SETTLED.value


# ============================================================================
# 2. Business Exceptions MUST Return HTTP 200 with Full VEO
# ============================================================================

def test_api_investigate_missing_bank_record_returns_200():
    """Missing bank record is a valid investigation outcome, returning HTTP 200."""
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1000"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagnosis"] == SettlementDiagnosis.MISSING_BANK_RECORD.value
    assert data["severity"] == ExceptionSeverity.HIGH.value
    assert data["confidence"] == "LOW"
    assert data["evidence_pack"]["bank"]["present"] is False
    assert len(data["evidence_pack"]["exceptions"]) >= 1


def test_api_investigate_missing_ledger_entry_returns_200():
    """Missing ledger record is a valid investigation outcome, returning HTTP 200."""
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1038"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagnosis"] == SettlementDiagnosis.MISSING_LEDGER_RECORD.value
    assert data["severity"] == ExceptionSeverity.HIGH.value
    assert data["evidence_pack"]["ledger"]["present"] is False


def test_api_investigate_bank_rejected_returns_200():
    """Bank rejected record is a valid investigation outcome, returning HTTP 200."""
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1042"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagnosis"] == SettlementDiagnosis.BANK_REJECTED.value
    assert data["severity"] == ExceptionSeverity.HIGH.value


def test_api_investigate_conflicting_evidence_returns_200():
    """Conflicting evidence is a valid investigation outcome, returning HTTP 200."""
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1052"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagnosis"] == SettlementDiagnosis.CONFLICTING_EVIDENCE.value
    assert data["severity"] == ExceptionSeverity.CRITICAL.value


def test_api_investigate_orphan_insufficient_evidence_returns_200():
    """Orphan bank/ledger records are valid investigation outcomes, returning HTTP 200."""
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1100"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagnosis"] == SettlementDiagnosis.INSUFFICIENT_EVIDENCE.value
    assert data["severity"] == ExceptionSeverity.CRITICAL.value
    assert data["evidence_pack"]["gateway"]["present"] is False


# ============================================================================
# 3. Negative Error Handling: HTTP 400 and HTTP 404
# ============================================================================

def test_api_investigate_unknown_transaction_returns_404():
    """Valid identifier format that does not match any record returns HTTP 404."""
    resp = client.post("/api/investigate", json={"query": "pay_NONEXISTENT_9999"})
    assert resp.status_code == 404
    err = resp.json()
    assert err["error"] == "NOT_FOUND"
    assert err["error_code"] == "TRANSACTION_NOT_FOUND"
    assert "pay_NONEXISTENT_9999" in err["message"]
    assert err["status_code"] == 404


def test_api_investigate_empty_query_returns_400():
    """Empty or whitespace query returns HTTP 400."""
    resp = client.post("/api/investigate", json={"query": ""})
    assert resp.status_code == 400
    err = resp.json()
    assert err["error"] == "INVALID_QUERY"
    assert err["error_code"] == "INVALID_QUERY"

    resp_ws = client.post("/api/investigate", json={"query": "   "})
    assert resp_ws.status_code == 400
    err_ws = resp_ws.json()
    assert err_ws["error"] == "INVALID_QUERY"


def test_api_investigate_unsupported_type_returns_400():
    """Explicit unsupported query_type parameter returns HTTP 400."""
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1001", "query_type": "BITCOIN_HASH"})
    assert resp.status_code == 400
    err = resp.json()
    assert err["error"] == "UNSUPPORTED_IDENTIFIER_TYPE"
    assert err["error_code"] == "UNSUPPORTED_IDENTIFIER_TYPE"


# ============================================================================
# 4. Unified Query Endpoint (/api/query)
# ============================================================================

def test_api_unified_query_single_transaction():
    """POST /api/query with a transaction ID performs an investigation."""
    resp = client.post("/api/query", json={"query": "pay_Gz8x1001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["transaction_id"] == "pay_Gz8x1001"
    assert data["diagnosis"] == SettlementDiagnosis.SUCCESSFULLY_SETTLED.value


def test_api_unified_query_date_pattern():
    """POST /api/query with a date string routes to batch listing."""
    resp = client.post("/api/query", json={"query": "2026-03-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_count" in data
    assert "items" in data
    assert "settlements" in data


# ============================================================================
# 5. Batch Settlements Listing (/api/settlements)
# ============================================================================

def test_api_list_settlements_all():
    """GET /api/settlements returns listing of loaded transactions."""
    resp = client.get("/api/settlements")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] > 0
    assert len(data["items"]) == data["total_count"]
    assert len(data["settlements"]) == data["total_count"]

    first_item = data["items"][0]
    assert "transaction_id" in first_item
    assert "status" in first_item


def test_api_list_settlements_status_filter():
    """GET /api/settlements?status=SUCCESSFULLY_SETTLED filters by diagnosis."""
    resp = client.get("/api/settlements?status=SUCCESSFULLY_SETTLED")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filtered_count"] > 0
    for item in data["items"]:
        assert item["diagnosis"] == "SUCCESSFULLY_SETTLED"


# ============================================================================
# 6. Exceptions Dashboard (/api/exceptions)
# ============================================================================

def test_api_exceptions_dashboard():
    """GET /api/exceptions summarizes system-wide exception state."""
    resp = client.get("/api/exceptions")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_transactions"] > 0
    assert data["total_exceptions"] > 0
    assert "critical_count" in data
    assert "error_count" in data
    assert "warning_count" in data
    assert "by_type" in data
    assert "by_severity" in data
    assert "flagged_transactions" in data
    assert "exceptions" in data

    # Check that known exception types exist
    assert "MISSING_BANK_RECORD" in data["by_type"]
    assert data["by_type"]["MISSING_BANK_RECORD"] >= 1


# ============================================================================
# 7. Health Endpoint (/api/health)
# ============================================================================

def test_api_health():
    """GET /api/health verifies readiness and count metrics."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["records_loaded"]["gateway"] > 0
    assert data["records_loaded"]["bank"] > 0
    assert data["records_loaded"]["ledger"] > 0


# ============================================================================
# 8. Cross-Layer Contract Verification (API VEO vs Direct Pipeline VEO)
# ============================================================================

def test_api_cross_layer_veo_contract_preservation():
    """
    Verifies that the VEO returned over the HTTP API matches the direct pipeline output
    field-for-field with no data loss or corruption.
    """
    # 1. Obtain direct VEO from EvidencePackBuilder
    store = get_data_store()
    tracer = get_trace_engine()
    builder = get_evidence_builder()

    trace = tracer.trace("pay_Gz8x1001")
    direct_veo = builder.build(trace)

    # 2. Obtain HTTP API response
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1001"})
    assert resp.status_code == 200
    api_veo_dict = resp.json()["evidence_pack"]

    # 3. Verify core structural fields
    assert api_veo_dict["veo_id"] == direct_veo.veo_id
    assert api_veo_dict["transaction_id"] == direct_veo.transaction_id
    assert api_veo_dict["query_type"] == direct_veo.query_type
    assert api_veo_dict["diagnosis"] == direct_veo.diagnosis.value
    assert api_veo_dict["confidence"] == direct_veo.confidence.value
    assert api_veo_dict["severity"] == direct_veo.severity.value
    assert api_veo_dict["status"] == direct_veo.status.value

    # 4. Verify monetary precision preservation
    gw_api = api_veo_dict["gateway"]
    assert str(direct_veo.gateway.gross_amount) == str(gw_api["gross_amount"])
    bank_api = api_veo_dict["bank"]
    assert str(direct_veo.bank.net_settlement_amount) == str(bank_api["net_settlement_amount"])
    ledger_api = api_veo_dict["ledger"]
    assert str(direct_veo.ledger.ledger_amount) == str(ledger_api["ledger_amount"])

    # 5. Verify epistemic facts preservation
    assert len(api_veo_dict["epistemic_model"]["known_facts"]) == len(direct_veo.epistemic_model.known_facts)
    assert len(api_veo_dict["evidence_refs"]) == len(direct_veo.evidence_refs)


# ============================================================================
# 9. Raw Dataset Immutability Check
# ============================================================================

def test_api_raw_csv_immutability():
    """Verifies that API operations never alter raw CSV files."""
    for filename, expected_hash in BASELINE_HASHES.items():
        filepath = DATA_DIR / filename
        assert filepath.exists(), f"Missing file: {filepath}"
        actual_hash = compute_sha256(filepath)
        assert actual_hash == expected_hash, (
            f"MUTATION DETECTED in {filename}! Expected {expected_hash}, got {actual_hash}"
        )
