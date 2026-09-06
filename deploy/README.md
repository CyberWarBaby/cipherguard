# CipherGuard — Independent Multi-VPS Deployment Guide

> **NITDA/ICSC Track G:** *"Watching What Third Party Integrations Really Do."*  
> This directory provides standalone deployment packages to run CipherGuard and Third-Party Partner APIs on completely independent virtual private servers (VPS).

---

## Architecture Topology

```
VPS A (CipherGuard Host)                     VPS B (Third-Party Carrier Host)
IP: http://<VPS_A_PUBLIC_IP>:8000            IP: http://<VPS_B_PUBLIC_IP>:8002
┌──────────────────────────────────────┐     ┌──────────────────────────────────┐
│  Kong Gateway (:8000)                │     │  ShipFast Logistics API (:8002)  │
│  └── CipherGuard Security (:8001)    │────►│  (Completely independent API)    │
└──────────────────────────────────────┘     └──────────────────────────────────┘
```

---

## 1. Deploying VPS B (ShipFast Simulated Partner API)

1. On your VPS B virtual machine:
   ```bash
   git clone <REPO_URL> cipher-guard
   cd cipher-guard/deploy/vps-b-shipfast
   ```
2. Launch the independent ShipFast container:
   ```bash
   docker compose up --build -d
   ```
3. Verify ShipFast is responding on VPS B:
   ```bash
   curl -i http://localhost:8002/health
   # From your laptop / external network:
   curl -i http://<VPS_B_PUBLIC_IP>:8002/health
   ```
   *Response:*
   ```json
   {"status":"healthy","service":"shipfast-api","version":"1.0.0"}
   ```

---

## 2. Deploying VPS A (CipherGuard Gateway & Security Layer)

1. On your VPS A virtual machine:
   ```bash
   git clone <REPO_URL> cipher-guard
   cd cipher-guard/deploy/vps-a-cipherguard
   cp .env.example .env
   ```
2. Edit `.env` with VPS B's public IP address:
   ```ini
   CIPHERGUARD_GATEWAY_URL=http://<VPS_A_PUBLIC_IP>:8000
   SHIPFAST_UPSTREAM_URL=http://<VPS_B_PUBLIC_IP>:8002
   ALLOW_INTERNAL_NETWORKS=false
   ```
3. Launch the CipherGuard stack:
   ```bash
   docker compose up --build -d
   ```
4. Verify Kong Gateway is healthy:
   ```bash
   curl -i http://<VPS_A_PUBLIC_IP>:8000/health
   ```

---

## 3. End-to-End Test Execution (Across Public IPs)

From the API Playground, Frontend, or an external machine:

### TEST 1 — Real Allowed Request
```bash
curl -i http://<VPS_A_PUBLIC_IP>:8000/api/integrations/shipfast/orders/ord_101
```
- **Flow:** Client -> VPS A (:8000) -> CipherGuard (:8001) -> Policy Engine (ALLOW) -> VPS B (:8002) -> Response.
- **Header:** `X-CipherGuard-Decision: ALLOW`.
- **Response:** ShipFast order data returned. VPS B server logs show the request arrived.

### TEST 2 — Real Blocked Request
```bash
curl -i http://<VPS_A_PUBLIC_IP>:8000/api/integrations/shipfast/admin/internal-stats
```
- **Flow:** Client -> VPS A (:8000) -> CipherGuard (:8001) -> Policy Engine (BLOCK) -> Returns `403 Forbidden`.
- **Security Action:** VPS B receives **0 requests**. CipherGuard generates a critical security alert.
