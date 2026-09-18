import fnmatch
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from app.core.threat_detector import inspect_threats, ThreatReport

class PolicyEvaluationResult(BaseModel):
    decision: Literal["ALLOW", "BLOCK", "FLAG"]
    risk_score: int
    matched_policies: List[str] = Field(default_factory=list)
    reason: str
    rule_violated: Optional[str] = None
    threat_classification: Optional[str] = None
    severity: Literal["low", "medium", "high", "critical"] = "low"

def path_matches_pattern(path: str, pattern: str) -> bool:
    """Checks wildcard pattern match (e.g., /orders/* or /admin/*)."""
    norm_path = "/" + path.strip("/")
    norm_pattern = "/" + pattern.strip("/")
    return fnmatch.fnmatch(norm_path, norm_pattern) or fnmatch.fnmatch(norm_path, norm_pattern + "/*")

def evaluate_request_policy(
    integration: Dict[str, Any],
    policies: List[Dict[str, Any]],
    method: str,
    path: str,
    query_params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    body_text: Optional[str] = None,
    client_ip: Optional[str] = None
) -> PolicyEvaluationResult:
    """
    Executes deep inline security and policy evaluation on an API request destined for an integration.
    Determines whether the request is ALLOW, BLOCK, or FLAG.
    """
    method = method.upper()
    integration_name = integration.get("name", "Unknown Integration")
    integration_status = integration.get("status", "active")

    # 1. Integration Lifecycle State Check
    if integration_status == "paused":
        return PolicyEvaluationResult(
            decision="BLOCK",
            risk_score=75,
            matched_policies=["Integration Lifecycle Policy"],
            reason=f"Integration '{integration_name}' is currently paused by administrator.",
            rule_violated="integration_paused",
            threat_classification="administrative_pause",
            severity="medium"
        )

    # 2. Configured Blocked Endpoints Check (Explicit Administrator Policies)
    for policy in policies:
        if not policy.get("is_active", True):
            continue

        policy_name = policy.get("name", "Security Policy")
        blocked_list = policy.get("blocked_endpoints") or []
        for blocked_pat in blocked_list:
            if path_matches_pattern(path, blocked_pat):
                return PolicyEvaluationResult(
                    decision="BLOCK",
                    risk_score=87,
                    matched_policies=[f"{policy_name}: Blocked pattern '{blocked_pat}'"],
                    reason=f"Administrative/restricted endpoint access is prohibited: '{path}' matches rule '{blocked_pat}'",
                    rule_violated=f"Blocked Pattern: {blocked_pat}",
                    threat_classification="unauthorized_endpoint",
                    severity="critical"
                )

    # 3. Threat Detection (SQLi, Path Traversal, XSS, Scanners)
    threat = inspect_threats(
        method=method,
        path=path,
        query_params=query_params,
        headers=headers,
        body_text=body_text
    )

    if threat and threat.severity in ("critical", "high"):
        return PolicyEvaluationResult(
            decision="BLOCK",
            risk_score=95 if threat.severity == "critical" else 85,
            matched_policies=[f"Threat Shield: {threat.rule_name}"],
            reason=f"Blocked malicious request signature: {threat.description}",
            rule_violated=threat.rule_name,
            threat_classification=threat.category,
            severity=threat.severity
        )

    # 4. Method Restrictions & Whitelist Policies
    for policy in policies:
        if not policy.get("is_active", True):
            continue

        policy_name = policy.get("name", "Security Policy")

        # 4a. Disallowed HTTP Methods Check
        allowed_methods = [m.upper() for m in (policy.get("allowed_methods") or ["GET"])]
        if method not in allowed_methods:
            action = policy.get("action_on_violation", "block")
            decision_type = "BLOCK" if action == "block" else "FLAG"
            return PolicyEvaluationResult(
                decision=decision_type,
                risk_score=70,
                matched_policies=[f"{policy_name}: Method Restriction"],
                reason=f"HTTP method '{method}' is not permitted for {integration_name}. Allowed: {', '.join(allowed_methods)}",
                rule_violated=f"Disallowed Method: {method}",
                threat_classification="method_restriction",
                severity="high"
            )

        # 4b. Allowed Endpoints Whitelist Check
        allowed_endpoints = policy.get("allowed_endpoints") or ["/*"]
        if allowed_endpoints and "/*" not in allowed_endpoints:
            matched = any(path_matches_pattern(path, pat) for pat in allowed_endpoints)
            if not matched:
                action = policy.get("action_on_violation", "alert")
                decision_type = "BLOCK" if action == "block" else "FLAG"
                return PolicyEvaluationResult(
                    decision=decision_type,
                    risk_score=55,
                    matched_policies=[f"{policy_name}: Endpoint Whitelist"],
                    reason=f"Endpoint '{path}' is not within the authorized contract whitelist for {integration_name}.",
                    rule_violated="Endpoint not in whitelist",
                    threat_classification="unmapped_endpoint",
                    severity="medium"
                )

    # 5. If sensitive keyword pattern flagged for auditing
    if threat and threat.severity == "medium":
        return PolicyEvaluationResult(
            decision="FLAG",
            risk_score=40,
            matched_policies=[f"Audit Guard: {threat.rule_name}"],
            reason=f"Sensitive request pattern flagged for audit: {threat.description}",
            rule_violated=threat.rule_name,
            threat_classification=threat.category,
            severity="medium"
        )

    # 6. Clean Request: ALLOW
    return PolicyEvaluationResult(
        decision="ALLOW",
        risk_score=10,
        matched_policies=[],
        reason="Request permitted by security policy.",
        rule_violated=None,
        threat_classification=None,
        severity="low"
    )
