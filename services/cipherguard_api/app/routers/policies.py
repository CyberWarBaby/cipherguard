from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from app.core.auth import get_current_user, require_role, AuthenticatedUser
from app.models.schemas import PolicyCreate, PolicyResponse
from app.db.client import (
    db_list_policies,
    db_create_policy,
    db_delete_policy,
    db_get_integration_by_slug_or_id
)

router = APIRouter(prefix="/policies", tags=["Integration Policies"])

@router.get("", response_model=List[PolicyResponse])
def list_policies(
    integration_id: Optional[str] = Query(None, description="Filter by integration ID"),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Lists security and traffic policies defined for integrations.
    """
    return db_list_policies(current_user.organization_id, integration_id=integration_id)

@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "security_analyst"]))
):
    """
    Defines a new traffic contract, method whitelist, or endpoint blocklist policy.
    """
    # Verify integration belongs to user's organization
    intg = db_get_integration_by_slug_or_id(current_user.organization_id, payload.integration_id)
    if not intg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced integration not found in your organization."
        )

    return db_create_policy(current_user.organization_id, payload.model_dump())

@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: str,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "security_analyst"]))
):
    """
    Deletes an existing policy.
    """
    success = db_delete_policy(current_user.organization_id, policy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Policy not found.")
    return None
