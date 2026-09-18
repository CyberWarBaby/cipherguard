import time
import httpx
import logging
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from app.config import settings
from app.core.policy_engine import evaluate_request_policy
from app.db.client import (
    db_get_integration_by_slug_or_id,
    db_list_policies,
    db_record_event
)

logger = logging.getLogger("cipherguard.proxy")
router = APIRouter(tags=["Security Proxy & Enforcement"])

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length"
}

# ------------------------------------------------------------------------------
# Generic Protected Integration Gateway Routes
# Flow: Customer App -> Kong (:8000) -> CipherGuard (:8001) -> Configured Upstream API
# ------------------------------------------------------------------------------
@router.api_route("/api/integrations/{integration_slug}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@router.api_route("/api/integrations/{integration_slug}/{subpath:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@router.api_route("/api/proxy/{integration_slug}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@router.api_route("/api/proxy/{integration_slug}/{subpath:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@router.api_route("/proxy/{integration_slug}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@router.api_route("/proxy/{integration_slug}/{subpath:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@router.api_route("/api/v1/proxy/{integration_slug}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@router.api_route("/api/v1/proxy/{integration_slug}/{subpath:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy_integration_traffic(
    integration_slug: str,
    request: Request,
    subpath: str = ""
):
    """
    Core inline security layer: intercepts outbound requests to third-party integrations,
    runs deep inspection against active policies, and either ALLOWS (proxies) or BLOCKS.
    """
    start_time = time.time()
    method = request.method.upper()
    endpoint_path = "/" + subpath.strip("/")
    
    org_id = request.headers.get("X-Organization-Id") or settings.DEFAULT_ORG_ID
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Resolve Integration
    integration = db_get_integration_by_slug_or_id(org_id, integration_slug.lower())
    if not integration:
        logger.warning(f"Rejected proxy request: integration '{integration_slug}' not found.")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": "error",
                "status_code": 404,
                "message": f"Integration '{integration_slug}' is not registered under CipherGuard.",
                "path": request.url.path
            }
        )

    # 2. Extract Body & Query parameters safely
    body_bytes = await request.body()
    body_text = None
    if body_bytes:
        try:
            body_text = body_bytes.decode("utf-8", errors="replace")
        except Exception:
            body_text = None

    query_params = dict(request.query_params)
    clean_headers = {k.lower(): v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}

    # 3. Fetch Policies & Evaluate Request
    policies = db_list_policies(org_id, integration["id"])
    decision_result = evaluate_request_policy(
        integration=integration,
        policies=policies,
        method=method,
        path=endpoint_path,
        query_params=query_params,
        headers=clean_headers,
        body_text=body_text,
        client_ip=client_ip
    )

    # 4. Decision: BLOCK -> Return 403, Upstream is NEVER called!
    if decision_result.decision == "BLOCK":
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Record blocked event in telemetry
        db_record_event({
            "organization_id": org_id,
            "integration_id": integration["id"],
            "integration_name": integration_slug.lower(),
            "method": method,
            "endpoint": endpoint_path,
            "action": "blocked_request",
            "resource": endpoint_path.strip("/").split("/")[0] if endpoint_path.strip("/") else "root",
            "status_code": 403,
            "latency_ms": latency_ms,
            "decision": "BLOCK",
            "is_violation": True,
            "risk_level": decision_result.severity,
            "risk_score": decision_result.risk_score,
            "matched_policies": decision_result.matched_policies,
            "reason": decision_result.reason,
            "threat_classification": decision_result.threat_classification,
            "client_ip": client_ip
        })

        logger.warning(f"[CIPHERGUARD SECURITY BLOCKED] {integration_slug} {method} {endpoint_path} -> {decision_result.reason}")

        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": "blocked",
                "decision": "BLOCK",
                "risk_score": decision_result.risk_score,
                "matched_policies": decision_result.matched_policies,
                "reason": decision_result.reason,
                "integration": integration_slug.lower(),
                "endpoint": endpoint_path
            }
        )

    # 5. Decision: ALLOW (or FLAG) -> Securely forward to third-party upstream
    upstream_base = integration.get("upstream_url") or integration.get("base_url")
    if not upstream_base:
        logger.error(f"Rejected proxy request: integration '{integration_slug}' has no upstream URL configured.")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": "error",
                "status_code": 502,
                "message": f"Integration '{integration_slug}' has no configured upstream base URL.",
                "integration": integration_slug.lower(),
                "endpoint": endpoint_path
            }
        )

    target_url = f"{upstream_base.rstrip('/')}/{subpath.lstrip('/')}" if subpath else upstream_base.rstrip('/')

    # 5a. Extensible Upstream Authentication Injection (Server-side secret injection)
    auth_type = integration.get("auth_type", "none")
    auth_credential = integration.get("auth_credential")
    auth_header_name = (integration.get("auth_header_name") or "Authorization").strip()

    if auth_credential:
        if auth_type == "api_key":
            clean_headers[auth_header_name.lower()] = auth_credential
        elif auth_type == "bearer_token":
            clean_headers["authorization"] = f"Bearer {auth_credential}"
        elif auth_type == "basic_auth":
            import base64
            encoded = base64.b64encode(auth_credential.encode("utf-8")).decode("utf-8")
            clean_headers["authorization"] = f"Basic {encoded}"

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            upstream_response = await client.request(
                method=method,
                url=target_url,
                params=request.query_params,
                headers=clean_headers,
                content=body_bytes
            )


        latency_ms = int((time.time() - start_time) * 1000)

        # Record telemetry event
        db_record_event({
            "organization_id": org_id,
            "integration_id": integration["id"],
            "integration_name": integration_slug.lower(),
            "method": method,
            "endpoint": endpoint_path,
            "action": "proxy_request",
            "resource": endpoint_path.strip("/").split("/")[0] if endpoint_path.strip("/") else "root",
            "status_code": upstream_response.status_code,
            "latency_ms": latency_ms,
            "decision": decision_result.decision,
            "is_violation": (decision_result.decision == "FLAG" or upstream_response.status_code >= 500),
            "risk_level": decision_result.severity,
            "risk_score": decision_result.risk_score,
            "matched_policies": decision_result.matched_policies,
            "reason": decision_result.reason,
            "threat_classification": decision_result.threat_classification,
            "client_ip": client_ip
        })

        # Return upstream response to client
        fwd_headers = {
            k: v for k, v in upstream_response.headers.items()
            if k.lower() not in HOP_BY_HOP_HEADERS
        }
        fwd_headers["X-CipherGuard-Decision"] = decision_result.decision
        fwd_headers["X-CipherGuard-Risk-Score"] = str(decision_result.risk_score)

        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=fwd_headers,
            media_type=upstream_response.headers.get("content-type")
        )

    except httpx.RequestError as exc:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Upstream communication failed for {integration_slug}: {exc}")
        
        db_record_event({
            "organization_id": org_id,
            "integration_id": integration["id"],
            "integration_name": integration_slug.lower(),
            "method": method,
            "endpoint": endpoint_path,
            "action": "upstream_error",
            "resource": endpoint_path.strip("/").split("/")[0] if endpoint_path.strip("/") else "root",
            "status_code": 502,
            "latency_ms": latency_ms,
            "decision": "ALLOW",
            "is_violation": True,
            "risk_level": "medium",
            "risk_score": 45,
            "matched_policies": ["Upstream Connectivity Guard"],
            "reason": f"Third-party integration service unreachable: {str(exc)}",
            "threat_classification": "upstream_unreachable",
            "client_ip": client_ip
        })

        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": "error",
                "status_code": 502,
                "message": f"Unable to reach third-party upstream service for '{integration_slug}'.",
                "integration": integration_slug.lower(),
                "endpoint": endpoint_path
            }
        )
