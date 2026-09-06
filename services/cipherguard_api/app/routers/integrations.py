from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.auth import get_current_user, require_role, AuthenticatedUser
from app.models.schemas import (
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationResponse,
    APIResponse
)
from app.db.client import (
    db_list_integrations,
    db_get_integration_by_slug_or_id,
    db_create_integration,
    db_update_integration,
    db_delete_integration
)

router = APIRouter(prefix="/integrations", tags=["Third-Party Integrations"])

from app.core.security import validate_target_url

@router.get("", response_model=List[IntegrationResponse])
def list_integrations(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Lists all registered third-party integrations with real-time risk scores and gateway endpoints.
    Internal Docker hostnames and credentials are securely masked/omitted in the response.
    """
    return db_list_integrations(current_user.organization_id, sanitize_internal_urls=True)

@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
def create_integration(
    payload: IntegrationCreate,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "security_analyst"]))
):
    """
    Registers a new third-party integration under CipherGuard monitoring.
    Validates upstream target URL against SSRF threats.
    """
    target_url = payload.upstream_url or payload.base_url
    if target_url:
        validate_target_url(target_url)

    existing = db_get_integration_by_slug_or_id(current_user.organization_id, payload.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An integration with slug '{payload.slug}' already exists in your organization."
        )

    data = payload.model_dump()
    created = db_create_integration(current_user.organization_id, data)
    
    resp_copy = dict(created)
    resp_copy["has_auth_credential"] = bool(created.get("auth_credential"))
    resp_copy.pop("auth_credential", None)
    resp_copy["gateway_url"] = f"/api/integrations/{resp_copy.get('slug')}"
    resp_copy["protected_endpoint"] = f"/api/integrations/{resp_copy.get('slug')}"
    return resp_copy

@router.get("/{id_or_slug}", response_model=IntegrationResponse)
def get_integration(
    id_or_slug: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Fetches details and real-time risk profile for a specific third-party integration.
    """
    integration = db_get_integration_by_slug_or_id(current_user.organization_id, id_or_slug)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{id_or_slug}' not found."
        )
    
    intg_copy = dict(integration)
    intg_copy["has_auth_credential"] = bool(intg_copy.get("auth_credential"))
    intg_copy.pop("auth_credential", None)
    intg_copy["gateway_url"] = f"/api/integrations/{intg_copy.get('slug')}"
    intg_copy["protected_endpoint"] = f"/api/integrations/{intg_copy.get('slug')}"

    upstream = intg_copy.get("upstream_url") or intg_copy.get("base_url")
    if "api:" in str(upstream) or "docker" in str(upstream):
        intg_copy["base_url"] = f"https://api.{intg_copy.get('slug')}.example"
        intg_copy["upstream_url"] = f"https://api.{intg_copy.get('slug')}.example"

    return intg_copy

@router.patch("/{id_or_slug}", response_model=IntegrationResponse)
def update_integration(
    id_or_slug: str,
    payload: IntegrationUpdate,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "security_analyst"]))
):
    """
    Updates configuration, status (e.g. active, monitoring, restricted, paused), or risk baseline.
    """
    target_url = payload.upstream_url or payload.base_url
    if target_url:
        validate_target_url(target_url)

    integration = db_get_integration_by_slug_or_id(current_user.organization_id, id_or_slug)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{id_or_slug}' not found."
        )

    updated = db_update_integration(
        current_user.organization_id,
        integration["id"],
        payload.model_dump(exclude_unset=True)
    )
    resp_copy = dict(updated)
    resp_copy["has_auth_credential"] = bool(updated.get("auth_credential"))
    resp_copy.pop("auth_credential", None)
    resp_copy["gateway_url"] = f"/api/integrations/{resp_copy.get('slug')}"
    resp_copy["protected_endpoint"] = f"/api/integrations/{resp_copy.get('slug')}"
    return resp_copy


@router.delete("/{id_or_slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(
    id_or_slug: str,
    current_user: AuthenticatedUser = Depends(require_role(["admin"]))
):
    """
    Removes a third-party integration from monitoring.
    """
    integration = db_get_integration_by_slug_or_id(current_user.organization_id, id_or_slug)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{id_or_slug}' not found."
        )

    success = db_delete_integration(current_user.organization_id, integration["id"])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete integration.")
    return None
