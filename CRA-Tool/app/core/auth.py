"""
CRA JWT authentication dependencies — protect routes with Bearer tokens.
"""

import uuid
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.services.auth_service import is_token_revoked
from app.utils.logger import logger

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="CRA JWT from POST /auth/login (after Microsoft sign-in)",
    auto_error=False,
)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Missing Bearer token")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        logger.warning("Invalid or expired CRA access token")
        raise _unauthorized("Invalid or expired token")

    if await is_token_revoked(db, payload.get("jti")):
        logger.warning("Revoked CRA access token used")
        raise _unauthorized("Token has been revoked")

    return payload


async def get_current_user(
    payload: dict = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise _unauthorized("Invalid token payload")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise _unauthorized("Invalid user ID format")

    user = await db.get(User, user_id)
    if user is None:
        raise _unauthorized("User not found")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return current_user


def get_current_tenant_id(
    payload: dict = Depends(get_token_payload),
) -> str:
    tid = payload.get("tid")
    if not tid:
        raise _unauthorized("Token missing tenant id")
    return str(tid)


async def get_validated_tenant_id(
    tenant_id: str = Depends(get_current_tenant_id),
    payload: dict = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> str:
    connected_tenants = set(payload.get("connected_tenants") or [])
    if tenant_id not in connected_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not available to the current user",
        )

    result = await db.execute(
        select(ConnectedTenant).where(
            ConnectedTenant.tenant_id == tenant_id,
            ConnectedTenant.status == "ACTIVE",
        )
    )
    if result.scalars().first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not connected or active",
        )
    return tenant_id


def require_roles(*allowed_roles: UserRole) -> Callable:
    allowed = {role.value for role in allowed_roles}

    async def _checker(
        payload: dict = Depends(get_token_payload),
        user: User = Depends(get_current_active_user),
    ) -> User:
        token_role = payload.get("role") or user.role
        if token_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(sorted(allowed))}",
            )
        return user

    return _checker
