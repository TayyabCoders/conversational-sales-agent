from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide

from app.di.container import container
from app.schemas.user_schema import UserCreate, User as UserSchema, LoginRequest
from app.schemas.auth_schema import (
    TokenResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    LogoutRequest,
    RequestPasswordResetRequest,
    RequestPasswordResetResponse,
    ResetPasswordRequest,
    ResetPasswordResponse
)
from app.edge.http.controller.auth_controller import AuthController

router = APIRouter()

@router.post("/register", status_code=201, response_model=UserSchema)
@inject
async def register_user(
    user_data: UserCreate,
    controller: AuthController = Depends(Provide["auth_controller"]),
):
    return await controller.register(user_data)


@router.post("/login", response_model=TokenResponse)
@inject
async def login_user(
    login_data: LoginRequest,
    controller: AuthController = Depends(Provide["auth_controller"]),
):
    return await controller.login(login_data)


@router.post("/refresh", response_model=RefreshTokenResponse)
@inject
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    controller: AuthController = Depends(Provide["auth_controller"]),
):
    """
    Refresh access token using a valid refresh token.
    """
    return await controller.refresh_token(refresh_data)


@router.post("/logout")
@inject
async def logout(
    logout_data: LogoutRequest,
    controller: AuthController = Depends(Provide["auth_controller"]),
):
    """
    Logout user and optionally revoke refresh token.
    """
    return await controller.logout(logout_data)


@router.post("/password-reset/request", response_model=RequestPasswordResetResponse)
@inject
async def request_password_reset(
    request_data: RequestPasswordResetRequest,
    controller: AuthController = Depends(Provide["auth_controller"]),
):
    """
    Request a password reset. Sends a reset token to the user's email.
    """
    return await controller.request_password_reset(request_data)


@router.post("/password-reset/confirm", response_model=ResetPasswordResponse)
@inject
async def reset_password(
    reset_data: ResetPasswordRequest,
    controller: AuthController = Depends(Provide["auth_controller"]),
):
    """
    Reset password using a valid reset token.
    """
    return await controller.reset_password(reset_data)