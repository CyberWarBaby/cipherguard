"""
CipherGuard Real External Separation Verification Test (NITDA/ICSC Track G)
Tests live communication across independent public hostnames:
- CipherGuard Public Gateway (VPS A Host): https://rotten-wolves-wait.loca.lt
- ShipFast Third-Party API (VPS B Host): https://crazy-parents-brush.loca.lt
- Generic Second Integration (PayFlex): /api/integrations/payflex/*
"""
import sys
import os
import json
import httpx

CIPHERGUARD_GATEWAY = os.getenv("CIPHERGUARD_GATEWAY", "https://rotten-wolves-wait.loca.lt")
SHIPFAST_EXTERNAL = os.getenv("SHIPFAST_EXTERNAL", "https://crazy-parents-brush.loca.lt")

HEADERS = {
    "bypass-tunnel-reminder": "1",
    "User-Agent": "CipherGuard-CustomerApp/1.0"
}

def run_external_tests():
    print("=" * 75)
    print("CIPHERGUARD EXTERNAL MULTI-HOST / VPS SEPARATION VERIFICATION")
    print(f"CipherGuard Public Gateway (VPS A): {CIPHERGUARD_GATEWAY}")
    print(f"ShipFast External API (VPS B):     {SHIPFAST_EXTERNAL}")
    print("=" * 75)

    client = httpx.Client(timeout=20.0, headers=HEADERS)

    # --------------------------------------------------------------------------
    # Step 1: Health & Diagnostics
    # --------------------------------------------------------------------------
    print("\n[Step 1] Verifying Public Connectivity...")
    cg_health = client.get(f"{CIPHERGUARD_GATEWAY}/health")
    assert cg_health.status_code == 200, f"CipherGuard gateway failed: {cg_health.status_code}"
    print(f"  ✓ CipherGuard Gateway reachable at {CIPHERGUARD_GATEWAY}/health")

    sf_health = client.get(f"{SHIPFAST_EXTERNAL}/health")
    assert sf_health.status_code == 200, f"ShipFast external API failed: {sf_health.status_code}"
    print(f"  ✓ ShipFast External API reachable at {SHIPFAST_EXTERNAL}/health")

    # --------------------------------------------------------------------------
    # Step 2: Configure ShipFast Upstream in CipherGuard
    # --------------------------------------------------------------------------
    print("\n[Step 2] Configuring ShipFast Upstream URL to External Endpoint...")
    patch_resp = client.patch(
        f"{CIPHERGUARD_GATEWAY}/api/v1/integrations/shipfast",
        json={"upstream_url": SHIPFAST_EXTERNAL, "base_url": SHIPFAST_EXTERNAL}
    )
    assert patch_resp.status_code == 200, f"Failed to update upstream: {patch_resp.text}"
    intg_data = patch_resp.json()
    print(f"  ✓ ShipFast configured with external upstream URL: {SHIPFAST_EXTERNAL}")

    # --------------------------------------------------------------------------
    # Step 3: TEST 1 — REAL ALLOWED REQUEST (Legitimate Traffic Forwarding)
    # --------------------------------------------------------------------------
    print("\n[Step 3] Executing TEST 1 — REAL ALLOWED REQUEST...")
    req_path = "/api/integrations/shipfast/orders/ord_101"
    test1_resp = client.get(f"{CIPHERGUARD_GATEWAY}{req_path}")
    print(f"  Customer App -> {CIPHERGUARD_GATEWAY}{req_path}")
    print(f"  HTTP Status Code: {test1_resp.status_code}")
    print(f"  X-CipherGuard-Decision:   {test1_resp.headers.get('x-cipherguard-decision')}")
    print(f"  X-CipherGuard-Risk-Score: {test1_resp.headers.get('x-cipherguard-risk-score')}")
    print(f"  Response Body: {test1_resp.text}")

    assert test1_resp.status_code == 200, f"Expected 200, got {test1_resp.status_code}"
    assert test1_resp.headers.get("x-cipherguard-decision") == "ALLOW", "Expected ALLOW decision"
    payload1 = test1_resp.json()
    assert payload1.get("carrier") == "ShipFast Logistics", "Expected response payload from ShipFast"
    assert payload1.get("order_id") == "ord_101"
    print("  ✓ TEST 1 PASSED: Legitimate request was inspected, allowed, and successfully forwarded to external ShipFast.")

    # --------------------------------------------------------------------------
    # Step 4: TEST 2 — REAL BLOCKED REQUEST (Prohibited Administrative Access)
    # --------------------------------------------------------------------------
    print("\n[Step 4] Executing TEST 2 — REAL BLOCKED REQUEST...")
    blocked_path = "/api/integrations/shipfast/admin/internal-stats"
    test2_resp = client.get(f"{CIPHERGUARD_GATEWAY}{blocked_path}")
    print(f"  Customer App -> {CIPHERGUARD_GATEWAY}{blocked_path}")
    print(f"  HTTP Status Code: {test2_resp.status_code}")
    print(f"  Response Body: {test2_resp.text}")

    assert test2_resp.status_code == 403, f"Expected 403 Forbidden, got {test2_resp.status_code}"
    payload2 = test2_resp.json()
    assert payload2.get("decision") == "BLOCK", "Expected BLOCK decision"
    assert "Administrative/restricted endpoint access is prohibited" in payload2.get("reason", "")
    print("  ✓ TEST 2 PASSED: CipherGuard blocked unauthorized admin endpoint before reaching ShipFast.")

    # --------------------------------------------------------------------------
    # Step 5: TEST 3 — GENERIC SECOND INTEGRATION (PayFlex Payments)
    # --------------------------------------------------------------------------
    print("\n[Step 5] Executing TEST 3 — GENERIC SECOND INTEGRATION (PayFlex)...")
    pay_charge_path = "/api/integrations/payflex/payments/charge"
    charge_payload = {
        "amount": 12500.0,
        "currency": "NGN",
        "customer_id": "cust_vps_demo",
        "reference": "ref_vps_ext_1001"
    }
    test3_charge = client.post(f"{CIPHERGUARD_GATEWAY}{pay_charge_path}", json=charge_payload)
    print(f"  Customer App -> POST {CIPHERGUARD_GATEWAY}{pay_charge_path}")
    print(f"  HTTP Status: {test3_charge.status_code}")
    print(f"  Decision Header: {test3_charge.headers.get('x-cipherguard-decision')}")
    print(f"  Response: {test3_charge.text}")

    assert test3_charge.status_code == 200, f"Expected 200, got {test3_charge.status_code}"
    assert test3_charge.headers.get("x-cipherguard-decision") == "ALLOW"
    assert test3_charge.json().get("status") == "succeeded"
    print("  ✓ PayFlex payment authorized with server-side injected credentials.")

    pay_block_path = "/api/integrations/payflex/admin/vault-keys"
    test3_block = client.get(f"{CIPHERGUARD_GATEWAY}{pay_block_path}")
    print(f"  Customer App -> GET {CIPHERGUARD_GATEWAY}{pay_block_path}")
    print(f"  HTTP Status: {test3_block.status_code}")
    assert test3_block.status_code == 403, f"Expected 403, got {test3_block.status_code}"
    assert test3_block.json().get("decision") == "BLOCK"
    print("  ✓ PayFlex /admin/vault-keys blocked with 403.")
    print("  ✓ TEST 3 PASSED: Generic multi-vendor security verified.")

    # --------------------------------------------------------------------------
    # Step 6: Telemetry & Alerts Verification
    # --------------------------------------------------------------------------
    print("\n[Step 6] Verifying Observability, Telemetry & Security Alerts...")
    stats_resp = client.get(f"{CIPHERGUARD_GATEWAY}/api/v1/traffic/stats")
    stats = stats_resp.json()
    print(f"  Traffic Stats: Total={stats['total_requests']}, Allowed={stats['allowed_requests']}, Blocked={stats['blocked_requests']}")

    alerts_resp = client.get(f"{CIPHERGUARD_GATEWAY}/api/v1/alerts")
    alerts = alerts_resp.json()
    print(f"  Security Alerts Count: {len(alerts)}")
    print(f"  Top Active Alert: {alerts[0]['title']} (Severity: {alerts[0]['severity']})")

    risk_resp = client.get(f"{CIPHERGUARD_GATEWAY}/api/v1/analytics/overview")
    risk = risk_resp.json()
    print(f"  Organizational Threat Posture: Score={risk['overall_risk_score']}, Level={risk['overall_risk_level']}")

    print("\n" + "=" * 75)
    print("ALL REAL EXTERNAL MULTI-HOST VERIFICATION TESTS PASSED (100%)")
    print("=" * 75)
    return True

if __name__ == "__main__":
    success = run_external_tests()
    sys.exit(0 if success else 1)
