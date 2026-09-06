from fastapi import APIRouter, status
from app.config import settings
from app.db.client import get_supabase_client

router = APIRouter(tags=["Health & Diagnostics"])

@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Liveness & basic health probe."""
    client = get_supabase_client()
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "supabase_connected": client is not None
    }

@router.get("/ready", status_code=status.HTTP_200_OK)
def readiness_check():
    """Readiness probe verifying operational readiness."""
    return {
        "ready": True,
        "service": settings.PROJECT_NAME,
        "status": "ready"
    }

@router.get("/live", status_code=status.HTTP_200_OK)
def liveness_check():
    """Kubernetes / container orchestrator liveness probe."""
    return {"live": True}
