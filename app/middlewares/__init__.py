from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.configs.app_config import settings
from app.middlewares.exception_middleware import setup_exception_handlers
from app.middlewares.request_middleware import RequestContextMiddleware
from app.middlewares.logging_middleware import LoggingMiddleware
from app.middlewares.security_middleware import SecurityHeadersMiddleware
from app.middlewares.rate_limit_middleware import RateLimitMiddleware
import structlog

logger = structlog.get_logger(__name__)

def register_middlewares(app: FastAPI):
    """
    Centralized middleware registration for the FastAPI application.
    
    IMPORTANT: Middleware execution order (LIFO for request, FIFO for response):
    - Request phase: Last registered → First registered
    - Response phase: First registered → Last registered
    
    Registration order (as seen below):
    1. Exception handlers (setup first)
    2. CORS (must be early for preflight requests)
    3. Security headers
    4. Rate limiting (optional, can be disabled via config)
    5. Logging
    6. Request context (executed first in request phase)
    """
    
    # 1. Setup global exception handlers (not middleware, but critical)
    setup_exception_handlers(app)
    logger.info("Exception handlers registered")

    # 2. Add CORS middleware (early for preflight requests)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware registered", origins=settings.CORS_ORIGINS)

    # 3. Add security headers middleware
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=not settings.DEBUG,  # Only enable HSTS in production
        debug=settings.DEBUG
    )
    logger.info("Security headers middleware registered")

    # 4. Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limiting middleware registered")

    # 5. Add logging middleware
    app.add_middleware(LoggingMiddleware)
    logger.info("Logging middleware registered")
    
    # 6. Add request context middleware (executed first in request phase)
    app.add_middleware(RequestContextMiddleware)
    logger.info("Request context middleware registered")
    
    logger.info("All middlewares registered successfully")

