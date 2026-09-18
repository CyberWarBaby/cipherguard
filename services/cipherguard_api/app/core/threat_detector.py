import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ThreatReport(BaseModel):
    is_threat: bool
    severity: str  # low, medium, high, critical
    category: str  # sqli, path_traversal, xss, sensitive_access, suspicious_client, malformed_payload
    rule_name: str
    description: str

# Regular expression signatures for common API threats
SQLI_PATTERNS = [
    r"(\b(union(\s+all)?)\b.+\b(select)\b)",
    r"(\b(select|insert|update|delete|drop|alter|truncate)\b\s+.+\b(from|into|table)\b)",
    r"('.+--)|(--\s*$)|(\b(or|and)\b\s+['\"\d\w]+(\s*=\s*|\s+is\s+)['\"\d\w]+)",
    r"(\/\*.*\*\/)",
    r"(;\s*(drop|shutdown|exec|select))"
]

PATH_TRAVERSAL_PATTERNS = [
    r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.\.%2f|%2e%2e%5c)",
    r"(/etc/(passwd|shadow|hosts|group))",
    r"([a-zA-Z]:\\(windows|winnt|system32))"
]

XSS_PATTERNS = [
    r"(<\s*script[^>]*>.*<\s*/\s*script\s*>)",
    r"(javascript\s*:\s*.+)",
    r"(on(load|error|click|mouseover|submit)\s*=)"
]

SUSPICIOUS_USER_AGENTS = [
    r"(sqlmap|nikto|nmap|masscan|zgrab|acunetix|nessus|gobuster|dirbuster|wpscan)",
]

SENSITIVE_PATH_PATTERNS = [
    (r"(\/|^)(admin|internal|private|debug|actuator|metrics)(\/|$)", "Restricted administrative endpoint pattern"),
    (r"(\/|^)(credentials|keys|tokens|passwords|secrets|vault)(\/|$)", "Sensitive credential / key retrieval pattern"),
    (r"(\/|^)(export|dump|backup|download-all)(\/|$)", "Bulk data exfiltration / dump pattern"),
]

def inspect_threats(
    method: str,
    path: str,
    query_params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    body_text: Optional[str] = None
) -> Optional[ThreatReport]:
    """
    Analyzes request metadata, URL, query string, headers, and body for attack signatures.
    Returns a ThreatReport if a threat is detected, otherwise None.
    """
    query_str = ""
    if query_params:
        query_str = " ".join(f"{k}={v}" for k, v in query_params.items())

    payload_to_check = f"{path} {query_str}"
    if body_text and len(body_text) < 50000:  # Cap scan size for performance
        payload_to_check += f" {body_text}"

    # 1. Check Path Traversal
    for pat in PATH_TRAVERSAL_PATTERNS:
        if re.search(pat, payload_to_check, re.IGNORECASE):
            return ThreatReport(
                is_threat=True,
                severity="critical",
                category="path_traversal",
                rule_name="Directory Traversal Signature",
                description=f"Path traversal sequence detected in request: pattern '{pat}'"
            )

    # 2. Check SQL Injection
    for pat in SQLI_PATTERNS:
        if re.search(pat, payload_to_check, re.IGNORECASE):
            return ThreatReport(
                is_threat=True,
                severity="critical",
                category="sqli",
                rule_name="SQL Injection Signature",
                description=f"SQL injection syntax detected: pattern '{pat}'"
            )

    # 3. Check XSS
    for pat in XSS_PATTERNS:
        if re.search(pat, payload_to_check, re.IGNORECASE):
            return ThreatReport(
                is_threat=True,
                severity="high",
                category="xss",
                rule_name="Cross-Site Scripting Signature",
                description="Cross-Site Scripting (XSS) script tag or handler detected."
            )

    # 4. Check Suspicious User-Agent
    if headers:
        user_agent = headers.get("user-agent", "").lower()
        for pat in SUSPICIOUS_USER_AGENTS:
            if re.search(pat, user_agent, re.IGNORECASE):
                return ThreatReport(
                    is_threat=True,
                    severity="high",
                    category="suspicious_client",
                    rule_name="Automated Attack Scanner",
                    description=f"Known automated vulnerability scanner or exploit tool detected: {user_agent}"
                )

    # 5. Check Sensitive Endpoint Patterns
    for pat, desc in SENSITIVE_PATH_PATTERNS:
        if re.search(pat, path, re.IGNORECASE):
            return ThreatReport(
                is_threat=True,
                severity="high",
                category="sensitive_access",
                rule_name="Sensitive Keyword Access",
                description=f"{desc} matching '{path}'"
            )

    return None
