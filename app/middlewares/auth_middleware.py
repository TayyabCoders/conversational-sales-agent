"""
Production-grade authentication middleware for FastAPI
Based on Node.js boilerplate auth.hook.js patterns
"""
from typing import Optional, List
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, ExpiredSignatureError
import structlog
from dependency_injector.wiring import inject, Provide

from app.di.container import container
from app.utils.security_util import decode_token
from app.models.user_model import User, Role

logger = structlog.get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)

# Public routes that don't require authentication
PUBLIC_ROUTES = [
    "/",
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
]


def is_public_route(path: str) -> bool:
    """Check if the route is public and doesn't require authentication."""
    return any(path.startswith(route) for route in PUBLIC_ROUTES)


@inject
async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_repository = Provide["user_repository"]
) -> User:
    """
    Dependency to get the current authenticated user.
    Raises HTTPException if authentication fails.
    
    Usage in routes:
        @router.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}
    """
    # Check if route is public
    if is_public_route(request.url.path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="get_current_user should not be called on public routes"
        )
    
    # Check for credentials
    if not credentials:
        logger.warning(
            "Missing authorization header",
            path=request.url.path,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        # Decode and verify token
        payload = decode_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract email/username from token
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify it's an access token (not refresh token)
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Use access token for authentication",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
    except ExpiredSignatureError:
        logger.warning(
            "Expired token",
            path=request.url.path,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning(
            "Invalid token",
            error=str(e),
            path=request.url.path,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database
    user = await user_repository.findByEmail(email)
    
    if not user:
        logger.warning(
            "User not found",
            email=email,
            path=request.url.path
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(
            "Inactive user attempted access",
            user_id=str(user.id),
            email=user.email,
            path=request.url.path
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Attach user to request state for downstream use
    request.state.user = user
    
    logger.debug(
        "User authenticated successfully",
        user_id=str(user.id),
        email=user.email,
        role=user.role.value
    )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get the current active user.
    This is a convenience wrapper around get_current_user.
    
    Usage in routes:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_active_user)):
            return {"user": user.email}
    """
    # get_current_user already checks is_active, so just return
    return current_user


@inject
async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_repository = Provide["user_repository"]
) -> Optional[User]:
    """
    Optional authentication dependency.
    Returns user if valid token is provided, None otherwise.
    Does not raise exceptions for missing or invalid tokens.
    
    Usage in routes:
        @router.get("/maybe-protected")
        async def maybe_protected_route(user: Optional[User] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello, {user.email}"}
            return {"message": "Hello, guest"}
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    try:
        # Decode and verify token
        payload = decode_token(token)
        
        if not payload:
            logger.debug("Invalid token in optional auth")
            return None
        
        # Extract email
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if not email or token_type != "access":
            logger.debug("Invalid token payload in optional auth")
            return None
        
        # Fetch user from database
        user = await user_repository.findByEmail(email)
        
        if user and user.is_active:
            # Attach user to request state
            request.state.user = user
            logger.debug(
                "User authenticated via optional auth",
                user_id=str(user.id),
                email=user.email
            )
            return user
        
        return None
        
    except (ExpiredSignatureError, JWTError) as e:
        logger.debug("Token error in optional auth", error=str(e))
        return None


def require_role(*allowed_roles: Role):
    """
    Dependency factory for role-based access control.
    
    Usage in routes:
        @router.delete("/admin/users/{user_id}")
        async def delete_user(
            user_id: str,
            current_user: User = Depends(require_role(Role.admin))
        ):
            return {"message": "User deleted"}
        
        @router.get("/staff/dashboard")
        async def staff_dashboard(
            current_user: User = Depends(require_role(Role.admin, Role.staff))
        ):
            return {"message": "Staff dashboard"}
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(
                "Access denied: insufficient permissions",
                user_id=str(current_user.id),
                user_role=current_user.role.value,
                required_roles=[role.value for role in allowed_roles]
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return role_checker


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Convenience dependency for admin-only routes.
    
    Usage in routes:
        @router.get("/admin/settings")
        async def admin_settings(admin: User = Depends(require_admin)):
            return {"message": "Admin settings"}
    """
    if current_user.role != Role.admin:
        logger.warning(
            "Access denied: admin required",
            user_id=str(current_user.id),
            user_role=current_user.role.value
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user
