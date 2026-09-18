import time
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import (
    health,
    auth,
    organizations,
    integrations,
    policies,
    events,
    alerts,
    analytics,
    scans,
    proxy,
    traffic
)

# Configure Root Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cipherguard.server")

def create_application() -> FastAPI:
    application = FastAPI(
        title="CipherGuard Security Gateway API",
        description="NITDA/ICSC Track G Challenge: Watching What Third Party Integrations Really Do. "
                    "Continuous observation, inline policy enforcement, threat shielding, and anomaly intelligence for enterprise third-party APIs.",
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # 1. Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Security Headers & Observability Middleware
    @application.middleware("http")
    async def security_and_timing_middleware(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time_ms = int((time.time() - start_time) * 1000)

        # Attach Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)
        return response

    # 3. Global Exception Handlers
    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "status_code": exc.status_code,
                "message": exc.detail,
                "path": request.url.path
            }
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "status_code": 422,
                "message": "Input validation error",
                "errors": exc.errors(),
                "path": request.url.path
            }
        )

    @application.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server exception on {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "status_code": 500,
                "message": "An internal server error occurred.",
                "path": request.url.path
            }
        )

    # 4. Register Routers
    # Base health probes
    application.include_router(health.router)
    
    # API v1 Prefix Registration (e.g., /api/v1/integrations)
    v1_prefix = settings.API_V1_PREFIX
    application.include_router(health.router, prefix=v1_prefix)
    application.include_router(auth.router, prefix=v1_prefix)
    application.include_router(organizations.router, prefix=v1_prefix)
    application.include_router(integrations.router, prefix=v1_prefix)
    application.include_router(policies.router, prefix=v1_prefix)
    application.include_router(alerts.router, prefix=v1_prefix)
    application.include_router(analytics.router, prefix=v1_prefix)
    application.include_router(scans.router, prefix=v1_prefix)
    application.include_router(traffic.router, prefix=v1_prefix)

    # Root Level Registration (supports stripped gateway routes e.g., /api/cipherguard/integrations -> /integrations)
    application.include_router(auth.router)
    application.include_router(organizations.router)
    application.include_router(integrations.router)
    application.include_router(policies.router)
    application.include_router(alerts.router)
    application.include_router(analytics.router)
    application.include_router(scans.router)
    application.include_router(traffic.router)
    
    # Telemetry and Event Ingestion
    application.include_router(events.router)

    # Core Security Proxy Engine (intercepts and guards third-party traffic)
    application.include_router(proxy.router)

    return application

app = create_application()
