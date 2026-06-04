"""
Health and monitoring business logic.
"""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.health import ComponentHealth, HealthCheckResponse
from app.schemas.health_schema import HealthResponse


def get_health_status() -> HealthResponse:
    return HealthResponse(status="Server Running Successfully")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_system_health() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="healthy",
        timestamp=_now(),
        components={
            "api": ComponentHealth(
                status="healthy",
                details={"app_name": settings.app_name, "version": settings.app_version},
            ),
            "environment": ComponentHealth(
                status="healthy",
                details={"debug": settings.debug, "database_configured": bool(settings.database_url)},
            ),
        },
    )


async def get_db_health(db: AsyncSession) -> ComponentHealth:
    await db.execute(text("select 1"))
    return ComponentHealth(status="healthy", details={"engine": "async", "dialect": "configured"})


async def get_auth_health() -> ComponentHealth:
    return ComponentHealth(
        status="healthy",
        details={
            "algorithm": settings.algorithm,
            "access_token_expire_minutes": settings.access_token_expire_minutes,
            "entra_authority": settings.microsoft_authority,
        },
    )


async def get_migration_health(db: AsyncSession) -> ComponentHealth:
    result = await db.execute(text("select version_num from alembic_version"))
    version = result.scalar_one_or_none()
    return ComponentHealth(status="healthy", details={"alembic_version": version})
