"""
Auth endpoints: register, login, refresh, logout, password management.
Rate-limited. All tokens use httpOnly cookies for refresh; Bearer for access.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.core.security import decode_token
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])

_REFRESH_COOKIE = "docuflow_refresh"
_COOKIE_SECURE = settings.is_production
_COOKIE_SAMESITE = "strict" if settings.is_production else "lax"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",  # Scope cookie to auth endpoints only
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AuthService(db)
    auth_response, refresh_token = await svc.register(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        organization_name=body.organization_name,
        ip_address=request.client.host if request.client else None,
    )
    _set_refresh_cookie(response, refresh_token)
    return auth_response


@router.post("/login", response_model=AuthResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AuthService(db)
    auth_response, refresh_token = await svc.login(
        email=body.email,
        password=body.password,
        ip_address=request.client.host if request.client else None,
    )
    _set_refresh_cookie(response, refresh_token)
    return auth_response


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    token = request.cookies.get(_REFRESH_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )
    from jose import JWTError

    try:
        payload = decode_token(token, expected_type="refresh")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    from app.core.security import create_access_token, create_refresh_token
    from app.repositories.user_repository import UserRepository
    from uuid import UUID

    user_id = payload.get("sub")
    repo = UserRepository(db)
    user = await repo.get_by_id(UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    from app.repositories.organization_repository import OrganizationRepository

    org_repo = OrganizationRepository(db)
    memberships = await org_repo.list_user_memberships(user.id)
    default_org_id = str(memberships[0].organization_id) if memberships else None

    new_access = create_access_token(str(user.id), {"org_id": default_org_id} if default_org_id else {})
    new_refresh = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, new_refresh)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=new_access,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=_REFRESH_COOKIE, path="/api/v1/auth")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return UserResponse.model_validate(current_user)


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AuthService(db)
    # Always return success to prevent email enumeration
    await svc.request_password_reset(body.email)
    return {"message": "If an account exists, a reset link has been sent"}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AuthService(db)
    await svc.reset_password(body.token, body.new_password)
    return {"message": "Password reset successfully"}


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AuthService(db)
    await svc.change_password(current_user.id, body.current_password, body.new_password)
    return {"message": "Password changed successfully"}
