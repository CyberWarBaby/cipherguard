from typing import Dict, Any, List, Tuple

def calculate_integration_risk(
    integration: Dict[str, Any],
    events: List[Dict[str, Any]],
    alerts: List[Dict[str, Any]]
) -> Tuple[int, str, List[str]]:
    """
    Deterministically computes the risk score (0-100), risk level, and explanation factors
    for a specific integration based on recent security telemetry and active alerts.
    """
    intg_id = integration.get("id")
    intg_name = integration.get("name", "Integration")

    # Filter alerts and events for this integration
    intg_alerts = [a for a in alerts if a.get("integration_id") == intg_id and a.get("status") in ("open", "investigating")]
    intg_events = [e for e in events if e.get("integration_id") == intg_id or e.get("integration_name") == integration.get("slug")]

    critical_alerts = [a for a in intg_alerts if a.get("severity") == "critical"]
    high_alerts = [a for a in intg_alerts if a.get("severity") == "high"]
    medium_alerts = [a for a in intg_alerts if a.get("severity") == "medium"]

    blocked_events = [e for e in intg_events if e.get("decision") == "BLOCK" or e.get("is_violation")]
    server_error_events = [e for e in intg_events if e.get("status_code", 200) >= 500]

    factors: List[str] = []
    score = 10  # Baseline operational risk

    # 1. Alert Penalties
    if critical_alerts:
        penalty = len(critical_alerts) * 35
        score += penalty
        factors.append(f"{len(critical_alerts)} Critical active alert(s) (+{penalty} pts)")

    if high_alerts:
        penalty = len(high_alerts) * 20
        score += penalty
        factors.append(f"{len(high_alerts)} High active alert(s) (+{penalty} pts)")

    if medium_alerts:
        penalty = len(medium_alerts) * 8
        score += penalty
        factors.append(f"{len(medium_alerts)} Medium active alert(s) (+{penalty} pts)")

    # 2. Blocked Traffic Penalties
    if blocked_events:
        penalty = min(len(blocked_events) * 15, 30)
        score += penalty
        factors.append(f"{len(blocked_events)} Blocked/prohibited request(s) (+{penalty} pts)")

    # 3. Upstream Reliability Anomaly Penalties
    if server_error_events:
        penalty = min(len(server_error_events) * 5, 15)
        score += penalty
        factors.append(f"{len(server_error_events)} Server error spike(s) (+{penalty} pts)")

    # 4. Status Constraints
    if integration.get("status") == "restricted":
        score += 20
        factors.append("Integration operates in restricted policy mode (+20 pts)")
    elif integration.get("status") == "paused":
        score += 30
        factors.append("Integration is administratively paused (+30 pts)")

    if not factors:
        factors.append("No active policy violations or alerts. Clean traffic baseline.")

    # Clamp score to 0 - 100
    final_score = min(max(score, 0), 100)

    # Determine risk level
    if final_score >= 85:
        level = "critical"
    elif final_score >= 60:
        level = "high"
    elif final_score >= 30:
        level = "medium"
    else:
        level = "low"

    return final_score, level, factors

def calculate_organization_risk(
    integrations: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    alerts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Aggregates integration risks and computes organizational threat posture metrics.
    """
    breakdown = []
    total_score = 0
    active_alerts = [a for a in alerts if a.get("status") in ("open", "investigating")]
    critical_count = sum(1 for a in active_alerts if a.get("severity") == "critical")

    for intg in integrations:
        score, level, factors = calculate_integration_risk(intg, events, alerts)
        breakdown.append({
            "id": intg.get("id"),
            "name": intg.get("name"),
            "slug": intg.get("slug"),
            "category": intg.get("category"),
            "risk_score": score,
            "risk_level": level,
            "active_alerts_count": len([a for a in active_alerts if a.get("integration_id") == intg.get("id")]),
            "risk_factors": factors
        })
        total_score += score

    avg_score = round(total_score / max(len(integrations), 1))
    
    # Weight organization risk towards the highest integration risk if critical alerts exist
    if critical_count > 0:
        highest_score = max((b["risk_score"] for b in breakdown), default=avg_score)
        org_score = max(avg_score, round(highest_score * 0.85))
    else:
        org_score = avg_score

    org_score = min(max(org_score, 0), 100)

    if org_score >= 85:
        org_level = "critical"
    elif org_score >= 60:
        org_level = "high"
    elif org_score >= 30:
        org_level = "medium"
    else:
        org_level = "low"

    violations_count_24h = sum(1 for e in events if e.get("decision") == "BLOCK" or e.get("is_violation"))

    return {
        "overall_risk_score": org_score,
        "overall_risk_level": org_level,
        "total_monitored_integrations": len(integrations),
        "total_active_alerts": len(active_alerts),
        "critical_alerts_count": critical_count,
        "total_observed_events_24h": len(events),
        "violations_count_24h": violations_count_24h,
        "integration_risk_breakdown": breakdown,
        "recent_activity_timeline": [
            {
                "id": e.get("id"),
                "integration_name": e.get("integration_name"),
                "method": e.get("method"),
                "endpoint": e.get("endpoint"),
                "status_code": e.get("status_code"),
                "decision": e.get("decision", "ALLOW"),
                "is_violation": e.get("is_violation", False),
                "risk_level": e.get("risk_level", "low"),
                "timestamp": e.get("timestamp")
            }
            for e in events[:15]
        ]
    }
