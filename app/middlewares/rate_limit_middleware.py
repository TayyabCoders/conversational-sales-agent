"""
Rate limiting middleware for FastAPI using SlowAPI
Enhanced with enterprise features: Redis storage, comprehensive headers, structured errors
"""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
import structlog
from datetime import datetime, timezone
import time

from app.core.slowapi_limiter import limiter, get_client_ip
from app.configs.app_config import settings

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce sliding window rate limiting using SlowAPI.
    Configurable exempt routes for health checks, metrics, etc.
    Provides comprehensive rate limit headers and structured error responses.
    """

    def __init__(self, app):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)
        self.exempt_routes = set(settings.RATE_LIMIT_EXEMPT_ROUTES)

        logger.info(
            "Rate limit middleware initialized",
            exempt_routes=list(self.exempt_routes),
            strategy=settings.RATE_LIMIT_STRATEGY,
            storage=settings.RATE_LIMIT_STORAGE_URL
        )

    async def dispatch(self, request, call_next):
        """Process request with rate limiting."""
        # Check if route is exempt
        if request.url.path in self.exempt_routes:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = get_client_ip(request)

        # Check rate limit using SlowAPI's limiter
        try:
            # limiter.limiter.hit returns True if allowed, False if exceeded
            allowed = limiter.limiter.hit(client_ip, cost=1)

            if not allowed:
                # Get window stats for headers and response
                stats = limiter.limiter.get_window_stats(client_ip)
                retry_after = int(stats[2])  # reset_time - now
                reset_time = datetime.fromtimestamp(stats[2], tz=timezone.utc).isoformat()

                logger.warning(
                    "Rate limit exceeded",
                    client_ip=client_ip,
                    path=request.url.path,
                    retry_after=retry_after,
                    reset_at=reset_time
                )

                return JSONResponse(
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit exceeded. Please retry after {retry_after} seconds.",
                            "details": {
                                "limit": settings.RATE_LIMIT_REQUESTS,
                                "window": f"{settings.RATE_LIMIT_WINDOW} seconds",
                                "retry_after": retry_after,
                                "reset_at": reset_time
                            }
                        }
                    },
                    headers={"Retry-After": str(retry_after)}
                )

        except Exception as e:
            # If rate limiting fails, log error but allow request
            logger.error(
                "Rate limiting error, allowing request",
                client_ip=client_ip,
                error=str(e)
            )

        # Process request
        response = await call_next(request)

        # Add rate limit info to response headers if enabled
        if settings.RATE_LIMIT_HEADER_ENABLED:
            try:
                stats = limiter.limiter.get_window_stats(client_ip)
                remaining = max(0, stats[0])  # remaining_requests
                reset_time = int(stats[2])  # reset_time

                response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(reset_time)
            except Exception as e:
                logger.warning("Failed to add rate limit headers", error=str(e))

        return response
