from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger

logger = get_logger(__name__)

class AuthController:
    @inject
    def __init__(self, auth_mediator = Provide["auth_mediator"]):
        self.auth_mediator = auth_mediator

    async def register(self, user_data):
        try:
            logger.info("AuthController: Registering user...")
            
            user = await self.auth_mediator.register_user(user_data)
            
            logger.info("AuthController: Registered user successfully.")

            return user 

        except Exception as e:
            logger.error("AuthController: Failed to register user.", exc_info=True)
            raise e

    async def login(self, login_data):
        try:
            logger.info("AuthController: Logging in user...")
            
            user = await self.auth_mediator.authenticate_user(
                login_data.email,
                login_data.password
            )
            
            logger.info("AuthController: User logged in successfully.")
            
            return user

        except Exception as e:
            logger.error("AuthController: Failed to log in user.", exc_info=True)
            raise e

    async def refresh_token(self, refresh_token_data):
        try:
            logger.info("AuthController: Refreshing access token...")
            
            access_token = await self.auth_mediator.refresh_access_token(refresh_token_data.refresh_token)
            
            logger.info("AuthController: Access token refreshed successfully.")
            
            return access_token

        except Exception as e:
            logger.error("AuthController: Failed to refresh access token.", exc_info=True)
            raise e

    async def logout(self, logout_data):
        try:
            logger.info("AuthController: Logging out user...")
            
            await self.auth_mediator.logout_user(logout_data.refresh_token)
            
            logger.info("AuthController: User logged out successfully.")
            
            return {"message": "Successfully logged out"}

        except Exception as e:
            logger.error("AuthController: Failed to log out user.", exc_info=True)
            raise e

    async def request_password_reset(self, request_data):
        try:
            logger.info("AuthController: Requesting password reset...")
            
            await self.auth_mediator.request_password_reset(request_data.email)
            
            logger.info("AuthController: Password reset requested successfully.")
            
            return {"message": "Password reset requested successfully"}

        except Exception as e:
            logger.error("AuthController: Failed to request password reset.", exc_info=True)
            raise e

    async def reset_password(self, reset_data):
        try:
            logger.info("AuthController: Resetting password...")
            
            await self.auth_mediator.reset_password(reset_data.token, reset_data.new_password)
            
            logger.info("AuthController: Password reset successfully.")
            
            return {"message": "Password reset successfully"}

        except Exception as e:
            logger.error("AuthController: Failed to reset password.", exc_info=True)
            raise e

