import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from app.core.auth import get_current_user, AuthenticatedUser
from app.models.schemas import IntegrationEventCreate, IntegrationEventResponse, APIResponse
from app.db.client import db_record_event, db_list_events
from app.config import settings

logger = logging.getLogger("cipherguard.events")
router = APIRouter(tags=["Telemetry & Events"])

def infer_action(method: str, endpoint: str) -> str:
    m = method.upper()
    if m == "GET":
        return "read"
    elif m == "POST":
        return "create"
    elif m in ("PUT", "PATCH"):
        return "update"
    elif m == "DELETE":
        return "delete"
    return "execute"

def infer_resource(endpoint: str) -> str:
    parts = [p for p in endpoint.strip("/").split("/") if p]
    return parts[0] if parts else "root"

@router.post("/api/v1/events", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
@router.post("/api/events", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def ingest_event(
    event: IntegrationEventCreate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Ingests a structured integration event, evaluates security policies,
    and flags anomalies/violations in Supabase.
    """
    clean_endpoint = event.endpoint.strip()
    clean_method = event.method.upper().strip()
    
    event_dict = {
        "organization_id": current_user.organization_id,
        "integration_name": event.integration_name.lower().strip(),
        "method": clean_method,
        "endpoint": clean_endpoint,
        "action": event.action or infer_action(clean_method, clean_endpoint),
        "resource": event.resource or infer_resource(clean_endpoint),
        "status_code": event.status_code,
        "latency_ms": event.latency_ms or 45,
        "timestamp": event.timestamp.isoformat() if event.timestamp else datetime.now(timezone.utc).isoformat()
    }

    try:
        saved_record = db_record_event(event_dict)
        return APIResponse(
            status="success",
            message="Integration event ingested and evaluated.",
            data=saved_record
        )
    except Exception as e:
        logger.error(f"Failed to record event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record event: {str(e)}"
        )

@router.post("/api/events/kong-log", status_code=status.HTTP_200_OK)
async def ingest_kong_log(request: Request):
    """
    Webhook handler for Kong Gateway's http-log plugin.
    Automatically parses proxy telemetry and records integration activity in Supabase.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload from gateway")

    req_data = payload.get("request", {})
    resp_data = payload.get("response", {})
    service_data = payload.get("service", {})
    
    uri = req_data.get("uri", "/")
    method = req_data.get("method", "GET")
    status_code = resp_data.get("status", 200)
    service_name = service_data.get("name", "shipfast-service")

    integration_name = service_name.replace("-service", "").lower()
    
    # Strip route prefix if present
    endpoint = uri
    if endpoint.startswith(f"/api/{integration_name}"):
        endpoint = endpoint[len(f"/api/{integration_name}"):] or "/"
    elif endpoint.startswith(f"/{integration_name}"):
        endpoint = endpoint[len(f"/{integration_name}"):] or "/"

    started_at_epoch_ms = payload.get("started_at")
    if started_at_epoch_ms:
        timestamp_str = datetime.fromtimestamp(started_at_epoch_ms / 1000.0, tz=timezone.utc).isoformat()
    else:
        timestamp_str = datetime.now(timezone.utc).isoformat()

    latencies = payload.get("latencies", {})
    latency_ms = latencies.get("request", 45)

    event_payload = {
        "organization_id": settings.DEFAULT_ORG_ID,
        "integration_name": integration_name,
        "method": method.upper(),
        "endpoint": endpoint,
        "action": infer_action(method, endpoint),
        "resource": infer_resource(endpoint),
        "status_code": status_code,
        "latency_ms": latency_ms,
        "timestamp": timestamp_str
    }

    try:
        saved_record = db_record_event(event_payload)
        logger.info(f"Captured gateway telemetry: {integration_name} {method} {endpoint} -> {status_code}")
        return {"status": "success", "event_id": saved_record.get("id")}
    except Exception as e:
        logger.error(f"Error handling Kong log event: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/api/v1/events", response_model=List[IntegrationEventResponse])
@router.get("/api/events", response_model=List[Dict[str, Any]])
def list_recent_events(
    limit: int = Query(50, ge=1, le=500),
    integration_id: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Lists recent observed third-party integration telemetry events.
    """
    return db_list_events(current_user.organization_id, limit=limit, integration_id=integration_id)
