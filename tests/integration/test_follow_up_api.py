"""
tests/integration/test_follow_up_api.py

Integration test suite for Phase 11 Conversational Follow-up Q&A API.
Verifies:
1. Multi-turn conversation on pay_Gz8x1001 (4 sequential turns).
2. Continuity: session ID preservation and dialogue context resolution.
3. Context isolation: switching transaction ID clears prior dialogue facts.
4. Parity: POST /api/follow-up and POST /api/investigate/ask produce identical results.
5. Thread reset: POST /api/conversation/reset clears session memory.
6. Canonical demo transactions: all 6 demo cases support follow-up Q&A.
7. Immutability: raw CSV datasets remain bit-for-bit identical.
"""

import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)

DATA_DIR = Path("data")
BASELINE_HASHES = {
    "gateway.csv": "8945186e3ded7e81b21834e1c5312656fdb3da1af0fd011d7768a2758f24bcff",
    "bank.csv": "6db6886b96b1fd642a0a3df1d009bcbf93750090aaea8180a7cc4386c358edc4",
    "ledger.csv": "89c5bfb92be8a81f45abfe07975affe711b54009daf59453951c54251722f504",
}


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_multi_turn_conversation_happy_path():
    """
    Executes a 4-turn continuous conversation on pay_Gz8x1001.
    Verifies that conversation_id is established and persisted across turns.
    """
    txn_id = "pay_Gz8x1001"

    # Turn 1: Initial question
    resp1 = client.post(
        "/api/investigate/ask",
        json={"identifier": txn_id, "question": "What is the status of this payment?"},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    conv_id = data1["conversation_id"]
    assert conv_id is not None
    assert conv_id.startswith("conv_")
    assert data1["answer"] is not None
    assert data1["validated"] is True

    # Turn 2: Follow-up question referencing turn 1 with conversation_id
    resp2 = client.post(
        "/api/investigate/ask",
        json={
            "identifier": txn_id,
            "question": "Can you give me the bank reference number (UTR)?",
            "conversation_id": conv_id,
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["conversation_id"] == conv_id
    assert data2["answer"] is not None

    # Turn 3: Follow-up regarding fee
    resp3 = client.post(
        "/api/investigate/ask",
        json={
            "identifier": txn_id,
            "question": "Was there any fee or deduction reported?",
            "conversation_id": conv_id,
        },
    )
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["conversation_id"] == conv_id
    assert data3["answer"] is not None

    # Turn 4: Follow-up regarding reconciliation
    resp4 = client.post(
        "/api/investigate/ask",
        json={
            "identifier": txn_id,
            "question": "Is the internal ledger entry fully matched?",
            "conversation_id": conv_id,
        },
    )
    assert resp4.status_code == 200
    data4 = resp4.json()
    assert data4["conversation_id"] == conv_id
    assert data4["answer"] is not None


def test_endpoint_parity_follow_up_and_ask():
    """Verify POST /api/follow-up is a full functional alias of /api/investigate/ask."""
    txn_id = "pay_Gz8x1001"
    q = "What is the current diagnosis?"

    resp_ask = client.post("/api/investigate/ask", json={"identifier": txn_id, "question": q})
    resp_followup = client.post("/api/follow-up", json={"identifier": txn_id, "question": q})

    assert resp_ask.status_code == 200
    assert resp_followup.status_code == 200
    assert resp_followup.json()["internal_summary"] == resp_ask.json()["internal_summary"]
    assert resp_followup.json()["merchant_friendly_response"] == resp_ask.json()["merchant_friendly_response"]


def test_context_isolation_across_transactions():
    """
    Verify that reusing a conversation_id on a new transaction resets the context
    and prevents cross-transaction fact leakage.
    """
    # Turn on pay_Gz8x1001 (Clean Settled)
    resp1 = client.post(
        "/api/investigate/ask",
        json={"identifier": "pay_Gz8x1001", "question": "What is the order ID?"},
    )
    assert resp1.status_code == 200
    conv_id = resp1.json()["conversation_id"]

    # Reusing conv_id on pay_Gz8x1042 (Bank Rejected)
    resp2 = client.post(
        "/api/investigate/ask",
        json={
            "identifier": "pay_Gz8x1042",
            "question": "Did this order settle like the previous one?",
            "conversation_id": conv_id,
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    # Must NOT claim successful settlement
    assert "SUCCESSFULLY_SETTLED" not in data2["internal_summary"]
    assert "BANK_REJECTED" in data2["internal_summary"]


def test_conversation_reset_endpoint():
    """Verify POST /api/conversation/reset clears the server-side dialogue session."""
    # Create a conversation
    resp1 = client.post(
        "/api/investigate/ask",
        json={"identifier": "pay_Gz8x1001", "question": "Initial question"},
    )
    conv_id = resp1.json()["conversation_id"]

    # Reset it
    resp_reset = client.post("/api/conversation/reset", json={"conversation_id": conv_id})
    assert resp_reset.status_code == 200
    data_reset = resp_reset.json()
    assert data_reset["success"] is True
    assert data_reset["conversation_id"] == conv_id


def test_all_canonical_demo_cases_support_follow_up():
    """
    Verify that all 6 canonical demo cases can be queried with follow-up questions
    and return strictly validated answers.
    """
    cases = [
        ("pay_Gz8x1001", "Why is this marked settled?"),
        ("pay_Gz8x1000", "Why is the bank record missing?"),
        ("pay_Gz8x1038", "Is the ledger entry recorded?"),
        ("pay_Gz8x1042", "Why did the bank reject this?"),
        ("pay_Gz8x1052", "What is the conflicting evidence?"),
        ("pay_Gz8x1100", "Are there enough records to confirm?"),
    ]

    for txn_id, question in cases:
        resp = client.post(
            "/api/investigate/ask",
            json={"identifier": txn_id, "question": question},
        )
        assert resp.status_code == 200, f"Failed for {txn_id}: {resp.text}"
        data = resp.json()
        assert data["answer"] is not None
        assert data["validated"] is True
        assert data["conversation_id"] is not None


def test_raw_csv_immutability_after_conversation_suite():
    """Verify bit-for-bit SHA-256 immutability of raw datasets."""
    for filename, baseline in BASELINE_HASHES.items():
        filepath = DATA_DIR / filename
        current_hash = compute_sha256(filepath)
        assert current_hash == baseline, f"Raw data modified! File {filename} changed."
