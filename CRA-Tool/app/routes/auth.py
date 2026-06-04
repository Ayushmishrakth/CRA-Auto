"""
Microsoft authentication routes (Phase 3 & 4).
"""

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer_scheme, get_current_active_user
from app.core.security import decode_access_token
from app.db.session import get_db
from app.db.models.user import User
from app.schemas.auth_schema import (
    LogoutRequest,
    MessageResponse,
    MicrosoftLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Microsoft login",
)
async def microsoft_login(
    body: MicrosoftLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await auth_service.login_with_microsoft(db, body)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh CRA tokens",
)
async def refresh_tokens(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await auth_service.refresh_access_token(db, body)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout",
)
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> MessageResponse:
    access_payload = None
    if credentials and credentials.scheme.lower() == "bearer":
        access_payload = decode_access_token(credentials.credentials)
    return await auth_service.logout_user(db, access_payload, body.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    return auth_service.get_user_profile(current_user)
