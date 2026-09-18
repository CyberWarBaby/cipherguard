import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "CipherGuard API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip()
    SUPABASE_KEY: str = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    
    # CORS Configuration
    ALLOWED_ORIGINS_RAW: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"
    )
    
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]

    # Rate Limiting
    DEFAULT_RATE_LIMIT_RPM: int = int(os.getenv("DEFAULT_RATE_LIMIT_RPM", "120"))
    
    # Default Tenant
    DEFAULT_ORG_ID: str = os.getenv("DEFAULT_ORG_ID", "a0000000-0000-0000-0000-000000000001")

    # Gateway & Upstream Integration Endpoints (Configurable for multi-host / VPS deployments)
    CIPHERGUARD_GATEWAY_URL: str = os.getenv("CIPHERGUARD_GATEWAY_URL", "http://localhost:8000").rstrip("/")
    SHIPFAST_UPSTREAM_URL: str = os.getenv("SHIPFAST_UPSTREAM_URL", "http://shipfast-api:8000").rstrip("/")
    PAYFLEX_UPSTREAM_URL: str = os.getenv("PAYFLEX_UPSTREAM_URL", "http://payflex-api:8000").rstrip("/")
    
    # SSRF Protection Controls
    ALLOW_INTERNAL_NETWORKS: bool = os.getenv("ALLOW_INTERNAL_NETWORKS", "true").lower() in ("true", "1", "yes")

settings = Settings()

