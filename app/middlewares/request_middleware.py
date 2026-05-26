import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from app.utils.tracking_util import PerformanceTracker

logger = structlog.get_logger(__name__)

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to establish request context:
    1. Generates/Extracts Request-ID and Correlation-ID.
    2. Injects PerformanceTracker into request state.
    3. Binds IDs to structlog contextvars.
    """
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Set IDs in request state for downstream use
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.start_time = time.time()
        
        # Inject performance tracker
        request.state.performance = PerformanceTracker(request)

        # Bind to structured logs
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id
        )

        response = await call_next(request)

        # Add IDs to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id

        return response
