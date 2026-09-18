from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from app.core.auth import get_current_user, require_role, AuthenticatedUser
from app.models.schemas import AlertResponse, AlertUpdate, APIResponse
from app.db.client import db_list_alerts, db_get_alert, db_update_alert_status

router = APIRouter(prefix="/alerts", tags=["Security Alerts"])

@router.get("", response_model=List[AlertResponse])
def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status (open, investigating, resolved, dismissed)"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    integration_id: Optional[str] = Query(None, description="Filter by integration ID or slug"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Lists security alerts and detected policy violations for the organization with filtering and pagination.
    """
    return db_list_alerts(
        org_id=current_user.organization_id,
        status_filter=status,
        severity_filter=severity,
        integration_id=integration_id,
        limit=limit,
        offset=offset
    )

@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert_detail(
    alert_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieves full incident details and remediation instructions for a specific alert.
    """
    alert = db_get_alert(current_user.organization_id, alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security alert '{alert_id}' not found."
        )
    return alert

@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert_status(
    alert_id: str,
    payload: AlertUpdate,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "security_analyst"]))
):
    """
    Updates the status of an alert (e.g. mark as investigating, resolved, or dismissed) with optional remediation notes.
    """
    updated = db_update_alert_status(
        org_id=current_user.organization_id,
        alert_id=alert_id,
        new_status=payload.status,
        notes=payload.notes
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found."
        )
    return updated
