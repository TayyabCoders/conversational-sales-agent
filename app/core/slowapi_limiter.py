from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from app.configs.app_config import settings

import ipaddress
from typing import Optional

def get_client_ip(request: Request) -> str:
    """
    Extract real client IP with comprehensive proxy support.
    Priority: X-Forwarded-For > X-Real-IP > CF-Connecting-IP > client.host
    Handle comma-separated proxy chains, validate IP format, fallback gracefully.
    """
    headers_priority = [
        "X-Forwarded-For",
        "X-Real-IP", 
        "CF-Connecting-IP"
    ]
    
    for header in headers_priority:
        header_value = request.headers.get(header)
        if header_value:
            # Handle comma-separated values (proxy chain)
            ips = [ip.strip() for ip in header_value.split(",")]
            for ip in ips:
                if _is_valid_ip(ip):
                    return ip
    
    # Fallback to client.host
    client_host = request.client.host if request.client else None
    if client_host and _is_valid_ip(client_host):
        return client_host
    
    # Ultimate fallback
    return "127.0.0.1"

def _is_valid_ip(ip: str) -> bool:
    """Validate if string is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

# Initialize Limiter
# By default, it uses the storage_uri from settings
limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=settings.RATE_LIMIT_STORAGE_URL,
    enabled=settings.RATE_LIMIT_ENABLED,
    default_limits=[f"{settings.RATE_LIMIT_REQUESTS} per {settings.RATE_LIMIT_WINDOW} seconds"],
    strategy=settings.RATE_LIMIT_STRATEGY,
    headers_enabled=settings.RATE_LIMIT_HEADER_ENABLED,
    key_prefix=settings.RATE_LIMIT_KEY_PREFIX,
)
