"""
tests/integration/test_ui_api_contract.py

Integration test suite verifying the API contracts required by Phase 10 Investigation UI.
Ensures that all endpoints, canonical demo transactions, VEO structures, and error payloads
match frontend component expectations exactly.
"""

import hashlib
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.diagnosis.models import SettlementDiagnosis, ConfidenceLevel, InvestigationStatus
from server.exceptions.models import ExceptionSeverity


@pytest.fixture
def client():
    return TestClient(app)


def test_ui_api_health_check(client):
    """Verify /api/health endpoint used by Header.jsx for status probing."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "service" in data


def test_ui_canonical_demo_scenarios(client):
    """
    Verify all 6 canonical demo transactions referenced in Sidebar.jsx and EmptyState.jsx:
    1. Clean Settled: pay_Gz8x1001
    2. In-Flight Delay / Missing Bank: pay_Gz8x1000
    3. Missing Ledger: pay_Gz8x1038
    4. Bank Rejection: pay_Gz8x1042
    5. Conflicting Evidence: pay_Gz8x1052
    6. Insufficient Evidence: pay_Gz8x1100
    """
    expected_diagnoses = {
        "pay_Gz8x1001": SettlementDiagnosis.SUCCESSFULLY_SETTLED.value,
        "pay_Gz8x1000": SettlementDiagnosis.MISSING_BANK_RECORD.value,
        "pay_Gz8x1038": SettlementDiagnosis.MISSING_LEDGER_RECORD.value,
        "pay_Gz8x1042": SettlementDiagnosis.BANK_REJECTED.value,
        "pay_Gz8x1052": SettlementDiagnosis.CONFLICTING_EVIDENCE.value,
        "pay_Gz8x1100": SettlementDiagnosis.INSUFFICIENT_EVIDENCE.value,
    }

    for txn_id, expected_diag in expected_diagnoses.items():
        resp = client.post("/api/investigate", json={"query": txn_id})
        assert resp.status_code == 200, f"Failed for {txn_id}: {resp.text}"
        data = resp.json()

        assert data["success"] is True
        assert data["transaction_id"] == txn_id
        assert data["diagnosis"] == expected_diag
        assert data["confidence"] in ["HIGH", "MEDIUM", "LOW"]
        assert isinstance(data["confidence_reason"], str) and len(data["confidence_reason"]) > 0

        # Verify evidence_pack contract for SystemInspector and ReferenceChain
        veo = data["evidence_pack"]
        assert "gateway" in veo
        assert "bank" in veo
        assert "ledger" in veo
        assert "reconciliation" in veo
        assert "resolution_path" in veo
        assert "timeline" in veo
        assert "epistemic_model" in veo
        assert "integrity_hash" in veo
        assert len(veo["integrity_hash"]) == 64

        # Verify resolution_path structure for ReferenceChain.jsx
        path = veo["resolution_path"]
        assert "steps" in path
        assert "resolved_gateway_transaction_id" in path
        assert "path_summary" in path
        assert isinstance(path["steps"], list)
        for step in path["steps"]:
            assert "step_number" in step
            assert "from_entity" in step
            assert "to_entity" in step
            assert "lookup_key" in step
            assert "matched" in step

        # Verify timeline for TimelineView.jsx
        timeline = veo["timeline"]
        assert isinstance(timeline, list)
        for event in timeline:
            assert "timestamp" in event
            assert "system" in event
            assert "event" in event

        # Verify epistemic_model for EpistemicViewer.jsx
        epistemic = veo["epistemic_model"]
        assert "known_facts" in epistemic
        assert "inferences" in epistemic
        assert "unknowns" in epistemic

        # Verify explanation for ExplanationDualView.jsx
        expl = data["explanation"]
        assert "internal_summary" in expl
        assert "merchant_friendly_response" in expl
        assert isinstance(expl["validated"], bool)


def test_ui_not_found_error_structure(client):
    """
    Verify 404 response structure expected by ErrorState.jsx
    when querying an identifier that has a valid format but does not exist in records.
    """
    resp = client.post("/api/investigate", json={"query": "pay_99999"})
    assert resp.status_code == 404
    err_body = resp.json()
    error_obj = err_body.get("detail", err_body)
    assert error_obj["error"] == "NOT_FOUND"
    assert "message" in error_obj
    assert "pay_99999" in error_obj["message"]


def test_ui_unsupported_identifier_error_structure(client):
    """Verify 400 response structure for invalid identifier prefixes."""
    resp = client.post("/api/investigate", json={"query": "TXN_99999"})
    assert resp.status_code == 400
    err_body = resp.json()
    error_obj = err_body.get("detail", err_body)
    assert error_obj["error"] == "UNSUPPORTED_IDENTIFIER_TYPE"


def test_ui_ask_follow_up_question(client):
    """Verify POST /api/investigate/ask used by ExplanationDualView Q&A input."""
    resp = client.post(
        "/api/investigate/ask",
        json={
            "identifier": "pay_Gz8x1001",
            "question": "Was the customer charged twice?",
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["answer"] is not None
    assert len(data["answer"]) > 0
    assert "internal_summary" in data
    assert "merchant_friendly_response" in data
    assert data["validated"] is True


def test_ui_raw_csv_immutability():
    """Verify that raw CSV datasets remain 100% bit-for-bit immutable."""
    EXPECTED_HASHES = {
        "data/gateway.csv": "8945186e3ded7e81b21834e1c5312656fdb3da1af0fd011d7768a2758f24bcff",
        "data/bank.csv": "6db6886b96b1fd642a0a3df1d009bcbf93750090aaea8180a7cc4386c358edc4",
        "data/ledger.csv": "89c5bfb92be8a81f45abfe07975affe711b54009daf59453951c54251722f504",
    }
    for rel_path, expected_hash in EXPECTED_HASHES.items():
        p = Path(rel_path)
        assert p.exists(), f"Missing {rel_path}"
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        assert actual == expected_hash, f"Hash mismatch for {rel_path}: {actual} != {expected_hash}"
