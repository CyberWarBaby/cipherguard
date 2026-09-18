import os
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

TEST_API_KEY = "sf_test_shipfast_cipherguard_321"

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Sets environment variable for SHIPFAST_API_KEY during tests."""
    monkeypatch.setenv("SHIPFAST_API_KEY", TEST_API_KEY)

# ------------------------------------------------------------------------------
# Health Probe Tests (Unauthenticated)
# ------------------------------------------------------------------------------
def test_health_check_unauthenticated():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "shipfast-api"

def test_readiness_check_unauthenticated():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True

# ------------------------------------------------------------------------------
# API Key Authentication Tests — Missing / Invalid Headers (401 Unauthorized)
# ------------------------------------------------------------------------------
def test_get_order_missing_api_key():
    response = client.get("/orders/ord_101")
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]

def test_get_order_invalid_api_key():
    response = client.get("/orders/ord_101", headers={"X-API-Key": "sf_test_invalid_key_12345"})
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]

def test_post_order_missing_api_key():
    payload = {"customer_id": "cust_101", "destination_city": "Abuja", "items_count": 2}
    response = client.post("/orders", json=payload)
    assert response.status_code == 401

def test_post_order_invalid_api_key():
    payload = {"customer_id": "cust_101", "destination_city": "Abuja", "items_count": 2}
    response = client.post("/orders", json=payload, headers={"X-API-Key": "wrong_key"})
    assert response.status_code == 401

def test_get_customer_address_missing_api_key():
    response = client.get("/customers/cust_101/address")
    assert response.status_code == 401

def test_get_customer_address_invalid_api_key():
    response = client.get("/customers/cust_101/address", headers={"X-API-Key": "wrong_key"})
    assert response.status_code == 401

def test_get_admin_stats_missing_api_key():
    response = client.get("/admin/internal-stats")
    assert response.status_code == 401

# ------------------------------------------------------------------------------
# API Key Authentication Tests — Valid Key (Success)
# ------------------------------------------------------------------------------
def test_get_order_valid_api_key():
    response = client.get("/orders/ord_101", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == "ord_101"
    assert data["status"] == "shipped"
    assert data["carrier"] == "ShipFast Logistics"
    # Ensure API Key is not leaked in response
    assert TEST_API_KEY not in str(data)

def test_post_order_valid_api_key():
    payload = {"customer_id": "cust_101", "destination_city": "Lagos", "items_count": 3}
    response = client.post("/orders", json=payload, headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "processing"
    assert "order_id" in data
    # Ensure API Key is not leaked in response
    assert TEST_API_KEY not in str(data)

def test_get_customer_address_valid_api_key():
    response = client.get("/customers/cust_101/address", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "cust_101"
    assert data["city"] == "Abuja"

def test_get_admin_stats_valid_api_key():
    response = client.get("/admin/internal-stats", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    assert response.json()["message"] == "Simulated ShipFast admin metrics"

def test_unconfigured_server_key_rejects_requests(monkeypatch):
    """If SHIPFAST_API_KEY is unset or empty, requests should fail with 401 Unauthorized."""
    monkeypatch.delenv("SHIPFAST_API_KEY", raising=False)
    response = client.get("/orders/ord_101", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 401
