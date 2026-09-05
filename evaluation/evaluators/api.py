"""
evaluation/evaluators/api.py

Evaluates the REST API layer, endpoint contracts, layer parity, and date filtering:
- Validates status codes, schemas, and error envelopes across all endpoints
- Compares Direct Deterministic Engine vs Investigation Service vs REST API for parity
- Validates Phase 12 Exception Dashboard metrics and multi-system date filters
"""

from fastapi.testclient import TestClient
from evaluation.models import APIMetrics
from server.main import app
from server.api.dependencies import get_trace_engine, get_evidence_builder
from server.api.service import InvestigationService
from server.api.dependencies import get_data_store, get_settlement_analyst, get_conversation_manager


def evaluate_api_layer() -> APIMetrics:
    client = TestClient(app)

    endpoints_evaluated = 0
    all_endpoints_healthy = True
    parity_mismatches = 0
    date_filter_correct = 0
    date_filter_total = 4

    # 1. Health endpoint
    endpoints_evaluated += 1
    r_health = client.get("/api/health")
    if r_health.status_code != 200 or r_health.json().get("status") != "ok":
        all_endpoints_healthy = False

    # 2. Investigate single transaction
    endpoints_evaluated += 1
    r_inv = client.post("/api/investigate", json={"query": "pay_Gz8x1001"})
    if r_inv.status_code != 200 or not r_inv.json().get("success"):
        all_endpoints_healthy = False

    # 3. Investigate not found
    endpoints_evaluated += 1
    r_404 = client.post("/api/investigate", json={"query": "pay_99999"})
    if r_404.status_code != 404:
        all_endpoints_healthy = False

    # 4. Unified Query endpoint
    endpoints_evaluated += 1
    r_query = client.post("/api/query", json={"query": "pay_Gz8x1001"})
    if r_query.status_code != 200:
        all_endpoints_healthy = False

    # 5. Ask question endpoint
    endpoints_evaluated += 1
    r_ask = client.post("/api/investigate/ask", json={"identifier": "pay_Gz8x1001", "question": "What is the status?"})
    if r_ask.status_code != 200:
        all_endpoints_healthy = False

    # 6. Follow-up endpoint
    endpoints_evaluated += 1
    r_fu = client.post("/api/follow-up", json={"identifier": "pay_Gz8x1001", "question": "What is the UTR?"})
    if r_fu.status_code != 200:
        all_endpoints_healthy = False

    # 7. Reset conversation endpoint
    endpoints_evaluated += 1
    r_reset = client.post("/api/conversation/reset", json={"conversation_id": "test_conv_id"})
    if r_reset.status_code != 200:
        all_endpoints_healthy = False

    # 8. Exceptions dashboard endpoint
    endpoints_evaluated += 1
    r_exc = client.get("/api/exceptions")
    if r_exc.status_code != 200 or r_exc.json().get("total_transactions") != 101:
        all_endpoints_healthy = False

    # -------------------------------------------------------------
    # Multi-Layer Parity Check
    # -------------------------------------------------------------
    # Direct Engine vs Service vs REST API
    sample_ids = ["pay_Gz8x1001", "pay_Gz8x1000", "pay_Gz8x1042", "pay_Gz8x1052"]
    trace_engine = get_trace_engine()
    evidence_builder = get_evidence_builder()
    service = InvestigationService(
        data_store=get_data_store(),
        trace_engine=trace_engine,
        evidence_builder=evidence_builder,
        settlement_analyst=get_settlement_analyst(),
        conversation_manager=get_conversation_manager(),
    )

    import asyncio

    for tid in sample_ids:
        # Layer 1: Direct Engine
        trace_direct = trace_engine.trace(tid)
        veo_direct = evidence_builder.build(trace_direct)

        # Layer 2: Investigation Service
        inv_service = asyncio.run(service.investigate(tid))

        # Layer 3: REST API
        inv_api = client.post("/api/investigate", json={"query": tid}).json()

        # Compare parity
        d1 = veo_direct.diagnosis.value
        d2 = inv_service.diagnosis.value
        d3 = inv_api["diagnosis"]

        s1 = veo_direct.status.value
        s2 = inv_service.status.value
        s3 = inv_api["status"]

        h1 = veo_direct.integrity_hash
        h2 = inv_service.evidence_pack.integrity_hash
        h3 = inv_api["evidence_pack"]["integrity_hash"]

        if not (d1 == d2 == d3 and s1 == s2 == s3 and h1 == h2 == h3):
            parity_mismatches += 1

    # -------------------------------------------------------------
    # Date Filtering Accuracy on /api/exceptions
    # -------------------------------------------------------------
    # Day 1: 2026-09-01 (36 total, 5 flagged)
    r_d1 = client.get("/api/exceptions?date=2026-09-01")
    if r_d1.status_code == 200 and r_d1.json().get("total_transactions") == 36 and r_d1.json().get("actionable_exceptions_count") == 5:
        date_filter_correct += 1

    # Day 2: 2026-09-02 (64 total, 11 flagged)
    r_d2 = client.get("/api/exceptions?date=2026-09-02")
    if r_d2.status_code == 200 and r_d2.json().get("total_transactions") == 64 and r_d2.json().get("actionable_exceptions_count") == 11:
        date_filter_correct += 1

    # Empty date: 1999-01-01 (0 total, 0 flagged)
    r_d3 = client.get("/api/exceptions?date=1999-01-01")
    if r_d3.status_code == 200 and r_d3.json().get("total_transactions") == 0 and r_d3.json().get("actionable_exceptions_count") == 0:
        date_filter_correct += 1

    # Invalid date: 400 Bad Request
    r_d4 = client.get("/api/exceptions?date=invalid-date")
    d4_body = r_d4.json() if r_d4.status_code == 400 else {}
    if r_d4.status_code == 400 and (d4_body.get("error") == "INVALID_DATE_FORMAT" or d4_body.get("detail", {}).get("error") == "INVALID_DATE_FORMAT"):
        date_filter_correct += 1

    date_filter_accuracy = round(date_filter_correct / date_filter_total, 4)

    return APIMetrics(
        endpoints_evaluated=endpoints_evaluated,
        all_endpoints_healthy=all_endpoints_healthy,
        parity_mismatches=parity_mismatches,
        date_filter_accuracy=date_filter_accuracy,
    )
