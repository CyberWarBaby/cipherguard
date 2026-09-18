from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone

# ------------------------------------------------------------------------------
# Common Schemas
# ------------------------------------------------------------------------------
class APIResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[Any] = None

class PaginatedResponse(BaseModel):
    status: str = "success"
    total: int
    page: int
    limit: int
    data: List[Any]

# ------------------------------------------------------------------------------
# Organizations & Users
# ------------------------------------------------------------------------------
class OrganizationBase(BaseModel):
    name: str = Field(..., max_length=255, example="NITDA Defense Corp")
    slug: str = Field(..., max_length=100, example="nitda-defense")
    plan: str = Field(default="enterprise", max_length=50)

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationResponse(OrganizationBase):
    id: str
    created_at: datetime
    updated_at: datetime

class UserProfileResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    full_name: Optional[str] = None
    role: str = "security_analyst"
    is_active: bool = True
    created_at: datetime

# ------------------------------------------------------------------------------
# Third-Party Integrations
# ------------------------------------------------------------------------------
class IntegrationBase(BaseModel):
    name: str = Field(..., max_length=100, example="ShipFast Logistics")
    slug: str = Field(..., max_length=100, example="shipfast")
    category: Literal["Shipping", "Payments", "Messaging", "AI", "Analytics", "Authentication", "Cloud", "Other"] = "Shipping"
    upstream_url: Optional[str] = Field(None, example="https://api.shipfast.example")
    base_url: Optional[str] = Field(None, example="https://api.shipfast.example")
    auth_type: Literal["none", "api_key", "bearer_token", "basic_auth"] = "none"
    auth_header_name: Optional[str] = Field("Authorization", example="X-API-Key")
    status: Literal["active", "monitoring", "restricted", "paused"] = "monitoring"
    description: Optional[str] = Field(None, example="Third-party logistics & package tracking API.")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class IntegrationCreate(IntegrationBase):
    auth_credential: Optional[str] = Field(None, description="Secure upstream credential stored server-side only; never returned in API responses")
    risk_score: Optional[int] = Field(default=15, ge=0, le=100)

class IntegrationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    category: Optional[Literal["Shipping", "Payments", "Messaging", "AI", "Analytics", "Authentication", "Cloud", "Other"]] = None
    upstream_url: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: Optional[Literal["none", "api_key", "bearer_token", "basic_auth"]] = None
    auth_header_name: Optional[str] = None
    auth_credential: Optional[str] = None
    status: Optional[Literal["active", "monitoring", "restricted", "paused"]] = None
    description: Optional[str] = None
    risk_score: Optional[int] = Field(None, ge=0, le=100)
    metadata: Optional[Dict[str, Any]] = None

class IntegrationResponse(IntegrationBase):
    id: str
    organization_id: str
    gateway_url: str = Field(..., example="/api/integrations/shipfast")
    protected_endpoint: str = Field(..., example="/api/integrations/shipfast")
    provider: str = Field(default="Custom Provider")
    risk_score: int
    risk_level: str
    has_auth_credential: bool = False
    observed_endpoints_count: int = 0
    last_activity_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # Note: internal container hostnames and sensitive auth credentials are strictly sanitized/omitted


# ------------------------------------------------------------------------------
# Security Decisions & Inspection
# ------------------------------------------------------------------------------
class SecurityDecision(BaseModel):
    decision: Literal["ALLOW", "BLOCK", "FLAG"]
    risk_score: int
    matched_policies: List[str] = Field(default_factory=list)
    reason: str
    threat_classification: Optional[str] = None

# ------------------------------------------------------------------------------
# Policies
# ------------------------------------------------------------------------------
class PolicyBase(BaseModel):
    name: str = Field(..., max_length=255, example="ShipFast Strict Read Policy")
    description: Optional[str] = Field(None, example="Restricts integration to read-only orders.")
    allowed_methods: List[str] = Field(default_factory=lambda: ["GET"])
    allowed_endpoints: List[str] = Field(default_factory=lambda: ["/*"])
    blocked_endpoints: List[str] = Field(default_factory=list)
    rate_limit_rpm: int = Field(default=120, ge=1, le=10000)
    is_active: bool = True
    action_on_violation: Literal["alert", "block", "log"] = "alert"

class PolicyCreate(PolicyBase):
    integration_id: str

