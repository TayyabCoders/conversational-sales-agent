"""
Enterprise Logging Utility
==========================
Typed log helpers with enforced schema, sensitive data redaction,
and audit logging. Inspired by Pino's structured helpers — but built
for Python with structlog superpowers.

Usage:
    from app.utils.logger import create_logger, log_request, audit_log

    logger = create_logger("my_module")
    logger.info("hello", some_key="value")

    log_request(method="GET", path="/api/users", status_code=200, duration_ms=42)
    audit_log("UPDATE", user_id="u-1", resource_type="Order", resource_id="o-1", changes={"status": ["pending", "confirmed"]})
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

# ---------------------------------------------------------------------------
# Sensitive Data Redaction Processor
# ---------------------------------------------------------------------------

_REDACT_KEYS: set[str] = {
    "password", "passwd", "pass",
    "token", "access_token", "refresh_token",
    "secret", "secret_key",
    "authorization",
    "cookie", "set_cookie",
    "credit_card", "creditcard", "card_number",
    "ssn", "social_security",
    "api_key", "apikey",
    "private_key", "privatekey",
    "otp", "pin",
}

_REDACT_SENTINEL = "[REDACTED]"


def _should_redact(key: str) -> bool:
    """Check if a key matches any sensitive pattern (case-insensitive)."""
    normalised = key.lower().replace("-", "_").replace(" ", "_")
    return normalised in _REDACT_KEYS


def _redact_value(value: Any) -> Any:
    """Recursively redact sensitive values in dicts / lists."""
    if isinstance(value, dict):
        return {k: (_REDACT_SENTINEL if _should_redact(k) else _redact_value(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    return value


def redact_sensitive_data(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    structlog processor that scrubs sensitive fields from log output.

    Handles:
    - Top-level keys (e.g. password="abc" → password="[REDACTED]")
    - Nested dicts  (e.g. user={"password": "abc"} → user={"password": "[REDACTED]"})
    - Lists of dicts
    """
    return {
        k: (_REDACT_SENTINEL if _should_redact(k) else _redact_value(v))
        for k, v in event_dict.items()
    }


# ---------------------------------------------------------------------------
# Child Logger Factory
# ---------------------------------------------------------------------------

def create_logger(module: str) -> structlog.stdlib.BoundLogger:
    """Create a named child logger for a specific module.

    Example:
        logger = create_logger("auth_service")
        logger.info("user_logged_in", user_id="123")
    """
    return structlog.get_logger(module)


# ---------------------------------------------------------------------------
# Typed Log Helpers
# ---------------------------------------------------------------------------

_root = structlog.get_logger("app")


def log_request(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    user_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    query_string: Optional[str] = None,
    content_type: Optional[str] = None,
) -> None:
    """Log an API request/response with consistent structure."""
    _root.info(
        "api_request",
        type="api_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        user_id=user_id,
        client_ip=client_ip,
        user_agent=user_agent,
        query_string=query_string,
        content_type=content_type,
    )


def log_query(
    *,
    operation: str,
    table: str,
    duration_ms: int,
    status: str = "success",
    query: Optional[str] = None,
) -> None:
    """Log a database query."""
    _root.debug(
        "db_query",
        type="db_query",
        operation=operation,
        table=table,
        duration_ms=duration_ms,
        status=status,
        query=query,
    )


def log_cache(
    *,
    operation: str,
    key: str,
    hit: Optional[bool] = None,
) -> None:
    """Log a cache operation (GET/SET/DELETE)."""
    _root.debug(
        "cache_operation",
        type="cache_operation",
        operation=operation,
        key=key,
        hit=hit,
    )


def log_queue(
    *,
    queue_type: str,
    topic: str,
    operation: str,
    message_id: Optional[str] = None,
    message_type: Optional[str] = None,
) -> None:
    """Log a message queue publish/consume event."""
    _root.debug(
        "queue_message",
        type="queue_message",
        queue_type=queue_type,
        topic=topic,
        operation=operation,
        message_id=message_id,
        message_type=message_type,
    )


def log_external_api(
    *,
    service: str,
    method: str,
    url: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[int] = None,
) -> None:
    """Log an outbound HTTP call to an external service."""
    _root.info(
        "external_api",
        type="external_api",
        service=service,
        method=method,
        url=url,
        status_code=status_code,
        duration_ms=duration_ms,
    )


def log_business_event(
    event: str,
    *,
    status: str = "success",
    **data: Any,
) -> None:
    """Log a business domain event (order placed, payment received, etc.)."""
    _root.info(
        f"business_event:{event}",
        type="business_event",
        event=event,
        status=status,
        **data,
    )


def log_security_event(
    event: str,
    *,
    severity: str = "medium",
    **data: Any,
) -> None:
    """Log a security event (auth failure, RBAC violation, suspicious activity)."""
    level = _root.error if severity == "critical" else _root.warning
    level(
        f"security_event:{event}",
        type="security_event",
        event=event,
        severity=severity,
        **data,
    )


def log_performance(
    *,
    metric: str,
    value: float,
    unit: str = "ms",
) -> None:
    """Log a performance metric."""
    _root.info(
        "performance_metric",
        type="performance_metric",
        metric=metric,
        value=value,
        unit=unit,
    )


def log_error(
    error: Exception,
    *,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an error with context. Uses ERROR for 5xx, WARN for 4xx."""
    status_code = getattr(error, "status_code", 500)
    error_info = {
        "type": "application_error",
        "error_name": type(error).__name__,
        "error_message": str(error),
        "error_code": getattr(error, "code", None),
        **(context or {}),
    }
    if status_code >= 500 or not isinstance(status_code, int):
        _root.error("application_error", **error_info, exc_info=error)
    else:
        _root.warning("client_error", **error_info)


def audit_log(
    action: str,
    *,
    user_id: Optional[str] = None,
    resource_type: str,
    resource_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Compliance-grade audit trail entry.

    Example:
        audit_log(
            "UPDATE",
            user_id="user-123",
            resource_type="Order",
            resource_id="order-456",
            changes={"status": ["pending", "confirmed"]},
        )
    """
    _root.info(
        f"audit:{action}:{resource_type}",
        type="audit_log",
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        ip_address=ip_address,
        audit_timestamp=datetime.now(timezone.utc).isoformat(),
    )
