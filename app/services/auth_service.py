from typing import Optional, Dict, Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.schemas.user_schema import UserCreate
from app.di.container import container
import structlog
from dependency_injector.wiring import inject, Provide

logger = structlog.get_logger(__name__)


class AuthService:
    @inject
    def __init__(
        self,
        user_repository = Provide["user_repository"],
        prometheus = Provide["prometheus"],
        security_util = Provide["security_util"],
        cache = Provide["cache"],
    ):
        self.user_repository = user_repository
        self.prometheus = prometheus
        self.security_util = security_util
        # Redis cache for stateful refresh tokens
        self.cache = cache
    
    async def register(self, user_data: UserCreate) -> Dict[str, Any]:
        try:
            logger.info("AuthService: Registering user...")
            
            # Check if user already exists
            if await self.user_repository.findByUsername(user_data.username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
        
            if await self.user_repository.findByEmail(user_data.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )

            # Hash password and create user
            user_dict = user_data.model_dump()
            password = user_dict.pop("password")
            user_dict["hashed_password"] = self.security_util.get_password_hash(password)
            
            user = await self.user_repository.create(user_dict)
            logger.info(f"User registered successfully: {user.username}")
            
            # Record business event
            self.prometheus.record_business_event("user_registration", "success")
            
            return user
        
        except Exception as e:
            logger.error("AuthService: Failed to register user.", exc_info=True)
            raise e

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        try:
            logger.info("AuthService: Logging in user...")
            
            # Try finding by username first, then email
            user = await self.user_repository.findByEmail(email)
            if not user:
                user = await self.user_repository.findByEmail(email)

            if not user or not self.security_util.verify_password(password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user"
                )

            # Generate access and refresh tokens
            access_token = self.security_util.create_access_token(data={"sub": user.email})
            refresh_token = self.security_util.create_refresh_token(data={"sub": user.email})

            # Store refresh token in Redis for stateful validation/rotation
            try:
                if self.cache and self.cache.connected:
                    key = f"refresh_token:{refresh_token}"
                    # 30 days TTL (in seconds), similar to Node implementation
                    ttl_seconds = 30 * 24 * 60 * 60
                    await self.cache.set(
                        key,
                        {
                            "user_id": str(user.id),
                            "email": user.email,
                        },
                        ttl=ttl_seconds,
                    )
                else:
                    logger.warning(
                        "AuthService: Cache not connected, refresh tokens will not be persisted",
                    )
            except Exception:
                # Do not block login on cache issues; log and continue
                logger.error("AuthService: Failed to store refresh token in cache", exc_info=True)
            
            logger.info(f"User logged in: {user.username}")
            
            # Record business event
            self.prometheus.record_business_event("user_login", "success")
        
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": user,
            }
        
        except Exception as e:
            logger.error("AuthService: Failed to log in user.", exc_info=True)
            raise e

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        try:
            """Generate a new access token using a valid refresh token.

            This implementation mirrors the Node behavior by validating the
            refresh token against Redis and rotating it.
            """

            # First, check presence of refresh token in Redis (stateful validation)
            cache_data: Optional[Dict[str, Any]] = None
            if self.cache and self.cache.connected:
                key = f"refresh_token:{refresh_token}"
                cache_data = await self.cache.get(key)

            if not cache_data:
                # As a fallback, still allow purely JWT-based validation if desired
                payload = self.security_util.decode_token(refresh_token)
                if not payload or payload.get("type") != "refresh":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid refresh token",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                username = payload.get("sub")
            else:
                username = cache_data.get("email")

            if not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Verify user still exists and is active
            user = await self.user_repository.findByEmail(username)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Rotate refresh token in Redis (if available)
            new_refresh_token: Optional[str] = None
            try:
                if self.cache and self.cache.connected:
                    old_key = f"refresh_token:{refresh_token}"
                    # Remove old token entry
                    await self.cache.delete(old_key)

                    new_refresh_token = self.security_util.create_refresh_token(
                        data={"sub": user.email}
                    )
                    new_key = f"refresh_token:{new_refresh_token}"
                    ttl_seconds = 30 * 24 * 60 * 60
                    await self.cache.set(
                        new_key,
                        {
                            "user_id": str(user.id),
                            "email": user.email,
                        },
                        ttl=ttl_seconds,
                    )
            except Exception:
                logger.error(
                    "AuthService: Failed to rotate refresh token in cache",
                    exc_info=True,
                )

            # Generate new access token
            access_token = self.security_util.create_access_token(data={"sub": user.email})
            logger.info(f"Access token refreshed for user: {user.email}")

            response: Dict[str, Any] = {
                "access_token": access_token,
                "token_type": "bearer",
            }
            if new_refresh_token:
                response["refresh_token"] = new_refresh_token

            return response
        
        except Exception as e:
            logger.error("AuthService: Failed to refresh access token.", exc_info=True)
            raise e

    async def logout(self, refresh_token: Optional[str] = None) -> Dict[str, Any]:
        try:
            """
            Logout user. In a production system, you would:
            1. Invalidate the refresh token (add to blacklist/revoke in DB)
            2. Optionally invalidate the access token (though it will expire naturally)
            
            For now, we'll just return a success message.
            """
            if refresh_token:
                # Revoke refresh token from Redis cache if present
                try:
                    if self.cache and self.cache.connected:
                        key = f"refresh_token:{refresh_token}"
                        await self.cache.delete(key)
                        logger.info("User logged out and refresh token revoked")
                    else:
                        logger.warning(
                            "AuthService: Cache not connected, cannot revoke refresh token",
                        )
                except Exception:
                    logger.error(
                        "AuthService: Failed to revoke refresh token during logout",
                        exc_info=True,
                    )
            else:
                logger.info("User logged out (client-side only)")
        
            return {"message": "Successfully logged out"}
        
        except Exception as e:
            logger.error("AuthService: Failed to log out user.", exc_info=True)
            raise e

    async def request_password_reset(self, email: str) -> Dict[str, Any]:
        try:
            """
            Generate a password reset token and send it via email.
            In production, you would:
            1. Store the token in database with expiration
            2. Send email with reset link
            """
            user = await self.user_repository.findByEmail(email)
        
            if not user:
                # For security, don't reveal if email exists
                logger.warning(f"Password reset requested for non-existent email: {email}")
                return {
                    "message": "If the email exists, a password reset link has been sent"
                }
        
            # Generate password reset token
            reset_token = self.security_util.create_password_reset_token(email)
        
            # TODO: Store token in database with expiration
            # TODO: Send email with reset link
            logger.info(f"Password reset requested for user: {user.username}")
        
            # In development, return the token (REMOVE IN PRODUCTION)
            return {
                "message": "If the email exists, a password reset link has been sent",
                "reset_token": reset_token  # Only for development/testing
            }
        
        except Exception as e:
            logger.error("AuthService: Failed to request password reset.", exc_info=True)
            raise e

    async def reset_password(self, token: str, new_password: str) -> Dict[str, Any]:
        try:
            """Reset user password using a valid reset token"""
            email = self.security_util.verify_password_reset_token(token)
            
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired reset token"
                )
            
            user = await self.user_repository.findByEmail(email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Update password
            hashed_password = self.security_util.get_password_hash(new_password)
            await self.user_repository.update(user.id, {"hashed_password": hashed_password})
            
            # TODO: Invalidate all existing tokens for this user
            logger.info(f"Password reset successful for user: {user.username}")
            
            return {"message": "Password has been reset successfully"}

        except Exception as e:
            logger.error("AuthService: Failed to reset password.", exc_info=True)
            raise e