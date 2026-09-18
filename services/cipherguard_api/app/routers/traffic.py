from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional, Dict, Any
from app.core.auth import get_current_user, AuthenticatedUser
from app.models.schemas import IntegrationEventResponse, TrafficStatsResponse, APIResponse
from app.db.client import db_list_events, db_get_traffic_stats

router = APIRouter(prefix="/traffic", tags=["Traffic & Telemetry Intelligence"])

@router.get("", response_model=List[IntegrationEventResponse])
def get_traffic_log(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    integration_id: Optional[str] = Query(None, description="Filter by integration slug or ID"),
    decision: Optional[str] = Query(None, description="Filter by decision: ALLOW, BLOCK, or FLAG"),
    is_violation: Optional[bool] = Query(None, description="Filter by violation status"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    status_code: Optional[int] = Query(None, description="Filter by HTTP status code"),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieves real-time traffic audit logs with filtering by integration, decision, violation, or HTTP method.
    """
    return db_list_events(
        org_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        integration_id=integration_id,
        decision=decision,
        is_violation=is_violation,
        method=method,
        status_code=status_code
    )

@router.get("/stats", response_model=TrafficStatsResponse)
def get_traffic_statistics(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Returns aggregated traffic statistics including allowed vs. blocked requests,
    average latency, and top blocked endpoints.
    """
    return db_get_traffic_stats(current_user.organization_id)

@router.get("/{event_id}", response_model=IntegrationEventResponse)
def get_traffic_event(event_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Retrieves forensic details for a specific traffic or security event.
    """
    events = db_list_events(org_id=current_user.organization_id, limit=500)
    for e in events:
        if e.get("id") == event_id:
            return e
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Traffic event '{event_id}' not found.")
