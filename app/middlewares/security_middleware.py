"""
Security headers middleware
Adds production-grade security headers to all responses
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import structlog

logger = structlog.get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all HTTP responses.
    Helps protect against common web vulnerabilities.
    """
    
    def __init__(self, app, enable_hsts: bool = True, debug: bool = False):
        """
        Initialize security headers middleware.
        
        Args:
            app: FastAPI application instance
            enable_hsts: Whether to enable HSTS (Strict-Transport-Security)
            debug: Whether in debug mode (allows more permissive CSP for Swagger UI)
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.debug = debug
        
        logger.info(
            "Security headers middleware initialized",
            hsts_enabled=enable_hsts,
            debug=debug
        )
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Enable XSS filter (legacy but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy (basic, can be customized)
        if self.debug:
            # Permissive CSP for development (allows Swagger UI external resources)
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' https://*; "
                "script-src 'self' https://cdn.jsdelivr.net https://fastapi.tiangolo.com 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "connect-src 'self' https://cdn.jsdelivr.net"
            )
        else:
            response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (HTTP Strict Transport Security) - only if HTTPS
        if self.enable_hsts and request.url.scheme == "https":
            # 1 year max-age, include subdomains
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
