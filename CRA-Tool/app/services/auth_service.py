"""
Microsoft authentication business logic.

Flow: validate Microsoft ID token → upsert user → issue CRA JWT pair.
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.microsoft import MicrosoftTokenValidationError, validate_microsoft_id_token
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_refresh_token,
)
from app.db.models.refresh_token import RefreshToken
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User, UserRole
from app.db.models.user_session import UserSession
from app.schemas.auth_schema import (
    MessageResponse,
    MicrosoftLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
)
from app.services.audit_service import AuditEvent, audit_service
from app.utils.logger import logger


def _get_connected_tenants(user: User) -> list[str]:
    """Tenant IDs for JWT claim — primary + linked tenants."""
    tenants = {user.microsoft_tid}
    return sorted(tenants)


def _issue_tokens(user: User) -> TokenResponse:
    connected = _get_connected_tenants(user)
    access = create_access_token(
        sub=str(user.id),
        tid=user.microsoft_tid,
        email=user.email,
        role=user.role,
        connected_tenants=connected,
    )
    refresh = create_refresh_token(sub=str(user.id), tid=user.microsoft_tid)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def _upsert_user_from_microsoft(db: AsyncSession, claims) -> User:
    """Create or update user from validated Microsoft claims."""
    now = datetime.now(timezone.utc)
    
    result = await db.execute(
        select(User).where(
            User.microsoft_oid == claims.oid,
            User.microsoft_tid == claims.tid,
        )
    )
    user = result.scalars().first()

    if user is None:
        user = User(
            microsoft_oid=claims.oid,
            microsoft_tid=claims.tid,
            email=claims.email,
            display_name=claims.name or claims.email,
            role=UserRole.USER.value,
            is_active=True,
            last_login=now,
        )
        db.add(user)
        await db.flush()

        # Add tenant if not exists
        tenant_res = await db.execute(
            select(ConnectedTenant).where(ConnectedTenant.tenant_id == claims.tid)
        )
        tenant = tenant_res.scalars().first()
        if not tenant:
            db.add(ConnectedTenant(tenant_id=claims.tid, tenant_name=claims.tid))
            await audit_service.log_event(
                db,
                tenant_id=claims.tid,
                event=AuditEvent.TENANT_CONNECTED,
                action="tenant.connected",
                user_id=user.id,
                resource="connected_tenants",
            )
            
        logger.info("New CRA user from Microsoft login: oid=%s tid=%s", claims.oid, claims.tid)
    else:
        user.email = claims.email
        user.display_name = claims.name or user.display_name
        user.last_login = now
        logger.info("Existing user login: id=%s", user.id)

    await db.commit()
    await db.refresh(user)
    return user


async def _revoke_jti(db: AsyncSession, jti: str, expires_at: datetime) -> None:
    result = await db.execute(select(UserSession).where(UserSession.jwt_jti == jti))
    session = result.scalars().first()
    if not session:
        return
    session.revoked_at = datetime.now(timezone.utc)
    await db.commit()


async def is_token_revoked(db: AsyncSession, jti: str | None) -> bool:
    if not jti:
        return False
    result = await db.execute(select(UserSession).where(UserSession.jwt_jti == jti))
    session = result.scalars().first()
    return session is not None and session.revoked_at is not None


async def login_with_microsoft(db: AsyncSession, body: MicrosoftLoginRequest) -> TokenResponse:
    """POST /auth/login — validate Microsoft ID token and return CRA JWTs."""
    try:
        claims = validate_microsoft_id_token(body.id_token)
    except MicrosoftTokenValidationError as exc:
        await audit_service.log_event(
            db,
            tenant_id="unknown",
            event=AuditEvent.LOGIN_FAILURE,
            action="auth.login_failed",
            metadata={"reason": str(exc)},
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await _upsert_user_from_microsoft(db, claims)

    if not user.is_active:
        await audit_service.log_event(
            db,
            tenant_id=user.microsoft_tid,
            event=AuditEvent.LOGIN_FAILURE,
            action="auth.login_failed",
            user_id=user.id,
            metadata={"reason": "inactive_user"},
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    tokens = _issue_tokens(user)
    
    # Store user session and refresh token
    access_payload = decode_access_token(tokens.access_token)
    refresh_payload = decode_refresh_token(tokens.refresh_token)
    
    if access_payload and refresh_payload:
        db.add(UserSession(
            user_id=user.id,
            jwt_jti=access_payload["jti"],
            expires_at=datetime.fromtimestamp(access_payload["exp"], tz=timezone.utc)
        ))
        db.add(RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(tokens.refresh_token),
            expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        ))
        await audit_service.log_event(
            db,
            tenant_id=user.microsoft_tid,
            event=AuditEvent.LOGIN_SUCCESS,
            action="auth.login",
            user_id=user.id,
            resource="users",
        )
        await db.commit()

    return tokens


async def refresh_access_token(db: AsyncSession, body: RefreshTokenRequest) -> TokenResponse:
    """POST /auth/refresh — exchange valid refresh token for new CRA token pair."""
    payload = decode_refresh_token(body.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    token_hash = hash_refresh_token(body.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored_token = result.scalars().first()
    
    if not stored_token or stored_token.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    stored_token.revoked = True

    tokens = _issue_tokens(user)
    
    access_payload = decode_access_token(tokens.access_token)
    refresh_payload = decode_refresh_token(tokens.refresh_token)
    
    if access_payload and refresh_payload:
        db.add(UserSession(
            user_id=user.id,
            jwt_jti=access_payload["jti"],
            expires_at=datetime.fromtimestamp(access_payload["exp"], tz=timezone.utc)
        ))
        db.add(RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(tokens.refresh_token),
            expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        ))
        await audit_service.log_event(
            db,
            tenant_id=user.microsoft_tid,
            event=AuditEvent.TOKEN_REFRESH,
            action="auth.refresh",
            user_id=user.id,
            resource="refresh_tokens",
        )
        await db.commit()
        
    return tokens


async def logout_user(
    db: AsyncSession,
    access_payload: dict | None,
    body_refresh_token: str | None,
) -> MessageResponse:
    """POST /auth/logout — revoke access + refresh token JTIs."""
    revoked = 0

    if access_payload:
        jti = access_payload.get("jti")
        if jti:
            result = await db.execute(select(UserSession).where(UserSession.jwt_jti == jti))
            session = result.scalars().first()
            if session:
                session.revoked_at = datetime.now(timezone.utc)
                revoked += 1
                await audit_service.log_event(
                    db,
                    tenant_id=access_payload.get("tid", "unknown"),
                    event=AuditEvent.SESSION_REVOKED,
                    action="auth.session_revoked",
                    user_id=session.user_id,
                    resource="user_sessions",
                )

    if body_refresh_token:
        refresh_payload = decode_refresh_token(body_refresh_token)
        if refresh_payload:
            result = await db.execute(
                select(RefreshToken).where(
                    RefreshToken.token_hash == hash_refresh_token(body_refresh_token)
                )
            )
            rt = result.scalars().first()
            if rt:
                rt.revoked = True
                revoked += 1
    await audit_service.log_event(
        db,
        tenant_id=(access_payload or {}).get("tid", "unknown"),
        event=AuditEvent.LOGOUT,
        action="auth.logout",
        user_id=uuid.UUID(access_payload["sub"]) if access_payload and access_payload.get("sub") else None,
        resource="users",
        metadata={"revoked_tokens": revoked},
    )
                    
    await db.commit()

    logger.info("Logout completed — revoked %s token(s)", revoked)
    return MessageResponse(message="Logged out successfully")


def get_user_profile(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        microsoft_oid=user.microsoft_oid,
        microsoft_tid=user.microsoft_tid,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        connected_tenants=_get_connected_tenants(user),
        created_at=user.created_at,
        last_login=user.last_login,
    )
