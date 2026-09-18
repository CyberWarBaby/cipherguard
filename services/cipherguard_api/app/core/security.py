import ipaddress
import socket
import urllib.parse
from fastapi import HTTPException, status
from typing import Tuple, Optional

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.169.254/32"), # AWS/GCP/Azure Metadata
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

# Allow internal docker network services for controlled hackathon demo if explicitly enabled
ALLOWED_DEMO_HOSTNAMES = {"shipfast-api", "payflex-api", "localhost", "127.0.0.1", "host.docker.internal"}

def validate_target_url(url: str, allow_internal_demo: Optional[bool] = None) -> str:
    """
    Validates a target URL to prevent SSRF vulnerabilities.
    Blocks cloud metadata endpoints, loopback, and private IPs unless explicitly allowed demo hostnames.
    """
    if allow_internal_demo is None:
        from app.config import settings
        allow_internal_demo = settings.ALLOW_INTERNAL_NETWORKS

    if not url or not isinstance(url, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target URL must be a valid string")

    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL scheme. Only HTTP and HTTPS are permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid target URL: missing hostname.")

    # Check allowed demo hostnames for local docker environment
    if allow_internal_demo and hostname.lower() in ALLOWED_DEMO_HOSTNAMES:
        return url


    # Resolve IP and verify not in blocked ranges
    try:
        ip_str = socket.gethostbyname(hostname)
        target_ip = ipaddress.ip_address(ip_str)

        for blocked_net in BLOCKED_IP_NETWORKS:
            if target_ip in blocked_net:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Security violation: Target resolves to a restricted/private network address ({ip_str})."
                )
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to resolve target host: {hostname}"
        )

    return url

def mask_sensitive_data(text: str) -> str:
    """Masks API keys, tokens, and authorization headers in logs."""
    if not text:
        return ""
    if len(text) <= 8:
        return "********"
    return f"{text[:4]}...{text[-4:]}"
