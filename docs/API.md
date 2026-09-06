# CipherGuard API — Frontend Integration Contract & API Reference

> **Target Audience:** Frontend Engineering Team (Next.js / TypeScript / Tailwind CSS) & Deployment Engineers  
> **Challenge:** NITDA/ICSC Track G — *"Commerce, Supply Chain & Consumer Protection: Watching What Third Party Integrations Really Do."*  
> **Base Gateway URL:** `http://localhost:8000` (Production: `https://api.cipherguard.com` or `http://<CIPHERGUARD_VPS_IP>:8000`)

---

## 1. Core Architecture Overview

CipherGuard is a **generic security, visibility, monitoring, and policy enforcement gateway** for third-party integrations (logistics, payments, messaging, identity, AI).

The customer backend and frontend applications **NEVER communicate directly with third-party APIs**. Instead, they route their traffic through CipherGuard's protected integration endpoints:

```
Customer Application / API Playground / Frontend
        │
        ▼ (Single Host: http://localhost:8000)
┌────────────────────────────────────────────────────────┐
│  Kong API Gateway (:8000)                              │
│  - /api/v1/*              ──> CipherGuard Management   │
│  - /api/integrations/*    ──> Protected Inline Gateway │
│  - /api/proxy/*           ──> Generic Proxy Gateway    │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (Inspects, Evaluates, Guards)
┌────────────────────────────────────────────────────────┐
│  CipherGuard Security Engine (:8001)                   │
│  - Identifies integration by slug or UUID              │
│  - Deep inspection of method, path, headers, body      │
│  - Enforces active security policies & threat shield   │
│  - Calculates dynamic risk & generates real-time alerts│
│  - Injects configured upstream auth credentials        │
│  - Decisions:                                          │
│    ├── BLOCK ──► Returns 403 Forbidden (Upstream NOT   │
│    │             called; Security Alert logged)        │
│    └── ALLOW ──► Forwards to Configured Upstream API   │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (Configurable Upstream HTTP)
┌────────────────────────────────────────────────────────┐
│  Configured Upstream Services (Separate Hosts/VPS)     │
│  - ShipFast Logistics (Simulated Third-Party Carrier)  │
│  - PayFlex Payments   (Simulated Third-Party Fintech)  │
│  - Stripe / Twilio / Custom REST Partner APIs          │
└────────────────────────────────────────────────────────┘
```

---

## 2. Protected Integration Gateway (Traffic Flow)

When a third-party integration is registered, CipherGuard provides a **protected base path**:

`http://<GATEWAY_HOST>:8000/api/integrations/<integration_slug_or_id>`

### 2.1 Logistics Example (ShipFast)
- **Protected Base:** `/api/integrations/shipfast`
- **Track Order (ALLOW):**
  ```http
  GET /api/integrations/shipfast/orders/ord_101 HTTP/1.1
  Host: localhost:8000
  ```
  *Response (`200 OK`)*:
  ```json
  {
    "order_id": "ord_101",
    "status": "shipped",
    "carrier": "ShipFast Logistics",
    "tracking_number": "SF-NG-ORD_101",
    "estimated_delivery": "2026-09-05"
  }
  ```
- **Create Order (ALLOW):**
  ```http
  POST /api/integrations/shipfast/orders HTTP/1.1
  Host: localhost:8000
  Content-Type: application/json

  {"customer_id": "cust_101", "destination_city": "Abuja", "items_count": 2}
  ```

- **Restricted Administrative Access (BLOCK):**
  ```http
  GET /api/integrations/shipfast/admin/internal-stats HTTP/1.1
  Host: localhost:8000
  ```
  *Response (`403 Forbidden`)*:
  ```json
  {
    "status": "blocked",
    "decision": "BLOCK",
    "risk_score": 87,
    "matched_policies": ["ShipFast Strict Read Policy: Blocked pattern '/admin/*'"],
    "reason": "Administrative/restricted endpoint access is prohibited: '/admin/internal-stats' matches rule '/admin/*'",
    "integration": "shipfast",
    "endpoint": "/admin/internal-stats"
  }
  ```
  *(Note: ShipFast NEVER receives this request. CipherGuard records a critical security alert and updates the risk score)*.

---

### 2.2 Payments Example (PayFlex — Multi-Vendor Proof)
- **Protected Base:** `/api/integrations/payflex`
- **Charge Payment (ALLOW with Server-Side Injected API Key):**
  ```http
  POST /api/integrations/payflex/payments/charge HTTP/1.1
  Host: localhost:8000
  Content-Type: application/json

  {"amount": 7500.0, "currency": "NGN", "customer_id": "cust_982"}
  ```
  *Response (`200 OK`)*:
  ```json
  {
    "payment_id": "pay_1788645905",
    "amount": 7500.0,
    "currency": "NGN",
    "status": "succeeded",
    "authorized_by": "Authenticated by CipherGuard injected key"
  }
  ```
- **Restricted Key Vault (BLOCK):**
  ```http
  GET /api/integrations/payflex/admin/vault-keys HTTP/1.1
  Host: localhost:8000
  ```
  *Response (`403 Forbidden`)*: Blocked by PayFlex Transaction Safety Policy.

---

## 3. Authentication & Security Headers

### Management APIs
Include the standard JWT Bearer token on management routes (`/api/v1/*`):
```http
Authorization: Bearer <SUPABASE_JWT_ACCESS_TOKEN>
Content-Type: application/json
```
*(During local development, unauthenticated requests automatically resolve to the default SecOps organization `NITDA Defense Corp`)*.

