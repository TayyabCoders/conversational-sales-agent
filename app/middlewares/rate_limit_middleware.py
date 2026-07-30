"""
Rate limiting middleware using SlowAPI properly.
Uses app.state.limiter + SlowAPIMiddleware as designed by the library.
Exempt routes are checked before delegating to SlowAPI.
"""
import structlog
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from app.configs.app_config import settings

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(SlowAPIMiddleware):
    """
    Thin wrapper around SlowAPIMiddleware that adds path-based exemptions.
    Reads exempt paths from settings.RATE_LIMIT_EXEMPT_ROUTES.
    """

    def __init__(self, app):
        super().__init__(app)
        self._exempt_paths = set(settings.RATE_LIMIT_EXEMPT_ROUTES)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        if request.url.path in self._exempt_paths:
            return await call_next(request)

        try:
            return await super().dispatch(request, call_next)
        except RateLimitExceeded as exc:
            retry_after = exc.headers.get("Retry-After", str(settings.RATE_LIMIT_WINDOW))
            logger.warning(
                "Rate limit exceeded",
                path=request.url.path,
                retry_after=retry_after,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Retry after {retry_after} seconds.",
                        "details": {
                            "limit": settings.RATE_LIMIT_REQUESTS,
                            "window": f"{settings.RATE_LIMIT_WINDOW} seconds",
                            "retry_after": int(retry_after),
                        },
                    }
                },
                headers={"Retry-After": retry_after},
            )