class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    allowed_methods: Optional[List[str]] = None
    allowed_endpoints: Optional[List[str]] = None
    blocked_endpoints: Optional[List[str]] = None
    rate_limit_rpm: Optional[int] = None
    is_active: Optional[bool] = None
    action_on_violation: Optional[Literal["alert", "block", "log"]] = None

class PolicyResponse(PolicyBase):
    id: str
    organization_id: str
    integration_id: str
    created_at: datetime
    updated_at: datetime

# ------------------------------------------------------------------------------
# Events & Traffic Telemetry
# ------------------------------------------------------------------------------
class IntegrationEventCreate(BaseModel):
    integration_name: str = Field(..., max_length=100, example="shipfast")
    method: str = Field(..., max_length=10, example="GET")
    endpoint: str = Field(..., max_length=1000, example="/orders/123")
    action: Optional[str] = Field(None, max_length=100, example="read")
    resource: Optional[str] = Field(None, max_length=100, example="orders")
    status_code: int = Field(..., ge=100, le=599, example=200)
    latency_ms: Optional[int] = Field(default=45, ge=0)
    decision: Optional[Literal["ALLOW", "BLOCK", "FLAG"]] = "ALLOW"
    matched_policies: Optional[List[str]] = Field(default_factory=list)
    reason: Optional[str] = None
    threat_classification: Optional[str] = None
    client_ip: Optional[str] = None
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

class IntegrationEventResponse(BaseModel):
    id: str
    organization_id: Optional[str] = None
    integration_id: Optional[str] = None
    integration_name: str
    method: str
    endpoint: str
    action: Optional[str] = None
    resource: Optional[str] = None
    status_code: int
    latency_ms: int = 0
    decision: Literal["ALLOW", "BLOCK", "FLAG"] = "ALLOW"
    matched_policies: List[str] = Field(default_factory=list)
    reason: Optional[str] = None
    threat_classification: Optional[str] = None
    client_ip: Optional[str] = None
    risk_level: str = "low"
    risk_score: int = 0
    is_violation: bool = False
    timestamp: datetime
    created_at: datetime

class TrafficStatsResponse(BaseModel):
    total_requests: int
    allowed_requests: int
    blocked_requests: int
    flagged_requests: int
    avg_latency_ms: float
    violations_count: int
    top_blocked_endpoints: List[Dict[str, Any]]
    traffic_by_method: Dict[str, int]
    traffic_by_status: Dict[str, int]

# ------------------------------------------------------------------------------
# Alerts
# ------------------------------------------------------------------------------
class AlertUpdate(BaseModel):
    status: Literal["open", "investigating", "resolved", "dismissed"]
    notes: Optional[str] = None

class AlertResponse(BaseModel):
    id: str
    organization_id: str
    integration_id: Optional[str] = None
    integration_name: Optional[str] = None
    event_id: Optional[str] = None
    title: str
    description: str
    severity: Literal["low", "medium", "high", "critical"]
    category: str
    status: Literal["open", "investigating", "resolved", "dismissed"]
    rule_violated: Optional[str] = None
    remediation: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

# ------------------------------------------------------------------------------
# Analytics & Risk Overview
# ------------------------------------------------------------------------------
class RiskScoreOverview(BaseModel):
    overall_risk_score: int = Field(..., ge=0, le=100, example=28)
    overall_risk_level: Literal["low", "medium", "high", "critical"] = "low"
    total_monitored_integrations: int
    total_active_alerts: int
    critical_alerts_count: int
    total_observed_events_24h: int
    violations_count_24h: int
    integration_risk_breakdown: List[Dict[str, Any]]
    recent_activity_timeline: List[Dict[str, Any]]

# ------------------------------------------------------------------------------
# Scans & Integration Audits
# ------------------------------------------------------------------------------
class ScanCreate(BaseModel):
    target_name: str = Field(..., max_length=255, example="ShipFast Delivery OpenAPI Spec")
    target_url: str = Field(..., max_length=2048, example="http://shipfast-api:8000/openapi.json")
    integration_id: Optional[str] = None

class ScanResponse(BaseModel):
    id: str
    organization_id: str
    integration_id: Optional[str] = None
    target_name: str
    target_url: str
    status: Literal["pending", "running", "completed", "failed"]
    findings_count: int
    score: int
    summary: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
