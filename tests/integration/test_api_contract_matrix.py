"""
tests/integration/test_api_contract_matrix.py

Automated Contract Matrix Verification across all 9 REST endpoints:
1. GET /api/health
2. POST /api/investigate
3. GET /api/investigate/{identifier}
4. POST /api/query
5. POST /api/investigate/ask
6. POST /api/follow-up
7. POST /api/conversation/reset
8. GET /api/exceptions
9. GET /api/settlements

Verifies Valid, Invalid, Not Found, Failure, and Contract conformity.
"""

import pytest
from fastapi.testclient import TestClient
from server.main import app

@pytest.fixture
def client():
    return TestClient(app)


# 1. /api/health
def test_contract_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "settlement-qa-agent"
    assert "diagnostics" in data
    assert data["diagnostics"]["overall_status"] == "READY"


# 2. /api/investigate
def test_contract_investigate_valid(client):
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["transaction_id"] == "pay_Gz8x1001"
    assert "diagnosis" in data
    assert "evidence_pack" in data
    assert "explanation" in data

def test_contract_investigate_empty_query(client):
    resp = client.post("/api/investigate", json={"query": "   "})
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "INVALID_QUERY"

def test_contract_investigate_not_found(client):
    resp = client.post("/api/investigate", json={"query": "pay_NONEXISTENT_9999"})
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "TRANSACTION_NOT_FOUND"

def test_contract_investigate_unsupported_type(client):
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1001", "query_type": "UNKNOWN_SYSTEM"})
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "UNSUPPORTED_IDENTIFIER_TYPE"


# 3. /api/investigate/{identifier}
def test_contract_investigate_get_valid(client):
    resp = client.get("/api/investigate/pay_Gz8x1001")
    assert resp.status_code == 200
    assert resp.json()["transaction_id"] == "pay_Gz8x1001"

def test_contract_investigate_get_not_found(client):
    resp = client.get("/api/investigate/pay_NONEXISTENT_9999")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "TRANSACTION_NOT_FOUND"


# 4. /api/query
def test_contract_query_by_id(client):
    resp = client.post("/api/query", json={"query": "pay_Gz8x1001"})
    assert resp.status_code == 200
    assert resp.json()["transaction_id"] == "pay_Gz8x1001"

def test_contract_query_by_date(client):
    resp = client.post("/api/query", json={"query": "2026-09-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_count" in data
    assert "settlements" in data

def test_contract_query_empty(client):
    resp = client.post("/api/query", json={"query": ""})
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "INVALID_QUERY"


# 5. /api/investigate/ask
def test_contract_ask_valid(client):
    resp = client.post("/api/investigate/ask", json={
        "identifier": "pay_Gz8x1001",
        "question": "Was this payment settled?",
    })
    assert resp.status_code == 200
    assert "answer" in resp.json()
    assert resp.json()["conversation_id"] is not None

def test_contract_ask_empty_question(client):
    resp = client.post("/api/investigate/ask", json={
        "identifier": "pay_Gz8x1001",
        "question": "   ",
    })
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "INVALID_QUERY"

def test_contract_ask_not_found(client):
    resp = client.post("/api/investigate/ask", json={
        "identifier": "pay_NONEXISTENT_9999",
        "question": "Status?",
    })
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "TRANSACTION_NOT_FOUND"


# 6. /api/follow-up
def test_contract_follow_up_parity(client):
    resp = client.post("/api/follow-up", json={
        "identifier": "pay_Gz8x1001",
        "question": "What is the status?",
    })
    assert resp.status_code == 200
    assert "answer" in resp.json()


# 7. /api/conversation/reset
def test_contract_conversation_reset(client):
    # First create a conversation
    resp = client.post("/api/investigate/ask", json={
        "identifier": "pay_Gz8x1001",
        "question": "Status?",
    })
    conv_id = resp.json()["conversation_id"]
    
    # Reset it
    reset_resp = client.post("/api/conversation/reset", json={"conversation_id": conv_id})
    assert reset_resp.status_code == 200
    assert reset_resp.json()["success"] is True


# 8. /api/exceptions
def test_contract_exceptions_unfiltered(client):
    resp = client.get("/api/exceptions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_exceptions"] == 17
    assert data["critical_count"] == 4

def test_contract_exceptions_date_filter(client):
    resp = client.get("/api/exceptions?date=2026-09-01")
    assert resp.status_code == 200
    assert resp.json()["total_exceptions"] == 5

def test_contract_exceptions_invalid_date(client):
    resp = client.get("/api/exceptions?date=not-a-date")
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "INVALID_DATE_FORMAT"


# 9. /api/settlements
def test_contract_settlements_unfiltered(client):
    resp = client.get("/api/settlements")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 101

def test_contract_settlements_date_filter(client):
    resp = client.get("/api/settlements?date=2026-09-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filtered_count"] == 36

def test_contract_settlements_invalid_date(client):
    resp = client.get("/api/settlements?date=invalid-date-format")
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "INVALID_DATE_FORMAT"
