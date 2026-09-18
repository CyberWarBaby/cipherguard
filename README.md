# CipherGuard — Generic API Security Gateway for Third-Party Integrations

> **Challenge:** NITDA/ICSC Track G — *"Commerce, Supply Chain & Consumer Protection: Watching What Third Party Integrations Really Do."*  
> **Overview:** Generic API security, visibility, monitoring, and policy enforcement gateway that sits between customer business applications and third-party partner APIs (logistics, payments, messaging, identity, AI).

---

## 1. Core Architecture

In modern commerce and supply chain systems, business backends communicate with numerous external third-party APIs using trusted credentials. If an integration credential or application route is compromised, malicious operations can be executed against those third-party providers.

CipherGuard acts as an **inline security and monitoring gateway** protecting that boundary. The customer application points to CipherGuard's protected integration endpoint:

```
Customer Application / API Playground / Business Backend
        │
        ▼ (Public Gateway: http://<GATEWAY_HOST>:8000)
┌────────────────────────────────────────────────────────┐
│  Kong API Gateway (:8000)                              │
│  - Generic Public Reverse Proxy                        │
│  - /api/v1/*              ──> CipherGuard Management   │
│  - /api/integrations/*    ──> Protected Inline Gateway │
│  - /api/proxy/*           ──> Generic Proxy Gateway    │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (Inline Security Inspection & Policy)
┌────────────────────────────────────────────────────────┐
│  CipherGuard Security Engine (:8001)                   │
│  1. Identify Integration (UUID or slug) from route     │
│  2. Load Configured Upstream URL (configurable env/DB) │
│  3. Deep Request Inspection (Method, Path, Query, Body)│
│  4. Evaluate Active Policies & Threat Detector (SQLi,  │
│     Path Traversal, Malformed Payloads)                │
│  5. Calculate Dynamic Risk Score & Record Telemetry    │
│  6. Decision:                                          │
│     ├── BLOCK ──► Return 403 Forbidden (Upstream is    │
│     │             NEVER called; Security Alert logged) │
│     └── ALLOW ──► Inject Configured Upstream Auth      │
│                   (API Key, Bearer, Basic Auth)        │
│                   Forward to Configured Upstream URL   │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (HTTP to External or Internal Upstream)
┌────────────────────────────────────────────────────────┐
│  Configured Upstream Third-Party APIs (Separate VPS)   │
│  - ShipFast Logistics (Simulated Third-Party Carrier)  │
│  - PayFlex Payments   (Simulated Third-Party Fintech)  │
│  - Stripe / Twilio / Custom Enterprise REST Partners   │
└────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Vendor Generality (No Vendor Hardcoding)

CipherGuard is **100% vendor-agnostic**. Neither Kong nor CipherGuard has hardcoded vendor routes or vendor-specific security rules:

1. **ShipFast Logistics (`shipfast`)**: Simulated delivery carrier (`GET /orders/*`, `POST /orders`, restricted `GET /admin/internal-stats`).
2. **PayFlex Payments (`payflex`)**: Simulated payment gateway (`POST /payments/charge`, `GET /payments/*`, restricted `GET /admin/vault-keys`).

Both integrations flow through the exact same protected base path pattern:
- `http://localhost:8000/api/integrations/shipfast/*`
- `http://localhost:8000/api/integrations/payflex/*`
- `http://localhost:8000/api/integrations/<any_custom_integration_id>/*`

---

## 3. Directory Structure

```
cipher-guard/
├── .env.example                     # Environment template (Supabase, Upstream URLs, CORS)
├── .gitignore                       # Protects secrets, logs, and artifacts
├── README.md                        # Master production documentation
├── docker-compose.yml               # Multi-container orchestration with health checks & volumes
├── docs/
│   └── API.md                       # Comprehensive Frontend API Contract & VPS Guide
├── gateway/
│   └── kong.yml                     # Unified Kong generic declarative routing, CORS & rate-limiting
├── supabase/
│   └── schema.sql                   # Supabase PostgreSQL schema with generic integrations & policies
├── services/
│   ├── shipfast_api/                # Simulated third-party logistics carrier
│   │   ├── Dockerfile
│   │   ├── main.py                  # Endpoints: /orders, /customers, /admin/internal-stats
│   │   └── requirements.txt
│   ├── payflex_api/                 # Simulated third-party payments provider (Generality Proof)
│   │   ├── Dockerfile
│   │   ├── main.py                  # Endpoints: /payments/charge, /payments/{id}, /admin/vault-keys
│   │   └── requirements.txt
│   └── cipherguard_api/             # CipherGuard core security & telemetry backend
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── app/
│       │   ├── main.py              # FastAPI app factory, middleware, router mounting
│       │   ├── config.py            # Environment settings (Upstreams, Supabase, JWT)
│       │   ├── core/
│       │   │   ├── policy_engine.py # Modular policy evaluation engine (ALLOW / BLOCK / FLAG)
│       │   │   ├── threat_detector.py # SQLi, path traversal, scanner signature detection
│       │   │   ├── analyzer.py      # Anomaly detection & multi-factor risk scoring
│       │   │   ├── security.py      # SSRF validation (blocks metadata/private IPs)
│       │   │   ├── auth.py          # JWT verification & RBAC authorization
│       │   │   └── rate_limit.py    # Sliding-window rate limiter
│       │   ├── models/schemas.py    # Pydantic schemas (Integration, Policy, Event, Alert)
│       │   ├── db/client.py         # Supabase client + In-memory fallback with seed
│       │   └── routers/             # Modular API endpoints
│       │       ├── proxy.py         # Inline security gateway & credential injection
│       │       ├── integrations.py  # Third-party inventory management + SSRF check
│       │       ├── policies.py      # Configurable policy CRUD
│       │       ├── traffic.py       # Live telemetry querying & statistics
│       │       ├── alerts.py        # Security alert triage & resolution
│       │       ├── analytics.py     # Executive risk posture overview
│       │       └── health.py        # /health, /ready, /live diagnostics
│       └── tests/
│           ├── test_cipherguard.py  # 19 automated pytest unit & integration tests
│           └── test_e2e_live.py     # Live E2E test script against Kong Gateway (:8000)
```

---

## 4. Quick Start & Local Verification

### 4.1 Prerequisites
- Docker & Docker Compose
- Python 3.11+ (optional, tests can run directly inside Docker)
- curl / Postman

### 4.2 Start the Stack
```bash
# Clone repository and copy environment configuration
cp .env.example .env

# Start all containers in detached mode
docker compose up --build -d
```

### 4.3 Verify Containers
```bash
docker compose ps
```
All 4 containers will report `(healthy)`:
- `cipherguard-kong` on port `8000` (public entrypoint)
- `cipherguard-api` on port `8003:8001`
- `shipfast-api` on port `8002:8000`
- `payflex-api` on port `8006:8000`

---

## 5. End-to-End Verification (Track G Scenarios)

### TEST A — ALLOW: Legitimate Logistics Request
```bash
curl -i http://localhost:8000/api/integrations/shipfast/orders/ord_101
```
- **Result:** `200 OK`
- **Headers:** `X-CipherGuard-Decision: ALLOW`, `X-CipherGuard-Risk-Score: 10`
- **Response:** ShipFast order tracking payload returned. Telemetry event recorded.

---

### TEST B — BLOCK: Restricted Administrative Access
```bash
curl -i http://localhost:8000/api/integrations/shipfast/admin/internal-stats
```
- **Result:** `403 Forbidden`
- **Headers:** `X-CipherGuard-Decision: BLOCK`, `X-CipherGuard-Risk-Score: 87`
- **Response:** Matched policy `ShipFast Strict Read Policy: Blocked pattern '/admin/*'`.
- **Proof:** ShipFast container logs show **ZERO** requests received. Critical security alert generated in CipherGuard.

---

### TEST C — GENERIC SECOND INTEGRATION: Payments (PayFlex)
```bash
# 1. Allowed payment charge with server-side API Key injection:
curl -i -X POST http://localhost:8000/api/integrations/payflex/payments/charge \
  -H "Content-Type: application/json" \
  -d '{"amount": 7500, "currency": "NGN", "customer_id": "cust_982"}'

# Result: 200 OK, X-CipherGuard-Decision: ALLOW, authorized_by: "Authenticated by CipherGuard injected key"

# 2. Blocked key vault access:
curl -i http://localhost:8000/api/integrations/payflex/admin/vault-keys

# Result: 403 Forbidden (Blocked by PayFlex Transaction Safety Policy)
```

---

### 5.4 Automated Test Suite
Run the automated test suite directly inside the Docker container:
```bash
docker compose exec cipherguard-api pytest tests/test_cipherguard.py -v
```
*(19 of 19 tests pass: 100%)*

Run the live E2E gateway verification script:
```bash
docker compose exec cipherguard-api python tests/test_e2e_live.py
```
*(All 6 live steps pass: 100%)*

---

## 6. Multi-VPS Deployment Model

In production, CipherGuard and third-party APIs can be hosted on separate servers or cloud providers:

- **VPS A (CipherGuard Gateway)**: Runs Kong (`:8000`) + CipherGuard API (`:8001`).
- **VPS B (Third-Party Carrier)**: Runs ShipFast API (`:8002`).
- **VPS C (Third-Party Fintech)**: Runs PayFlex API (`:8006`).

Configure `.env` on VPS A:
```ini
CIPHERGUARD_GATEWAY_URL=http://<VPS_A_PUBLIC_IP>:8000
SHIPFAST_UPSTREAM_URL=http://<VPS_B_PUBLIC_IP>:8002
PAYFLEX_UPSTREAM_URL=http://<VPS_C_PUBLIC_IP>:8006
ALLOW_INTERNAL_NETWORKS=false
```
All client traffic connects to `http://<VPS_A_PUBLIC_IP>:8000/api/integrations/<slug>/*`.
CipherGuard inspects and enforces policies, then securely forwards allowed requests across the public internet to VPS B or VPS C.
