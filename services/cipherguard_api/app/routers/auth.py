from fastapi import APIRouter, Depends, status
from app.core.auth import get_current_user, AuthenticatedUser
from app.models.schemas import APIResponse, UserProfileResponse

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])

@router.get("/me", response_model=APIResponse)
def get_user_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Returns the verified identity, role, and organization context derived from the Supabase token.
    """
    return APIResponse(
        status="success",
        message="Authenticated identity verified.",
        data=current_user.to_dict()
    )
