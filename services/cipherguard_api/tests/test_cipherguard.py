import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
import httpx
import jwt
from datetime import datetime, timedelta, timezone
from app.main import app
from app.config import settings
from app.db.client import memory_store

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_store():
    """Resets memory store before each test."""
    memory_store.reset()

def create_mock_jwt(user_id: str, email: str, org_id: str, role: str = "admin", expired: bool = False) -> str:
    secret = settings.SUPABASE_JWT_SECRET or "dev-test-secret"
    now = datetime.now(timezone.utc)
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "app_metadata": {
            "organization_id": org_id,
            "role": role
        },
        "exp": exp.timestamp()
    }
    return jwt.encode(payload, secret, algorithm="HS256")

# ------------------------------------------------------------------------------
# 1. Health & Diagnostics Tests
# ------------------------------------------------------------------------------
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "CipherGuard API"

def test_readiness_check():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True

def test_liveness_check():
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json()["live"] is True

# ------------------------------------------------------------------------------
# 2. Authentication & Authorization & Identity Tests
# ------------------------------------------------------------------------------
def test_auth_me_endpoint():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "user_id" in data["data"]
    assert "organization_id" in data["data"]

def test_organization_current():
    response = client.get("/api/v1/organizations/current")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["slug"] == "nitda-defense"

