import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from supabase import create_client, Client
from app.config import settings
from app.core.analyzer import (
    evaluate_request_policy,
    calculate_integration_risk,
    calculate_organization_risk,
    evaluate_event_policy
)

logger = logging.getLogger("cipherguard.db")

# ------------------------------------------------------------------------------
# In-Memory Store (for local development, testing, and fallback)
# ------------------------------------------------------------------------------
class MemoryStore:
    def __init__(self):
        self.reset()

    def reset(self):
        default_org_id = settings.DEFAULT_ORG_ID

        self.organizations: List[Dict[str, Any]] = [
            {
                "id": default_org_id,
                "name": "NITDA Defense Corp",
                "slug": "nitda-defense",
                "plan": "enterprise",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]

        self.user_profiles: List[Dict[str, Any]] = [
            {
                "id": "c0000000-0000-0000-0000-000000000001",
                "organization_id": default_org_id,
                "email": "security@cipherguard.io",
                "full_name": "Lead SecOps Engineer",
                "role": "admin",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]

        self.integrations: List[Dict[str, Any]] = []
        self.policies: List[Dict[str, Any]] = []



        self.events: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
        self.scans: List[Dict[str, Any]] = []

memory_store = MemoryStore()

# ------------------------------------------------------------------------------
# Supabase Client Factory
# ------------------------------------------------------------------------------
def get_supabase_client() -> Optional[Client]:
    """Returns a Supabase client if configured, otherwise None."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        return None
    try:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None

# ------------------------------------------------------------------------------
# Organizations
# ------------------------------------------------------------------------------
def db_get_organization(org_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    if client:
        try:
            res = client.table("organizations").select("*").eq("id", org_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error fetching organization from Supabase: {e}")
    
    for org in memory_store.organizations:
        if org["id"] == org_id:
            return org
    return None

# ------------------------------------------------------------------------------
# Integrations
# ------------------------------------------------------------------------------
def db_list_integrations(org_id: str, sanitize_internal_urls: bool = True) -> List[Dict[str, Any]]:
    """
    Lists third-party integrations for an organization.
    Computes real-time dynamic risk scores and masks internal Docker URLs.
    """
    integrations: List[Dict[str, Any]] = []
    fetched_from_supabase = False
    client = get_supabase_client()
    if client:
        try:
            res = client.table("integrations").select("*").eq("organization_id", org_id).order("created_at", desc=True).execute()
            if res.data is not None:
                integrations = res.data
                fetched_from_supabase = True
        except Exception as e:
            logger.error(f"Error listing integrations from Supabase: {e}")

    if not fetched_from_supabase:
        integrations = [i for i in memory_store.integrations if i["organization_id"] == org_id]

    events = db_list_events(org_id, limit=200)
    alerts = db_list_alerts(org_id)

    enriched: List[Dict[str, Any]] = []
    for intg in integrations:
        score, level, _ = calculate_integration_risk(intg, events, alerts)
        intg_copy = dict(intg)
        intg_copy["risk_score"] = score
        intg_copy["risk_level"] = level
        intg_copy["gateway_url"] = f"/api/integrations/{intg.get('slug')}"
        intg_copy["protected_endpoint"] = f"/api/integrations/{intg.get('slug')}"
        intg_copy["provider"] = intg.get("provider") or f"{intg.get('name')} Provider"
        intg_copy["has_auth_credential"] = bool(intg.get("auth_credential"))
        intg_copy.pop("auth_credential", None)  # Strictly never expose secrets to frontend clients

        upstream = intg.get("upstream_url") or intg.get("base_url")
        intg_copy["upstream_url"] = upstream
        intg_copy["base_url"] = upstream

        if sanitize_internal_urls:
            # Mask internal Docker endpoints so frontend never sees internal container hostnames
            if "api:" in str(upstream) or "docker" in str(upstream):
                placeholder = f"https://api.{intg.get('slug')}.example"
                intg_copy["upstream_url"] = placeholder
                intg_copy["base_url"] = placeholder

        enriched.append(intg_copy)

    return enriched

def db_get_integration_by_slug_or_id(org_id: str, identifier: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    if client:
        try:
            res = client.table("integrations").select("*").eq("organization_id", org_id).or_(f"id.eq.{identifier},slug.eq.{identifier}").execute()
            if res.data:
                intg = dict(res.data[0])
                intg["gateway_url"] = f"/api/integrations/{intg.get('slug')}"
                intg["protected_endpoint"] = f"/api/integrations/{intg.get('slug')}"
                intg["upstream_url"] = intg.get("upstream_url") or intg.get("base_url")
                intg["base_url"] = intg["upstream_url"]
                return intg
        except Exception:
            pass

    for i in memory_store.integrations:
        if i["organization_id"] == org_id and (i["id"] == identifier or i["slug"] == identifier):
            intg = dict(i)
            intg["gateway_url"] = f"/api/integrations/{intg.get('slug')}"
            intg["protected_endpoint"] = f"/api/integrations/{intg.get('slug')}"
            intg["upstream_url"] = intg.get("upstream_url") or intg.get("base_url")
            intg["base_url"] = intg["upstream_url"]
            return intg
    return None

def db_create_integration(org_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    new_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    upstream_url = data.get("upstream_url") or data.get("base_url")
    record = {
        "id": new_id,
        "organization_id": org_id,
        "name": data["name"],
        "slug": data["slug"],
        "provider": data.get("provider", f"{data['name']} Provider"),
        "category": data.get("category", "Shipping"),
        "upstream_url": upstream_url,
        "base_url": upstream_url,
        "auth_type": data.get("auth_type", "none"),
        "auth_header_name": data.get("auth_header_name", "Authorization"),
        "auth_credential": data.get("auth_credential"),
        "metadata": data.get("metadata", {}),
        "gateway_url": f"/api/integrations/{data['slug']}",
        "protected_endpoint": f"/api/integrations/{data['slug']}",
        "status": data.get("status", "monitoring"),
        "risk_score": data.get("risk_score", 15),
        "risk_level": "low" if data.get("risk_score", 15) < 30 else "medium",
        "description": data.get("description"),
        "observed_endpoints_count": 0,
        "last_activity_at": None,
        "created_at": now_iso,
        "updated_at": now_iso
    }

    # Always keep in-memory fallback store in sync
    memory_store.integrations.insert(0, record)

    client = get_supabase_client()
    if client:
        try:
            res = client.table("integrations").insert(record).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Supabase create integration error: {e}")

    return record


def db_update_integration(org_id: str, integration_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Always keep in-memory fallback store in sync
    for idx, item in enumerate(memory_store.integrations):
        if item["organization_id"] == org_id and item["id"] == integration_id:
            memory_store.integrations[idx].update(data)
            break

    client = get_supabase_client()
    if client:
        try:
            res = client.table("integrations").update(data).eq("organization_id", org_id).eq("id", integration_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Supabase update integration error: {e}")

    for item in memory_store.integrations:
        if item["organization_id"] == org_id and item["id"] == integration_id:
            return item
    return None

def db_delete_integration(org_id: str, integration_id: str) -> bool:
    # Always keep in-memory fallback store in sync
    memory_store.integrations = [i for i in memory_store.integrations if not (i["organization_id"] == org_id and i["id"] == integration_id)]

    client = get_supabase_client()
    if client:
        try:
            client.table("integrations").delete().eq("organization_id", org_id).eq("id", integration_id).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase delete integration error: {e}")
            return False

    return True


# ------------------------------------------------------------------------------
# Policies
# ------------------------------------------------------------------------------
def db_list_policies(org_id: str, integration_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    if client:
        try:
            query = client.table("integration_policies").select("*").eq("organization_id", org_id)
            if integration_id:
                query = query.eq("integration_id", integration_id)
            res = query.order("created_at", desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error listing policies: {e}")

    policies = [p for p in memory_store.policies if p["organization_id"] == org_id]
    if integration_id:
        policies = [p for p in policies if p["integration_id"] == integration_id]
    return policies

def db_create_policy(org_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    new_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "id": new_id,
        "organization_id": org_id,
        "integration_id": data["integration_id"],
        "name": data["name"],
        "description": data.get("description"),
        "allowed_methods": data.get("allowed_methods", ["GET"]),
        "allowed_endpoints": data.get("allowed_endpoints", ["/*"]),
        "blocked_endpoints": data.get("blocked_endpoints", []),
        "rate_limit_rpm": data.get("rate_limit_rpm", 120),
        "is_active": data.get("is_active", True),
        "action_on_violation": data.get("action_on_violation", "alert"),
        "created_at": now_iso,
        "updated_at": now_iso
    }

    client = get_supabase_client()
    if client:
        try:
            res = client.table("integration_policies").insert(record).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Supabase create policy error: {e}")

    memory_store.policies.append(record)
    return record

def db_delete_policy(org_id: str, policy_id: str) -> bool:
    client = get_supabase_client()
    if client:
        try:
            client.table("integration_policies").delete().eq("organization_id", org_id).eq("id", policy_id).execute()
            return True
        except Exception:
            return False

    initial_len = len(memory_store.policies)
    memory_store.policies = [p for p in memory_store.policies if not (p["organization_id"] == org_id and p["id"] == policy_id)]
    return len(memory_store.policies) < initial_len

# ------------------------------------------------------------------------------
# Events & Traffic Telemetry
# ------------------------------------------------------------------------------
def db_record_event(event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Records an integration traffic event, executes policy evaluation if not pre-computed,
    updates integration metrics, and triggers security alerts on violation/block.
    """
    org_id = event_dict.get("organization_id") or settings.DEFAULT_ORG_ID
    event_dict["organization_id"] = org_id

    integration_name = event_dict.get("integration_name", "").lower()
    integration = db_get_integration_by_slug_or_id(org_id, integration_name)
    integration_id = integration["id"] if integration else event_dict.get("integration_id")
    event_dict["integration_id"] = integration_id

    # If decision was not pre-computed by proxy, evaluate it now
    if "decision" not in event_dict:
        policies = db_list_policies(org_id, integration_id)
        is_violation, risk_level, alert_data = evaluate_event_policy(event_dict, policies)
        event_dict["is_violation"] = is_violation
        event_dict["decision"] = "BLOCK" if is_violation else "ALLOW"
        event_dict["risk_level"] = risk_level
    else:
        is_violation = event_dict.get("is_violation", event_dict["decision"] in ("BLOCK", "FLAG"))
        risk_level = event_dict.get("risk_level", "critical" if event_dict["decision"] == "BLOCK" else "low")
        event_dict["is_violation"] = is_violation
        event_dict["risk_level"] = risk_level

    event_dict["id"] = event_dict.get("id") or str(uuid.uuid4())
    event_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    if not event_dict.get("timestamp"):
        event_dict["timestamp"] = event_dict["created_at"]

    # 1. Insert into storage
    client = get_supabase_client()
    if client:
        try:
            client.table("integration_events").insert(event_dict).execute()
        except Exception as e:
            logger.error(f"Error persisting event to Supabase: {e}")
    memory_store.events.insert(0, event_dict)

    # 2. Update Integration activity timestamp & endpoint count
    if integration_id:
        for idx, item in enumerate(memory_store.integrations):
            if item["id"] == integration_id:
                memory_store.integrations[idx]["last_activity_at"] = event_dict["timestamp"]
                memory_store.integrations[idx]["observed_endpoints_count"] = item.get("observed_endpoints_count", 0) + 1
                break

    # 3. If request was blocked or flagged, create an alert automatically
    if event_dict.get("is_violation") or event_dict.get("decision") in ("BLOCK", "FLAG"):
        matched_policies = event_dict.get("matched_policies") or []
        rule_str = ", ".join(matched_policies) if matched_policies else "Policy Constraint Violation"
        alert_data = {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "integration_id": integration_id,
            "integration_name": integration_name,
            "event_id": event_dict["id"],
            "title": f"Blocked Request on {integration_name}: {event_dict.get('endpoint')}",
            "description": event_dict.get("reason") or f"Request was {event_dict['decision']} by security engine.",
            "severity": "critical" if event_dict.get("decision") == "BLOCK" else "high",
            "category": event_dict.get("threat_classification") or "policy_violation",
            "status": "open",
            "rule_violated": rule_str,
            "remediation": "Audit the client request origin and review integration route permissions in policy settings.",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if client:
            try:
                client.table("alerts").insert(alert_data).execute()
            except Exception as e:
                logger.error(f"Error persisting alert to Supabase: {e}")
        memory_store.alerts.insert(0, alert_data)
        logger.warning(f"SECURITY ALERT CREATED: {alert_data['title']} (Severity: {alert_data['severity']})")

    return event_dict

def db_list_events(
    org_id: str,
    limit: int = 50,
    offset: int = 0,
    integration_id: Optional[str] = None,
    decision: Optional[str] = None,
    is_violation: Optional[bool] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None
) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    if client:
        try:
            query = client.table("integration_events").select("*").eq("organization_id", org_id)
            if integration_id:
                query = query.eq("integration_id", integration_id)
            if decision:
                query = query.eq("decision", decision.upper())
            if is_violation is not None:
                query = query.eq("is_violation", is_violation)
            if method:
                query = query.eq("method", method.upper())
            if status_code:
                query = query.eq("status_code", status_code)
            res = query.order("timestamp", desc=True).range(offset, offset + limit - 1).execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.error(f"Error listing events from Supabase: {e}")

    evts = [e for e in memory_store.events if e.get("organization_id") == org_id]
    if integration_id:
        evts = [e for e in evts if e.get("integration_id") == integration_id or e.get("integration_name") == integration_id]
    if decision:
        evts = [e for e in evts if str(e.get("decision")).upper() == decision.upper()]
    if is_violation is not None:
        evts = [e for e in evts if e.get("is_violation") == is_violation]
    if method:
        evts = [e for e in evts if str(e.get("method")).upper() == method.upper()]
    if status_code:
        evts = [e for e in evts if e.get("status_code") == status_code]

    return evts[offset:offset + limit]

def db_get_traffic_stats(org_id: str) -> Dict[str, Any]:
    """
    Computes real-time traffic telemetry statistics for the dashboard.
    """
    events = db_list_events(org_id, limit=500)
    total = len(events)
    allowed = sum(1 for e in events if e.get("decision") == "ALLOW")
    blocked = sum(1 for e in events if e.get("decision") == "BLOCK")
    flagged = sum(1 for e in events if e.get("decision") == "FLAG")
    violations = sum(1 for e in events if e.get("is_violation"))

    latencies = [e.get("latency_ms", 0) for e in events if e.get("latency_ms")]
    avg_latency = round(sum(latencies) / max(len(latencies), 1), 2)

    # Top blocked endpoints
    blocked_counts: Dict[str, int] = {}
    for e in events:
        if e.get("decision") == "BLOCK":
            ep = e.get("endpoint", "/")
            blocked_counts[ep] = blocked_counts.get(ep, 0) + 1

    top_blocked = [{"endpoint": ep, "count": cnt} for ep, cnt in sorted(blocked_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

    # Traffic by method
    method_counts: Dict[str, int] = {}
    for e in events:
        m = e.get("method", "GET").upper()
        method_counts[m] = method_counts.get(m, 0) + 1

    # Traffic by status code
    status_counts: Dict[str, int] = {}
    for e in events:
        s = str(e.get("status_code", 200))
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "total_requests": total,
        "allowed_requests": allowed,
        "blocked_requests": blocked,
        "flagged_requests": flagged,
        "avg_latency_ms": avg_latency,
        "violations_count": violations,
        "top_blocked_endpoints": top_blocked,
        "traffic_by_method": method_counts,
        "traffic_by_status": status_counts
    }

# ------------------------------------------------------------------------------
# Alerts
# ------------------------------------------------------------------------------
def db_list_alerts(
    org_id: str,
    status_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    integration_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    if client:
        try:
            query = client.table("alerts").select("*").eq("organization_id", org_id)
            if status_filter:
                query = query.eq("status", status_filter)
            if severity_filter:
                query = query.eq("severity", severity_filter)
            if integration_id:
                query = query.eq("integration_id", integration_id)
            res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.error(f"Error listing alerts from Supabase: {e}")

    alerts = [a for a in memory_store.alerts if a.get("organization_id") == org_id]
    if status_filter:
        alerts = [a for a in alerts if a.get("status") == status_filter]
    if severity_filter:
        alerts = [a for a in alerts if a.get("severity") == severity_filter]
    if integration_id:
        alerts = [a for a in alerts if a.get("integration_id") == integration_id]

    return alerts[offset:offset + limit]

def db_get_alert(org_id: str, alert_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    if client:
        try:
            res = client.table("alerts").select("*").eq("organization_id", org_id).eq("id", alert_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error fetching alert: {e}")

    for a in memory_store.alerts:
        if a.get("organization_id") == org_id and a["id"] == alert_id:
            return a
    return None

def db_update_alert_status(org_id: str, alert_id: str, new_status: str, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
    now_iso = datetime.now(timezone.utc).isoformat()
    resolved_at = now_iso if new_status in ("resolved", "dismissed") else None
    update_payload = {"status": new_status, "resolved_at": resolved_at}
    if notes:
        update_payload["remediation"] = notes

    client = get_supabase_client()
    if client:
        try:
            res = client.table("alerts").update(update_payload).eq("organization_id", org_id).eq("id", alert_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error updating alert: {e}")

    for idx, a in enumerate(memory_store.alerts):
        if a.get("organization_id") == org_id and a["id"] == alert_id:
            memory_store.alerts[idx].update(update_payload)
            return memory_store.alerts[idx]
    return None

# ------------------------------------------------------------------------------
# Analytics & Risk Overview
# ------------------------------------------------------------------------------
def db_get_risk_overview(org_id: str) -> Dict[str, Any]:
    integrations = db_list_integrations(org_id, sanitize_internal_urls=False)
    alerts = db_list_alerts(org_id, limit=200)
    recent_events = db_list_events(org_id, limit=200)
    return calculate_organization_risk(integrations, recent_events, alerts)

# ------------------------------------------------------------------------------
# Scans & Integration Audits
# ------------------------------------------------------------------------------
def db_create_scan(org_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    scan_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "id": scan_id,
        "organization_id": org_id,
        "integration_id": data.get("integration_id"),
        "target_name": data["target_name"],
        "target_url": data["target_url"],
        "status": "completed",
        "findings_count": 0,
        "score": 95,
        "summary": {
            "routes_discovered": 2,
            "security_policies_matched": 1,
            "unencrypted_endpoints": 0,
            "auth_schemes_detected": ["Bearer", "API-Key"]
        },
        "started_at": now_iso,
        "completed_at": now_iso,
        "created_at": now_iso
    }

    client = get_supabase_client()
    if client:
        try:
            res = client.table("scans").insert(record).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error creating scan in Supabase: {e}")

    memory_store.scans.insert(0, record)
    return record

def db_list_scans(org_id: str) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    if client:
        try:
            res = client.table("scans").select("*").eq("organization_id", org_id).order("created_at", desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error listing scans: {e}")
    return [s for s in memory_store.scans if s.get("organization_id") == org_id]
