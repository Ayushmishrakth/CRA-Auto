import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, decode_refresh_token, hash_refresh_token
from app.db.models.assessment import Assessment
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_parameter import AssessmentParameter
from app.db.models.assessment_rule import AssessmentRule
from app.db.models.audit_log import AuditLog
from app.db.models.refresh_token import RefreshToken
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User, UserRole
from app.db.models.user_session import UserSession
from app.db.repositories.base_repository import BaseRepository, TenantScopedRepository
from app.schemas.auth_schema import RefreshTokenRequest
from app.services.audit_service import AuditEvent
from app.services import auth_service


async def _seed_user(db: AsyncSession, tenant_id: str) -> User:
    user = User(
        microsoft_oid=str(uuid.uuid4()),
        microsoft_tid=tenant_id,
        email="assessor@example.com",
        display_name="Assessment User",
        role=UserRole.USER.value,
        is_active=True,
        last_login=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def test_phase4_metadata_contains_expected_tables(db_session: AsyncSession):
    def table_names(sync_conn):
        bind = sync_conn.get_bind()
        return set(inspect(bind).get_table_names())

    names = await db_session.run_sync(table_names)
    assert {
        "users",
        "connected_tenants",
        "user_sessions",
        "refresh_tokens",
        "assessments",
        "assessment_findings",
        "assessment_parameters",
        "assessment_rules",
        "audit_logs",
    }.issubset(names)


async def test_user_unique_identity_constraint(db_session: AsyncSession, tenant_id: str):
    user = await _seed_user(db_session, tenant_id)
    db_session.add(
        User(
            microsoft_oid=user.microsoft_oid,
            microsoft_tid=user.microsoft_tid,
            email="duplicate@example.com",
            display_name="Duplicate",
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_auth_token_persistence_and_revocation(db_session: AsyncSession, tenant_id: str):
    user = await _seed_user(db_session, tenant_id)
    tokens = auth_service._issue_tokens(user)
    access_payload = decode_access_token(tokens.access_token)
    refresh_payload = decode_refresh_token(tokens.refresh_token)

    db_session.add(
        UserSession(
            user_id=user.id,
            jwt_jti=access_payload["jti"],
            expires_at=datetime.fromtimestamp(access_payload["exp"], tz=timezone.utc),
        )
    )
    db_session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(tokens.refresh_token),
            expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
        )
    )
    await db_session.commit()

    assert await auth_service.is_token_revoked(db_session, access_payload["jti"]) is False
    logout_response = await auth_service.logout_user(
        db_session,
        access_payload,
        tokens.refresh_token,
    )
    assert logout_response.message == "Logged out successfully"
    assert await auth_service.is_token_revoked(db_session, access_payload["jti"]) is True

    stored_refresh = (
        await db_session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(tokens.refresh_token)
            )
        )
    ).scalars().one()
    assert stored_refresh.revoked is True

    assert stored_refresh.token_hash != refresh_payload["jti"]
    assert stored_refresh.token_hash != tokens.refresh_token
    audit_events = (
        await db_session.execute(select(AuditLog.event_type).order_by(AuditLog.created_at))
    ).scalars().all()
    assert AuditEvent.LOGOUT.value in audit_events
    assert AuditEvent.SESSION_REVOKED.value in audit_events


async def test_refresh_token_rotation_uses_hashed_storage(
    db_session: AsyncSession, tenant_id: str
):
    user = await _seed_user(db_session, tenant_id)
    tokens = auth_service._issue_tokens(user)
    refresh_payload = decode_refresh_token(tokens.refresh_token)
    db_session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(tokens.refresh_token),
            expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
        )
    )
    await db_session.commit()

    rotated = await auth_service.refresh_access_token(
        db_session,
        RefreshTokenRequest(refresh_token=tokens.refresh_token),
    )

    old_token = (
        await db_session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(tokens.refresh_token)
            )
        )
    ).scalars().one()
    new_token_hash = hash_refresh_token(rotated.refresh_token)
    new_token = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == new_token_hash)
        )
    ).scalars().one()
    audit_events = (await db_session.execute(select(AuditLog.event_type))).scalars().all()

    assert old_token.revoked is True
    assert new_token.revoked is False
    assert new_token.token_hash != rotated.refresh_token
    assert AuditEvent.TOKEN_REFRESH.value in audit_events


