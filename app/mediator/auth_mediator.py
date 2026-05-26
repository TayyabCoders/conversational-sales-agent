from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger

logger = get_logger(__name__)

class AuthMediator:
    @inject
    def __init__(
        self,
        auth_service = Provide["auth_service"]
    ):
        self.auth_service = auth_service

    async def register_user(self, user_data):
        
        try:
            logger.info("AuthMediator: Registering user...")
            
            user = await self.auth_service.register(user_data)
            
            logger.info("AuthMediator: User registered successfully.")
            
            return user
        
        except Exception as e:
            logger.error("AuthMediator: Failed to register user.", exc_info=True)
            raise e

    async def authenticate_user(self, username: str, password: str):
        try:
            logger.info("AuthMediator: Authenticating user...")
            
            result = await self.auth_service.login(username, password)
            
            logger.info("AuthMediator: User authenticated successfully.")
            
            return result
        
        except Exception as e:
            logger.error("AuthMediator: Failed to authenticate user.", exc_info=True)
            raise e

    async def refresh_access_token(self, refresh_token: str):
        try:
            logger.info("AuthMediator: Refreshing access token...")
            
            result = await self.auth_service.refresh_token(refresh_token)
            
            logger.info("AuthMediator: Access token refreshed successfully.")
            
            return result
        
        except Exception as e:
            logger.error("AuthMediator: Failed to refresh access token.", exc_info=True)
            raise e

    async def logout_user(self, refresh_token: str = None):
        try:
            logger.info("AuthMediator: Logging out user...")
            
            await self.auth_service.logout(refresh_token)
            
            logger.info("AuthMediator: User logged out successfully.")
            
            return {"message": "Successfully logged out"}
        
        except Exception as e:
            logger.error("AuthMediator: Failed to log out user.", exc_info=True)
            raise e

    async def request_password_reset(self, email: str):
        try:
            logger.info("AuthMediator: Requesting password reset...")
            
            await self.auth_service.request_password_reset(email)
            
            logger.info("AuthMediator: Password reset requested successfully.")
            
            return {"message": "Password reset requested successfully"}
        
        except Exception as e:
            logger.error("AuthMediator: Failed to request password reset.", exc_info=True)
            raise e

    async def reset_password(self, token: str, new_password: str):
        try:
            logger.info("AuthMediator: Resetting password...")
            
            await self.auth_service.reset_password(token, new_password)
            
            logger.info("AuthMediator: Password reset successfully.")
            
            return {"message": "Password reset successfully"}
        
        except Exception as e:
            logger.error("AuthMediator: Failed to reset password.", exc_info=True)
            raise e