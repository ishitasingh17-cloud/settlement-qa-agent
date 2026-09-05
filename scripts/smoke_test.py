#!/usr/bin/env python3
"""
scripts/smoke_test.py

Deterministic end-to-end integration smoke test exercising the complete product.
Exercises:
1. Health & Environment Diagnostics
2. Canonical Scenario 01 (pay_Gz8x1001 -> SUCCESSFULLY_SETTLED)
3. Follow-up Q&A on SC-01
4. Conversation Thread Reset
5. Canonical Scenario 05 (pay_Gz8x1052 -> CONFLICTING_EVIDENCE)
6. Follow-up Q&A on SC-05 & Context Isolation (0% fact leakage)
7. Exception Dashboard & Date Filtering
8. Drilldown into SC-02 (pay_Gz8x1000 -> MISSING_BANK_RECORD)
9. Canonical Scenario 06 (pay_Gz8x1100 -> INSUFFICIENT_EVIDENCE)
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from decimal import Decimal
from fastapi.testclient import TestClient
from server.main import app

def run_smoke_test():
    print("=" * 80)
    print("PS-8 SETTLEMENT Q&A AGENT - END-TO-END SMOKE TEST")
    print("=" * 80)

    client = TestClient(app)
    passed_steps = 0
    total_steps = 9

    # Step 1: Health check & diagnostics
    print("[1/9] Probing GET /api/health...")
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Health check failed: {resp.status_code}"
    health = resp.json()
    assert health["status"] == "ok"
    assert health["diagnostics"]["application"] == "READY"
    assert health["diagnostics"]["deterministic_fallback"] == "READY"
    print(f"      OK -> Status: {health['status']}, Mode: {health.get('mode')}")
    passed_steps += 1

    # Step 2: SC-01 Investigation (pay_Gz8x1001)
    print("[2/9] Investigating SC-01 (pay_Gz8x1001 - Clean Settlement)...")
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1001"})
    assert resp.status_code == 200, f"SC-01 failed: {resp.text}"
    sc1 = resp.json()
    assert sc1["diagnosis"] == "SUCCESSFULLY_SETTLED"
    assert sc1["status"] == "RESOLVED"
    assert sc1["severity"] == "NONE"
    assert sc1["evidence_pack"]["gateway"]["gross_amount"] == "111358"
    print(f"      OK -> Diagnosis: {sc1['diagnosis']}, Gross: {sc1['evidence_pack']['gateway']['gross_amount']} cents")
    passed_steps += 1

    # Step 3: Follow-up question on SC-01
    print("[3/9] Asking Follow-Up Question on SC-01...")
    resp = client.post("/api/investigate/ask", json={
        "identifier": "pay_Gz8x1001",
        "question": "What is the settlement status of this transaction?",
    })
    assert resp.status_code == 200, f"Follow-up failed: {resp.text}"
    q1 = resp.json()
    conv_id = q1["conversation_id"]
    assert conv_id is not None
    assert "settled" in q1["answer"].lower() or "verified" in q1["answer"].lower()
    print(f"      OK -> Answer received, Conversation ID: {conv_id}")
    passed_steps += 1

    # Step 4: Conversation Thread Reset
    print("[4/9] Testing POST /api/conversation/reset...")
    resp = client.post("/api/conversation/reset", json={"conversation_id": conv_id})
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    print("      OK -> Conversation thread reset successfully.")
    passed_steps += 1

    # Step 5: SC-05 Investigation (pay_Gz8x1052 - Conflicting Evidence)
    print("[5/9] Investigating SC-05 (pay_Gz8x1052 - Conflicting Evidence)...")
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1052"})
    assert resp.status_code == 200
    sc5 = resp.json()
    assert sc5["diagnosis"] == "CONFLICTING_EVIDENCE"
    assert sc5["status"] == "EXCEPTION"
    assert sc5["severity"] == "CRITICAL"
    print(f"      OK -> Diagnosis: {sc5['diagnosis']}, Severity: {sc5['severity']}")
    passed_steps += 1

    # Step 6: Follow-up question on SC-05 & Context Isolation Check
    print("[6/9] Verifying Context Isolation on SC-05 inquiry...")
    resp = client.post("/api/investigate/ask", json={
        "identifier": "pay_Gz8x1052",
        "question": "Why is this transaction flagged as an exception?",
        "conversation_id": conv_id,
    })
    assert resp.status_code == 200
    q5 = resp.json()
    # Ensure zero fact leakage from SC-01
    assert "pay_Gz8x1001" not in q5["answer"], "Fact leakage: found pay_Gz8x1001 in pay_Gz8x1052 response!"
    assert "111358" not in q5["answer"], "Fact leakage: found 111358 amount in pay_Gz8x1052 response!"
    print("      OK -> Context isolation preserved (0% fact leakage).")
    passed_steps += 1

    # Step 7: Exception Dashboard & Date Filtering
    print("[7/9] Testing Exception Dashboard GET /api/exceptions...")
    resp = client.get("/api/exceptions")
    assert resp.status_code == 200
    dash = resp.json()
    assert dash["total_exceptions"] == 17
    assert dash["critical_count"] == 4
    
    # Date filter test
    resp_date = client.get("/api/exceptions?date=2026-09-01")
    assert resp_date.status_code == 200
    assert resp_date.json()["total_exceptions"] == 5
    print(f"      OK -> Total Exceptions: {dash['total_exceptions']}, Date 2026-09-01 Filter: {resp_date.json()['total_exceptions']}")
    passed_steps += 1

    # Step 8: Drilldown into SC-02 (pay_Gz8x1000 - Missing Bank)
    print("[8/9] Executing Drilldown into SC-02 (pay_Gz8x1000)...")
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1000"})
    assert resp.status_code == 200
    sc2 = resp.json()
    assert sc2["diagnosis"] == "MISSING_BANK_RECORD"
    assert sc2["evidence_pack"]["bank"]["present"] is False
    print(f"      OK -> Diagnosis: {sc2['diagnosis']}, Bank record verified absent.")
    passed_steps += 1

    # Step 9: SC-06 Investigation (pay_Gz8x1100 - Insufficient Evidence)
    print("[9/9] Investigating SC-06 (pay_Gz8x1100 - Orphan Bank/Ledger Record)...")
    resp = client.post("/api/investigate", json={"query": "pay_Gz8x1100"})
    assert resp.status_code == 200
    sc6 = resp.json()
    assert sc6["diagnosis"] == "INSUFFICIENT_EVIDENCE"
    assert sc6["evidence_pack"]["gateway"]["present"] is False
    print(f"      OK -> Diagnosis: {sc6['diagnosis']}, Gateway anchor verified absent.")
    passed_steps += 1

    print("=" * 80)
    print(f"[+] SMOKE TEST COMPLETED: {passed_steps}/{total_steps} STEPS PASSED (100% PASS RATE).")
    print("=" * 80)
    return True

if __name__ == "__main__":
    try:
        success = run_smoke_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[!] Smoke test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
