"""
CRA internal JWT — issued after successful Microsoft authentication.

Microsoft tokens are validated in core/microsoft.py; CRA tokens secure all API calls.
"""

import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt

from app.core.config import settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    *,
    sub: str,
    tid: str,
    email: str,
    role: str,
    connected_tenants: list[str],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Issue short-lived CRA access JWT for API authorization."""
    expire = _utc_now() + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": sub,
        "tid": tid,
        "email": email,
        "role": role,
        "connected_tenants": connected_tenants,
        "exp": expire,
        "iat": _utc_now(),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(*, sub: str, tid: str) -> str:
    """Issue long-lived CRA refresh JWT for /auth/refresh."""
    expire = _utc_now() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": sub,
        "tid": tid,
        "exp": expire,
        "iat": _utc_now(),
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_cra_token(token: str, expected_type: str) -> Optional[dict[str, Any]]:
    """Decode and verify a CRA JWT; returns None if invalid or wrong type."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    return decode_cra_token(token, "access")


def decode_refresh_token(token: str) -> Optional[dict[str, Any]]:
    return decode_cra_token(token, "refresh")


def hash_refresh_token(token: str) -> str:
    """Store only a deterministic SHA-256 digest of refresh tokens."""
    payload = f"{settings.secret_key}:{token}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
