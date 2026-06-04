"""
API dependency helpers.
"""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    get_current_active_user,
    get_current_tenant_id,
    get_validated_tenant_id,
    require_roles,
)
from app.db.models.user import User, UserRole
from app.db.session import get_db


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


CurrentUser = Depends(get_current_active_user)
CurrentTenant = Depends(get_current_tenant_id)
ValidatedTenant = Depends(get_validated_tenant_id)
DatabaseSession = Depends(get_db)


def admin_required(user: User = Depends(require_roles(UserRole.ADMIN))) -> User:
    return user


__all__ = [
    "AsyncSession",
    "CurrentUser",
    "CurrentTenant",
    "DatabaseSession",
    "ValidatedTenant",
    "admin_required",
    "get_request_id",
]