# ------------------------------------------------------------------------------
# 3. Third-Party Integrations CRUD & Multi-Vendor Inventory Tests
# ------------------------------------------------------------------------------
def test_list_integrations():
    response = client.get("/api/v1/integrations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert any(i["slug"] == "shipfast" for i in data)
    assert any(i["slug"] == "payflex" for i in data)
    
    # Ensure internal Docker URL and auth credentials are not leaked to public clients
    shipfast_intg = next(i for i in data if i["slug"] == "shipfast")
    assert "shipfast-api:" not in str(shipfast_intg.get("base_url", ""))
    assert shipfast_intg["gateway_url"] == "/api/integrations/shipfast"
    assert shipfast_intg["protected_endpoint"] == "/api/integrations/shipfast"

    payflex_intg = next(i for i in data if i["slug"] == "payflex")
    assert "auth_credential" not in payflex_intg  # Never exposed
    assert payflex_intg["has_auth_credential"] is True
    assert payflex_intg["gateway_url"] == "/api/integrations/payflex"

def test_create_and_get_integration():
    payload = {
        "name": "GitHub Webhooks",
        "slug": "github-webhooks",
        "category": "Other",
        "upstream_url": "https://api.github.com",
        "auth_type": "bearer_token",
        "auth_credential": "ghp_secret_token_12345",
        "status": "monitoring",
        "description": "Code security webhook integration."
    }
    create_resp = client.post("/api/v1/integrations", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["slug"] == "github-webhooks"
    assert created_data["gateway_url"] == "/api/integrations/github-webhooks"
    assert "auth_credential" not in created_data
    assert created_data["has_auth_credential"] is True

    # Fetch integration metadata
    get_resp = client.get("/api/v1/integrations/github-webhooks")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "GitHub Webhooks"
    assert "auth_credential" not in get_resp.json()

def test_prevent_duplicate_integration_slug():
    payload = {
        "name": "ShipFast Duplicate",
        "slug": "shipfast",  # Already exists
        "category": "Shipping"
    }
    resp = client.post("/api/v1/integrations", json=payload)
    assert resp.status_code == 409

def test_create_integration_blocks_ssrf_metadata():
    payload = {
        "name": "Attacker Target",
        "slug": "ssrf-target",
        "category": "Other",
        "upstream_url": "http://169.254.169.254/latest/meta-data/"
    }
    resp = client.post("/api/v1/integrations", json=payload)
    assert resp.status_code == 400
    assert "restricted/private network" in resp.json()["message"]

# ------------------------------------------------------------------------------
# 4. Inline Security Proxy & Policy Enforcement (Scenarios A, B, C)
# ------------------------------------------------------------------------------
def test_proxy_scenario_a_allowed_shipfast_order_request():
    """
    TEST A — ALLOW:
    Client / API Playground -> Kong -> CipherGuard -> Policy Evaluation -> ALLOW -> ShipFast -> Response.
    """
    mock_upstream_response = httpx.Response(
        status_code=200,
        json={"order_id": "123", "status": "shipped", "carrier": "ShipFast Logistics"},
        headers={"content-type": "application/json"}
    )

    with patch.object(httpx.AsyncClient, "request", return_value=mock_upstream_response):
        # Test protected generic path /api/integrations/{slug}/orders/123
        response = client.get("/api/integrations/shipfast/orders/123")
        assert response.status_code == 200
        assert response.json()["order_id"] == "123"
        assert response.headers["x-cipherguard-decision"] == "ALLOW"
        assert "x-cipherguard-risk-score" in response.headers

    # Verify telemetry event was recorded
    events_resp = client.get("/api/v1/traffic")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 1
    recent = events[0]
    assert recent["integration_name"] == "shipfast"
    assert recent["endpoint"] == "/orders/123"
    assert recent["decision"] == "ALLOW"
    assert recent["is_violation"] is False

def test_proxy_scenario_b_blocked_shipfast_admin_stats_request():
    """
    TEST B — BLOCK:
    Client / API Playground -> Kong -> CipherGuard -> Policy Evaluation -> BLOCK -> 403 Response.
    Upstream third-party service must NEVER be called.
    """
    with patch.object(httpx.AsyncClient, "request") as mock_request:
        response = client.get("/api/integrations/shipfast/admin/internal-stats")
        assert response.status_code == 403
        data = response.json()
        assert data["status"] == "blocked"
        assert data["decision"] == "BLOCK"
        assert "Administrative/restricted endpoint access is prohibited" in data["reason"]
        assert any("Blocked pattern '/admin/*'" in p for p in data["matched_policies"])

        # Upstream third-party service was NEVER called
        mock_request.assert_not_called()

    # Verify that a critical security alert was automatically generated
    alerts_resp = client.get("/api/v1/alerts?status=open")
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert len(alerts) >= 1
    critical_alert = next((a for a in alerts if a["severity"] == "critical"), None)
    assert critical_alert is not None
    assert "Blocked Request on shipfast" in critical_alert["title"]

    # Verify traffic audit event records the block
    events_resp = client.get("/api/v1/traffic?decision=BLOCK")
    assert events_resp.status_code == 200
    blocked_events = events_resp.json()
    assert len(blocked_events) >= 1
    assert blocked_events[0]["decision"] == "BLOCK"
    assert blocked_events[0]["status_code"] == 403

def test_proxy_scenario_c_generic_second_integration_payflex():
    """
    TEST C — GENERIC SECOND INTEGRATION (PayFlex Payments):
    Demonstrates that CipherGuard protects an entirely different third-party provider (Payments)
    using the exact same security gateway, dynamic policy resolution, and server-side auth injection.
    """
    mock_upstream_response = httpx.Response(
        status_code=200,
        json={"payment_id": "pay_987", "status": "succeeded", "amount": 5000.0, "currency": "NGN"},
        headers={"content-type": "application/json"}
    )

    # 1. ALLOW request to PayFlex payment charge
    with patch.object(httpx.AsyncClient, "request", return_value=mock_upstream_response) as mock_request:
        charge_payload = {"amount": 5000.0, "currency": "NGN", "customer_id": "cust_982"}
        response = client.post("/api/integrations/payflex/payments/charge", json=charge_payload)
        assert response.status_code == 200
        assert response.json()["payment_id"] == "pay_987"
        assert response.headers["x-cipherguard-decision"] == "ALLOW"

        # Verify server-side API Key credential injection
        assert mock_request.called
        call_kwargs = mock_request.call_args[1]
        headers_sent = call_kwargs["headers"]
        assert headers_sent.get("x-api-key") == "pf_live_sec_demo12345"

    # 2. BLOCK request to PayFlex restricted vault keys
    with patch.object(httpx.AsyncClient, "request") as mock_request:
        blocked_resp = client.get("/api/integrations/payflex/admin/vault-keys")
        assert blocked_resp.status_code == 403
        data = blocked_resp.json()
        assert data["decision"] == "BLOCK"
        assert "Administrative/restricted endpoint access is prohibited" in data["reason"]
        mock_request.assert_not_called()

def test_proxy_blocks_sqli_threat():
    """
    Threat Shield: SQL Injection signature in query string is intercepted and blocked.
    """
    with patch.object(httpx.AsyncClient, "request") as mock_request:
        response = client.get("/api/integrations/shipfast/orders?id=1' OR '1'='1")
        assert response.status_code == 403
        data = response.json()
        assert data["decision"] == "BLOCK"
        assert "SQL injection" in data["reason"]
        mock_request.assert_not_called()

def test_proxy_blocks_path_traversal():
    """
    Threat Shield: Directory traversal sequence in query parameter is intercepted and blocked.
    """
    with patch.object(httpx.AsyncClient, "request") as mock_request:
        response = client.get("/api/integrations/shipfast/orders?file=../../etc/passwd")
        assert response.status_code == 403
        data = response.json()
        assert data["decision"] == "BLOCK"
        assert "traversal" in data["reason"].lower()
        mock_request.assert_not_called()

# ------------------------------------------------------------------------------
# 5. Traffic Telemetry & Statistics Tests
# ------------------------------------------------------------------------------
def test_traffic_statistics_endpoint():
    # Ingest a clean event
    client.post("/api/v1/events", json={
        "integration_name": "shipfast",
        "method": "GET",
        "endpoint": "/orders/101",
        "status_code": 200,
        "latency_ms": 25,
        "decision": "ALLOW"
    })

    # Ingest a blocked event
    client.post("/api/v1/events", json={
        "integration_name": "shipfast",
        "method": "GET",
        "endpoint": "/admin/config",
        "status_code": 403,
        "latency_ms": 5,
        "decision": "BLOCK"
    })

    resp = client.get("/api/v1/traffic/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_requests"] >= 2
    assert stats["allowed_requests"] >= 1
    assert stats["blocked_requests"] >= 1
    assert "top_blocked_endpoints" in stats

# ------------------------------------------------------------------------------
# 6. Security Alerts Triage & Status Update Tests
# ------------------------------------------------------------------------------
def test_alerts_lookup_and_status_update():
    # Trigger blocked request to create an alert
    client.get("/api/integrations/shipfast/admin/internal-stats")

    alerts = client.get("/api/v1/alerts").json()
    assert len(alerts) >= 1
    alert_id = alerts[0]["id"]

    # Get single alert detail
    detail = client.get(f"/api/v1/alerts/{alert_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == alert_id

    # Update alert status to resolved
    patch_resp = client.patch(f"/api/v1/alerts/{alert_id}", json={
        "status": "resolved",
        "notes": "Verified client was internal test suite. Access pattern authorized."
    })
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "resolved"
    assert patch_resp.json()["resolved_at"] is not None

# ------------------------------------------------------------------------------
# 7. SSRF Protection & Scanner Security
# ------------------------------------------------------------------------------
def test_scan_ssrf_protection_blocked_metadata_ip():
    payload = {
        "target_name": "Metadata Attack Target",
        "target_url": "http://169.254.169.254/latest/meta-data/"
    }
    resp = client.post("/api/v1/scans", json=payload)
    assert resp.status_code == 400
    assert "restricted/private network" in resp.json()["message"]

def test_scan_ssrf_protection_invalid_scheme():
    payload = {
        "target_name": "File Scheme Attack",
        "target_url": "file:///etc/passwd"
    }
    resp = client.post("/api/v1/scans", json=payload)
    assert resp.status_code == 400

# ------------------------------------------------------------------------------
# 8. Executive Risk Intelligence & Posture Scoring
# ------------------------------------------------------------------------------
def test_analytics_risk_overview():
    resp = client.get("/api/v1/analytics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_risk_score" in data
    assert "overall_risk_level" in data
    assert "total_monitored_integrations" in data
    assert "integration_risk_breakdown" in data
    assert len(data["integration_risk_breakdown"]) >= 2
    assert "risk_factors" in data["integration_risk_breakdown"][0]
