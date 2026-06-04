import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, decode_access_token
from app.db.base import Base
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User, UserRole
from app.db.models.user_session import UserSession
from app.db.session import get_db
from app.main import app


@pytest.fixture(autouse=True)
def disable_external_celery_enqueue(monkeypatch: pytest.MonkeyPatch):
    class QueuedTask:
        id = "test-celery-task"

    monkeypatch.setattr(
        "app.services.assessment_service.run_assessment_task.apply_async",
        lambda *args, **kwargs: QueuedTask(),
    )


@pytest.fixture
async def db_session(tmp_path: Path) -> AsyncGenerator[AsyncSession, None]:
    db_path = tmp_path / "phase4_test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def tenant_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
async def api_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_context(db_session: AsyncSession, tenant_id: str) -> dict:
    user = User(
        microsoft_oid=str(uuid.uuid4()),
        microsoft_tid=tenant_id,
        email="api-user@example.com",
        display_name="API User",
        role=UserRole.ADMIN.value,
        is_active=True,
        last_login=datetime.now(timezone.utc),
    )
    tenant = ConnectedTenant(
        tenant_id=tenant_id,
        tenant_name="API Tenant",
        consent_status="connected",
        deployment_status="ACTIVE",
        status="ACTIVE",
        granted_permissions=["User.Read.All"],
    )
    db_session.add_all([user, tenant])
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        sub=str(user.id),
        tid=tenant_id,
        email=user.email,
        role=user.role,
        connected_tenants=[tenant_id],
    )
    payload = decode_access_token(token)
    db_session.add(
        UserSession(
            user_id=user.id,
            jwt_jti=payload["jti"],
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
    )
    await db_session.commit()
    return {
        "user": user,
        "tenant": tenant,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }
