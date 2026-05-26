"""
Rate limiting decorators for FastAPI routes
Provides flexible route-specific rate limiting using SlowAPI
"""
from typing import Optional
from app.core.slowapi_limiter import limiter


def rate_limit(
    requests: int,
    window: int,
    key_func=None,
    scope: Optional[str] = None,
    exempt_when=None
):
    """
    Decorator for route-specific rate limiting.

    Args:
        requests: Maximum number of requests allowed
        window: Time window in seconds
        key_func: Custom function to extract rate limit key (defaults to IP)
        scope: Shared limit scope across routes
        exempt_when: Callable that returns True to exempt the request

    Example:
        @app.get("/api/data")
        @rate_limit(requests=10, window=60)
        async def get_data():
            pass

        @rate_limit(requests=1000, window=3600, scope="api")
        @app.get("/api/public")
        async def public_endpoint():
            pass
    """
    limit_str = f"{requests} per {window} seconds"

    decorator = limiter.limit(
        limit_str,
        key_func=key_func,
        scope=scope,
        exempt_when=exempt_when
    )

    return decorator


def shared_limit(
    requests: int,
    window: int,
    scope: str,
    key_func=None,
    exempt_when=None
):
    """
    Decorator for shared rate limits across multiple routes.

    Args:
        requests: Maximum number of requests allowed across all routes with this scope
        window: Time window in seconds
        scope: Unique scope identifier for shared limiting
        key_func: Custom function to extract rate limit key
        exempt_when: Callable that returns True to exempt the request

    Example:
        @shared_limit(requests=1000, window=3600, scope="user_uploads")
        @app.post("/upload/file")
        async def upload_file():
            pass

        @shared_limit(requests=1000, window=3600, scope="user_uploads")
        @app.post("/upload/image")
        async def upload_image():
            pass
    """
    return rate_limit(
        requests=requests,
        window=window,
        key_func=key_func,
        scope=scope,
        exempt_when=exempt_when
    )
