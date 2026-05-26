"""
Request/Response Logging Middleware
====================================
Logs every request/response with consistent structure using typed log helpers.
Features:
- Uses log_request() for consistent schema
- X-Response-Time header on every response
- Slow request detection (configurable threshold)
- User ID tracking when authenticated
- Performance segment summary
"""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.configs.app_config import settings
from app.utils.logger import log_request

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log request and response details with enterprise structure.
    """

    async def dispatch(self, request: Request, call_next):
        # Read IDs set by RequestContextMiddleware
        request_id = getattr(request.state, "request_id", "unknown")

        # Log request start with richer context
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_string=str(request.url.query) if request.url.query else None,
            client_ip=request.client.host if request.client else None,
            content_type=request.headers.get("content-type"),
            user_agent=request.headers.get("user-agent"),
        )

        try:
            response = await call_next(request)

            # Calculate duration
            start_time = getattr(request.state, "start_time", time.time())
            process_time = time.time() - start_time
            duration_ms = int(process_time * 1000)

            # Add response-time header
            response.headers["X-Response-Time"] = f"{duration_ms}ms"

            # Extract user_id if authenticated
            user = getattr(request.state, "user", None)
            user_id = str(user.id) if user and hasattr(user, "id") else None

            # Use typed log helper for consistent schema
            log_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                query_string=str(request.url.query) if request.url.query else None,
                content_type=request.headers.get("content-type"),
            )

            # Slow request detection
            threshold_ms = settings.LOG_SLOW_REQUEST_THRESHOLD_MS
            if duration_ms >= threshold_ms:
                logger.warning(
                    "slow_request_detected",
                    method=request.method,
                    path=request.url.path,
                    duration_ms=duration_ms,
                    threshold_ms=threshold_ms,
                    status_code=response.status_code,
                )

            # Log performance segment summary if tracker has segments
            perf = getattr(request.state, "performance", None)
            if perf and perf.has_segments():
                logger.info(
                    "request_performance",
                    method=request.method,
                    path=request.url.path,
                    total_ms=duration_ms,
                    segments=perf.get_metrics(),
                )

            return response

        except Exception as e:
            start_time = getattr(request.state, "start_time", time.time())
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )
            raise
