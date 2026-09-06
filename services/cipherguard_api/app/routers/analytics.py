from fastapi import APIRouter, Depends
from app.core.auth import get_current_user, AuthenticatedUser
from app.models.schemas import RiskScoreOverview
from app.db.client import db_get_risk_overview

router = APIRouter(prefix="/analytics", tags=["Analytics & Risk Intelligence"])

@router.get("/overview", response_model=RiskScoreOverview)
def get_risk_overview(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Returns executive risk scoring, active alerts count, violation ratios, and telemetry activity.
    """
    return db_get_risk_overview(current_user.organization_id)
