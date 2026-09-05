from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "settlement-qa-agent"
    assert "version" in data
    assert "records_loaded" in data
    assert data["records_loaded"]["gateway"] == 100
    assert data["records_loaded"]["bank"] == 90
    assert data["records_loaded"]["ledger"] == 88
    
    # Phase 14 Environment Diagnostics
    assert "diagnostics" in data
    diag = data["diagnostics"]
    assert diag["application"] == "READY"
    assert diag["backend"] == "READY"
    assert diag["dataset"] == "VERIFIED"
    assert diag["frontend_config"] == "READY"
    assert diag["deterministic_fallback"] == "READY"
    assert diag["overall_status"] == "READY"
    assert diag["gemini_provider"] in ("CONFIGURED", "NOT_CONFIGURED")
    assert diag["groq_provider"] in ("CONFIGURED", "NOT_CONFIGURED")
    
    # Secret Hygiene Verification: Ensure zero secret keys leaked
    serialized = str(data).lower()
    for sensitive in ["api_key", "secret", "token", "bearer", "password", "sk-", "ai_key"]:
        assert sensitive not in serialized, f"Sensitive term '{sensitive}' found in health response!"

