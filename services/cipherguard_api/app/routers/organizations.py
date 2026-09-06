from fastapi import APIRouter, Depends, HTTPException, status
from app.core.auth import get_current_user, AuthenticatedUser
from app.db.client import db_get_organization
from app.models.schemas import APIResponse

router = APIRouter(prefix="/organizations", tags=["Organizations & Multi-Tenancy"])

@router.get("/current", response_model=APIResponse)
def get_current_organization(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Returns the organization details for the authenticated user context.
    """
    org = db_get_organization(current_user.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )
    return APIResponse(
        status="success",
        data=org
    )