### Response Headers Attached by CipherGuard
All responses returned by the protected gateway contain real-time security metadata:
- `X-CipherGuard-Decision`: `ALLOW`, `BLOCK`, or `FLAG`
- `X-CipherGuard-Risk-Score`: Calculated dynamic risk score (0–100)
- `X-Process-Time-Ms`: Security inspection and proxy turnaround latency in milliseconds

---

## 4. Management & Dashboard API Endpoints (`/api/v1/*`)

### 4.1 Authentication & Profile
- `GET /api/v1/auth/me`: Returns current user ID, email, role, and organization ID.
- `GET /api/v1/organizations/current`: Returns current organization metadata and subscription plan.

### 4.2 Third-Party Integrations Inventory
- `GET /api/v1/integrations`: Lists all registered integrations with risk scores and protected gateway endpoints. Internal Docker URLs and credentials are sanitized/omitted.
- `POST /api/v1/integrations`: Registers a new integration with SSRF protection.
  ```json
  {
    "name": "QuickDelivery Partner",
    "slug": "quickdelivery",
    "category": "Shipping",
    "upstream_url": "https://api.quickdelivery.example.com",
    "auth_type": "api_key",
    "auth_header_name": "X-API-Key",
    "auth_credential": "qd_secret_live_key",
    "status": "active",
    "description": "Logistics dispatch partner."
  }
  ```
- `GET /api/v1/integrations/{id_or_slug}`: Retrieves details for a specific integration.
- `PATCH /api/v1/integrations/{id_or_slug}`: Updates configuration, status (`active`, `monitoring`, `restricted`, `paused`), or risk baseline.
- `DELETE /api/v1/integrations/{id_or_slug}`: Removes an integration.

### 4.3 Security Policies
- `GET /api/v1/policies?integration_id={id}`: Lists active security policies.
- `POST /api/v1/policies`: Creates a new policy rule:
  ```json
  {
    "integration_id": "b0000000-0000-0000-0000-000000000001",
    "name": "Block Financial and Admin Endpoints",
    "allowed_methods": ["GET", "POST"],
    "allowed_endpoints": ["/orders/*", "/tracking/*"],
    "blocked_endpoints": ["/admin/*", "/billing/*", "/export/*"],
    "rate_limit_rpm": 120,
    "action_on_violation": "block"
  }
  ```
- `PATCH /api/v1/policies/{policy_id}`: Updates an existing policy.
- `DELETE /api/v1/policies/{policy_id}`: Deletes a policy.

### 4.4 Traffic Telemetry & Auditing
- `GET /api/v1/traffic`: Paginated list of recent traffic events passing through the gateway.
  - Query params: `decision` (`ALLOW`, `BLOCK`, `FLAG`), `is_violation`, `integration_name`, `page`, `limit`.
- `GET /api/v1/traffic/stats`: Aggregated traffic statistics:
  ```json
  {
    "total_requests": 142,
    "allowed_requests": 130,
    "blocked_requests": 12,
    "flagged_requests": 0,
    "avg_latency_ms": 28.5,
    "violations_count": 12,
    "top_blocked_endpoints": [
      {"endpoint": "/admin/internal-stats", "count": 8},
      {"endpoint": "/admin/vault-keys", "count": 4}
    ],
    "traffic_by_method": {"GET": 110, "POST": 32},
    "traffic_by_status": {"200": 130, "403": 12}
  }
  ```

### 4.5 Security Alerts
- `GET /api/v1/alerts`: Returns real-time security alerts triggered by policy violations or blocked requests.
  - Query params: `status` (`open`, `investigating`, `resolved`, `dismissed`), `severity` (`critical`, `high`, `medium`, `low`).
- `GET /api/v1/alerts/{alert_id}`: Alert details.
- `PATCH /api/v1/alerts/{alert_id}`: Triage or resolve an alert:
  ```json
  {
    "status": "resolved",
    "notes": "Verified client was automated pentest tool. Policy working as expected."
  }
  ```

### 4.6 Risk Overview & Executive Analytics
- `GET /api/v1/analytics/overview`: High-level security posture summary:
  ```json
  {
    "overall_risk_score": 24,
    "overall_risk_level": "low",
    "total_monitored_integrations": 3,
    "total_active_alerts": 2,
    "critical_alerts_count": 2,
    "total_observed_events_24h": 142,
    "violations_count_24h": 12,
    "integration_risk_breakdown": [
      {"slug": "shipfast", "risk_score": 25, "risk_level": "low"},
      {"slug": "payflex", "risk_score": 35, "risk_level": "medium"}
    ]
  }
  ```

---

## 5. Multi-VPS Deployment Guide

CipherGuard natively supports multi-host / multi-VPS deployment:

| System | Role | Components | Port |
| :--- | :--- | :--- | :--- |
| **VPS A** | **CipherGuard Gateway** | Kong Gateway + CipherGuard Security API | Public port `8000` |
| **VPS B** | **Third-Party API** | ShipFast Logistics Simulated API | Public port `8002` |
| **VPS C** (or external) | **Third-Party API** | PayFlex Payments / Real Provider | Public port `8006` |

### Configuring VPS A:
In `.env` on VPS A:
```ini
CIPHERGUARD_GATEWAY_URL=http://<VPS_A_PUBLIC_IP>:8000
SHIPFAST_UPSTREAM_URL=http://<VPS_B_PUBLIC_IP>:8002
PAYFLEX_UPSTREAM_URL=http://<VPS_C_PUBLIC_IP>:8006
ALLOW_INTERNAL_NETWORKS=false
```
Then start the stack:
```bash
docker compose up -d
```
All customer traffic connects to `http://<VPS_A_PUBLIC_IP>:8000/api/integrations/<integration_slug>/*`.
CipherGuard inspects and enforces policies, then securely forwards allowed requests across the public internet to VPS B or VPS C.
