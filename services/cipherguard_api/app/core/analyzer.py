from typing import Dict, Any, List, Optional, Tuple
from app.core.policy_engine import evaluate_request_policy, PolicyEvaluationResult
from app.core.threat_detector import inspect_threats
from app.core.risk_engine import calculate_integration_risk, calculate_organization_risk

def evaluate_event_policy(
    event: Dict[str, Any],
    policies: List[Dict[str, Any]]
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Evaluates an event or request dictionary against active policies.
    Returns: (is_violation, risk_level, alert_dict_if_any)
    """
    method = event.get("method", "GET")
    endpoint = event.get("endpoint", "/")
    integration_name = event.get("integration_name", "unknown")
    org_id = event.get("organization_id")
    integration_id = event.get("integration_id")

    dummy_integration = {
        "id": integration_id,
        "name": integration_name,
        "slug": integration_name,
        "status": "active"
    }

    result = evaluate_request_policy(
        integration=dummy_integration,
        policies=policies,
        method=method,
        path=endpoint
    )

    is_violation = (result.decision in ("BLOCK", "FLAG"))
    risk_level = result.severity

    alert_dict = None
    if is_violation:
        alert_dict = {
            "organization_id": org_id,
            "integration_id": integration_id,
            "title": f"{result.rule_violated or 'Policy Violation'} on {integration_name}",
            "description": result.reason,
            "severity": result.severity,
            "category": result.threat_classification or "policy_violation",
            "status": "open",
            "rule_violated": ", ".join(result.matched_policies) if result.matched_policies else result.rule_violated,
            "remediation": "Review integration access contract and client permissions."
        }

    return is_violation, risk_level, alert_dict

def calculate_risk_metrics(
    integrations: List[Dict[str, Any]],
    alerts: List[Dict[str, Any]],
    recent_events: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Wrapper for calculate_organization_risk.
    """
    return calculate_organization_risk(integrations, recent_events, alerts)

__all__ = [
    "evaluate_request_policy",
    "PolicyEvaluationResult",
    "inspect_threats",
    "calculate_integration_risk",
    "calculate_organization_risk",
    "evaluate_event_policy",
    "calculate_risk_metrics"
]
