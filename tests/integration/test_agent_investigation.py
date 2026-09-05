"""
tests/integration/test_agent_investigation.py

End-to-end integration tests for AI Settlement Analyst (Phase 8).
Tests:
- POST /api/investigate with AI Analyst active
- POST /api/investigate/ask targeted Q&A endpoint
- Golden scenario coverage across all 6 core taxonomy states:
  * SUCCESSFULLY_SETTLED
  * MISSING_BANK_RECORD
  * MISSING_LEDGER_RECORD
  * BANK_REJECTED
  * CONFLICTING_EVIDENCE
  * INSUFFICIENT_EVIDENCE
- Raw dataset SHA-256 immutability verification
"""

import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.api.dependencies import get_investigation_service, get_settlement_analyst
from server.agent.providers import MockLLMProvider, MultiProviderRouter
from server.agent.analyst import SettlementAnalyst


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
# 1. API Integration with AI Analyst
# ============================================================================

def test_api_investigate_deterministic_fallback_when_unconfigured():
    """When no LLM keys are configured, /api/investigate returns deterministic fallback."""
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["transaction_id"] == "pay_Gz8x1001"
    assert data["llm_used"] is False
    assert "settled and confirmed" in data["explanation"]["merchant_friendly_response"]


def test_api_ask_question_happy_path():
    """Tests POST /api/investigate/ask for settled transaction."""
    resp = client.post(
        "/api/investigate/ask",
        json={
            "identifier": "pay_Gz8x1001",
            "question": "What is the status of this payment and what is the UTR?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "internal_summary" in data
    assert "merchant_friendly_response" in data
    assert data["answer"] is not None
    assert "SUCCESSFULLY_SETTLED" in data["answer"]


def test_api_ask_question_by_order_id():
    """Tests POST /api/investigate/ask using an order ID."""
    resp = client.post(
        "/api/investigate/ask",
        json={
            "identifier": "order_Odx1001",
            "question": "Has this order been paid?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] is not None
    assert "SUCCESSFULLY_SETTLED" in data["answer"]


def test_api_ask_question_unknown_transaction_returns_404():
    """Tests POST /api/investigate/ask with non-existent ID returns HTTP 404."""
    resp = client.post(
        "/api/investigate/ask",
        json={
            "identifier": "pay_NONEXISTENT_9999",
            "question": "Where is my money?",
        },
    )
    assert resp.status_code == 404
    err = resp.json()
    assert err["error"] == "NOT_FOUND"
    assert err["error_code"] == "TRANSACTION_NOT_FOUND"


def test_api_ask_question_empty_query_returns_400():
    """Tests POST /api/investigate/ask with empty question returns HTTP 400."""
    resp = client.post(
        "/api/investigate/ask",
        json={
            "identifier": "pay_Gz8x1001",
            "question": "",
        },
    )
    assert resp.status_code == 400
    err = resp.json()
    assert err["error"] == "INVALID_QUERY"


# ============================================================================
# 2. Golden Scenarios across 6 Taxonomy States
# ============================================================================

@pytest.mark.parametrize(
    "txn_id,expected_diag,expected_status",
    [
        ("pay_Gz8x1001", "SUCCESSFULLY_SETTLED", "RESOLVED"),
        ("pay_Gz8x1000", "MISSING_BANK_RECORD", "EXCEPTION"),
        ("pay_Gz8x1038", "MISSING_LEDGER_RECORD", "EXCEPTION"),
        ("pay_Gz8x1042", "BANK_REJECTED", "EXCEPTION"),
        ("pay_Gz8x1052", "CONFLICTING_EVIDENCE", "EXCEPTION"),
        ("pay_Gz8x1100", "INSUFFICIENT_EVIDENCE", "INSUFFICIENT_DATA"),
    ],
)
def test_golden_scenarios_ask_question(txn_id, expected_diag, expected_status):
    """Verifies that all 6 core taxonomy states can be queried via the AI Q&A API."""
    resp = client.post(
        "/api/investigate/ask",
        json={
            "identifier": txn_id,
            "question": "What is the diagnosis and what happened to this payment?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert expected_diag in data["answer"]
    assert expected_diag in data["internal_summary"]


# ============================================================================
# 3. Raw Dataset Immutability Check
# ============================================================================

def test_raw_csv_immutability_after_agent_operations():
    """Verifies that Phase 8 operations never mutate raw CSV files."""
    for filename, expected_hash in BASELINE_HASHES.items():
        filepath = DATA_DIR / filename
        assert filepath.exists(), f"Missing file: {filepath}"
        actual_hash = compute_sha256(filepath)
        assert actual_hash == expected_hash, (
            f"MUTATION DETECTED in {filename}! Expected {expected_hash}, got {actual_hash}"
        )
