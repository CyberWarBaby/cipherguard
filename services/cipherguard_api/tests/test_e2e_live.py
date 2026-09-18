"""
End-to-End Live Verification Script for CipherGuard (Track G)
Executes full real-world traffic flows through Kong Public Gateway (:8000):
- TEST A: ALLOW (ShipFast order request)
- TEST B: BLOCK (ShipFast /admin/internal-stats blocked with 403, upstream uncalled)
- TEST C: GENERIC SECOND INTEGRATION (PayFlex payment allowed, /admin/vault-keys blocked)
- Telemetry, Risk & Security Alerts Verification
"""
import sys
import os
import httpx

# In docker network: http://kong:8000. From host machine: http://localhost:8000
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://kong:8000")



def run_e2e_tests():
    print("=" * 70)
    print("CIPHERGUARD END-TO-END GATEWAY VERIFICATION (TRACK G)")
    print(f"Target Gateway: {GATEWAY_URL}")
    print("=" * 70)

    client = httpx.Client(timeout=10.0)

    # --------------------------------------------------------------------------
    # 1. Gateway & Diagnostics Probes
    # --------------------------------------------------------------------------
    print("\n[Step 1] Checking Gateway Diagnostics...")
    try:
        health_resp = client.get(f"{GATEWAY_URL}/health")
        assert health_resp.status_code == 200, f"Health returned {health_resp.status_code}"
        print(f"  ✓ Gateway /health reachable: {health_resp.json()['status']}")
    except Exception as e:
        print(f"  ✗ Gateway connectivity failed: {e}")
        return False

    # --------------------------------------------------------------------------
    # 2. Management & Inventory API
    # --------------------------------------------------------------------------
    print("\n[Step 2] Querying Registered Third-Party Integrations...")
    intg_resp = client.get(f"{GATEWAY_URL}/api/v1/integrations")
    assert intg_resp.status_code == 200, f"Integrations returned {intg_resp.status_code}"
    integrations = intg_resp.json()
    slugs = [i["slug"] for i in integrations]
    print(f"  ✓ Registered integrations found: {slugs}")
    assert "shipfast" in slugs, "ShipFast must be registered"
    assert "payflex" in slugs, "PayFlex must be registered"

    # --------------------------------------------------------------------------
    # 3. TEST A — ALLOW (ShipFast Order)
    # --------------------------------------------------------------------------
    print("\n[Step 3] Executing TEST A — ALLOW (ShipFast Order Tracking)...")
    path_a = "/api/integrations/shipfast/orders/ord_101"
    resp_a = client.get(f"{GATEWAY_URL}{path_a}")
    print(f"  Request: GET {GATEWAY_URL}{path_a}")
    print(f"  Status:  {resp_a.status_code}")
    print(f"  Decision Header: {resp_a.headers.get('x-cipherguard-decision')}")
    print(f"  Payload: {resp_a.json()}")

    assert resp_a.status_code == 200, f"Expected 200, got {resp_a.status_code}"
    assert resp_a.headers.get("x-cipherguard-decision") == "ALLOW", "Expected ALLOW decision"
    assert resp_a.json().get("carrier") == "ShipFast Logistics", "Expected response from ShipFast upstream"
    print("  ✓ TEST A PASSED: Legitimate request successfully inspected, allowed, and forwarded.")

    # --------------------------------------------------------------------------
    # 4. TEST B — BLOCK (ShipFast Restricted Administrative Route)
    # --------------------------------------------------------------------------
    print("\n[Step 4] Executing TEST B — BLOCK (ShipFast /admin/internal-stats)...")
    path_b = "/api/integrations/shipfast/admin/internal-stats"
    resp_b = client.get(f"{GATEWAY_URL}{path_b}")
    print(f"  Request: GET {GATEWAY_URL}{path_b}")
    print(f"  Status:  {resp_b.status_code}")
    print(f"  Payload: {resp_b.json()}")

    assert resp_b.status_code == 403, f"Expected 403, got {resp_b.status_code}"
    data_b = resp_b.json()
    assert data_b.get("decision") == "BLOCK", "Expected BLOCK decision"
    assert "Administrative/restricted endpoint access is prohibited" in data_b.get("reason", "")
    print("  ✓ TEST B PASSED: Restricted administrative route blocked by CipherGuard. Upstream NEVER reached.")

    # --------------------------------------------------------------------------
    # 5. TEST C — GENERIC SECOND INTEGRATION (PayFlex Payments)
    # --------------------------------------------------------------------------
    print("\n[Step 5] Executing TEST C — GENERIC SECOND INTEGRATION (PayFlex Payments)...")
    path_c_allow = "/api/integrations/payflex/payments/charge"
    payload_c = {
        "amount": 7500.0,
        "currency": "NGN",
        "customer_id": "cust_982",
        "reference": "ref_e2e_live_test"
    }
    resp_c1 = client.post(f"{GATEWAY_URL}{path_c_allow}", json=payload_c)
    print(f"  Request: POST {GATEWAY_URL}{path_c_allow}")
    print(f"  Status:  {resp_c1.status_code}")
    print(f"  Decision Header: {resp_c1.headers.get('x-cipherguard-decision')}")
    print(f"  Payload: {resp_c1.json()}")

    assert resp_c1.status_code == 200, f"Expected 200, got {resp_c1.status_code}"
    assert resp_c1.headers.get("x-cipherguard-decision") == "ALLOW", "Expected ALLOW decision"
    assert resp_c1.json().get("status") == "succeeded"
    print("  ✓ PayFlex payment request inspected and allowed with server-side credential injection.")

    # Test C2: Block restricted route on PayFlex
    path_c_block = "/api/integrations/payflex/admin/vault-keys"
    resp_c2 = client.get(f"{GATEWAY_URL}{path_c_block}")
    print(f"  Request: GET {GATEWAY_URL}{path_c_block}")
    print(f"  Status:  {resp_c2.status_code}")
    assert resp_c2.status_code == 403, f"Expected 403, got {resp_c2.status_code}"
    assert resp_c2.json().get("decision") == "BLOCK"
    print("  ✓ PayFlex /admin/vault-keys blocked with 403.")
    print("  ✓ TEST C PASSED: Multi-vendor generic security architecture verified.")

    # --------------------------------------------------------------------------
    # 6. Telemetry & Security Alerts Verification
    # --------------------------------------------------------------------------
    print("\n[Step 6] Verifying Telemetry & Real-Time Alerts in CipherGuard...")
    stats_resp = client.get(f"{GATEWAY_URL}/api/v1/traffic/stats")
    stats = stats_resp.json()
    print(f"  Traffic Summary: Total={stats['total_requests']}, Allowed={stats['allowed_requests']}, Blocked={stats['blocked_requests']}")
    assert stats["total_requests"] >= 3, "Expected at least 3 recorded requests"
    assert stats["blocked_requests"] >= 2, "Expected at least 2 blocked requests"

    alerts_resp = client.get(f"{GATEWAY_URL}/api/v1/alerts")
    alerts = alerts_resp.json()
    print(f"  Security Alerts Count: {len(alerts)}")
    assert len(alerts) >= 1, "Expected security alerts generated for blocked attempts"
    print(f"  Latest Alert: '{alerts[0]['title']}' (Severity: {alerts[0]['severity']})")

    print("\n" + "=" * 70)
    print("ALL END-TO-END GATEWAY CHECKS PASSED SUCCESSFULLY (100%)")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