async def test_assessment_relationships_and_findings(db_session: AsyncSession, tenant_id: str):
    user = await _seed_user(db_session, tenant_id)
    parameter = AssessmentParameter(
        parameter_key="mfa_enabled",
        parameter_name="MFA Enabled",
        category="identity",
        collection_method="graph",
    )
    db_session.add(parameter)
    await db_session.flush()

    rule = AssessmentRule(
        parameter_id=parameter.id,
        rule_type="boolean",
        severity="high",
        scoring_weight=1.0,
    )
    assessment = Assessment(
        tenant_id=tenant_id,
        triggered_by_user_id=user.id,
        status="running",
        progress_pct=25.0,
    )
    db_session.add_all([rule, assessment])
    await db_session.flush()

    finding = AssessmentFinding(
        assessment_id=assessment.id,
        parameter_id=parameter.id,
        rule_id=rule.id,
        status="warning",
        raw_value={"enabled": False},
        severity="high",
    )
    db_session.add(finding)
    await db_session.commit()
    db_session.expunge_all()

    stored = await db_session.get(Assessment, assessment.id)
    assert stored.tenant_id == tenant_id
    assert len(stored.findings) == 1
    assert stored.findings[0].parameter_id == parameter.id


async def test_assessment_findings_lazy_load_is_async_safe(
    db_session: AsyncSession, tenant_id: str
):
    user = await _seed_user(db_session, tenant_id)
    parameter = AssessmentParameter(
        parameter_key="lazy_mfa_enabled",
        parameter_name="Lazy MFA Enabled",
        category="identity",
        collection_method="graph",
    )
    assessment = Assessment(
        tenant_id=tenant_id,
        triggered_by_user_id=user.id,
        status="running",
        progress_pct=25.0,
    )
    db_session.add_all([parameter, assessment])
    await db_session.flush()
    db_session.add(
        AssessmentFinding(
            assessment_id=assessment.id,
            parameter_id=parameter.id,
            status="warning",
        )
    )
    await db_session.commit()
    db_session.expunge_all()

    stored = await db_session.get(Assessment, assessment.id)
    assert len(stored.findings) == 1


async def test_base_repository_crud_uses_async_session(db_session: AsyncSession, tenant_id: str):
    repo = BaseRepository(ConnectedTenant)
    tenant = await repo.create(
        db_session,
        obj_in={"tenant_id": tenant_id, "tenant_name": "Tenant A"},
    )

    fetched = await repo.get(db_session, tenant.id)
    assert fetched.tenant_id == tenant_id

    all_tenants = await repo.get_all(db_session)
    assert [item.tenant_id for item in all_tenants] == [tenant_id]

    updated = await repo.update(db_session, db_obj=tenant, obj_in={"tenant_name": "Tenant B"})
    assert updated.tenant_name == "Tenant B"

    deleted = await repo.delete(db_session, id=tenant.id)
    assert deleted.id == tenant.id
    assert await repo.get(db_session, tenant.id) is None


async def test_tenant_scoped_repository_prevents_cross_tenant_reads(db_session: AsyncSession):
    repo = BaseRepository(Assessment)
    tenant_repo = TenantScopedRepository(Assessment)
    user_a = await _seed_user(db_session, "tenant-a")
    user_b = await _seed_user(db_session, "tenant-b")
    db_session.add_all(
        [
            Assessment(
                tenant_id="tenant-a",
                triggered_by_user_id=user_a.id,
                status="queued",
                progress_pct=0.0,
            ),
            Assessment(
                tenant_id="tenant-b",
                triggered_by_user_id=user_b.id,
                status="queued",
                progress_pct=0.0,
            ),
        ]
    )
    await db_session.commit()

    results = await repo.get_all(db_session)
    assert {assessment.tenant_id for assessment in results} == {"tenant-a", "tenant-b"}

    tenant_a_results = await tenant_repo.get_all_for_tenant(db_session, tenant_id="tenant-a")
    assert [assessment.tenant_id for assessment in tenant_a_results] == ["tenant-a"]


async def test_audit_log_default_timestamp(db_session: AsyncSession, tenant_id: str):
    audit = AuditLog(
        tenant_id=tenant_id,
        event_type="auth",
        action="login",
    )
    db_session.add(audit)
    await db_session.commit()
    assert audit.created_at.tzinfo is not None
