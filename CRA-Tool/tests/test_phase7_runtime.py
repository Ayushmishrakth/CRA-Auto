import asyncio
import uuid
from datetime import datetime, timezone

from httpx import AsyncClient
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.core.celery_app import celery_app
from app.db.models.assessment import Assessment
from app.db.models.assessment_event import AssessmentEvent
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_job import AssessmentJob
from app.db.models.assessment_report import AssessmentReport
from app.db.models.assessment_recommendation import AssessmentRecommendation
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User
from app.services import event_bus
from app.services import runtime_assessment_service
from app.services import runtime_recommendation_service
from app.services import runtime_scoring_service
from app.services.registry_service import get_registry
from app.tasks.assessment_tasks import run_assessment_task


class _NoCloseSessionContext:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _SmallRegistry:
    def __init__(self, size: int = 8):
        original = get_registry()
        keys = {item["parameter_key"] for item in original.get_parameters()[:size]}
        self.parameters = [item for item in original.get_parameters() if item["parameter_key"] in keys]
        self.rules = [item for item in original.get_rules() if item["parameter_key"] in keys]
        self.collectors = [item for item in original.get_collectors() if item["parameter_key"] in keys]
        self.recommendations = [
            item for item in original.get_recommendations() if item["parameter_key"] in keys
        ]
        self.scoring = original.get_scoring_config()
        self._parameters = {item["parameter_key"]: item for item in self.parameters}
        self._rules = {item["parameter_key"]: item for item in self.rules}
        self._collectors = {item["parameter_key"]: item for item in self.collectors}
        self._recommendations = {item["parameter_key"]: item for item in self.recommendations}

    def get_parameters(self):
        return self.parameters

    def get_rules(self):
        return self.rules

    def get_collectors(self):
        return self.collectors

    def get_recommendations(self):
        return self.recommendations

    def get_scoring_config(self):
        return self.scoring

    def get_parameter_by_key(self, parameter_key):
        return self._parameters.get(parameter_key)

    def get_rule_by_key(self, parameter_key):
        return self._rules.get(parameter_key)

    def get_collector_by_key(self, parameter_key):
        return self._collectors.get(parameter_key)

    def get_recommendation_by_key(self, parameter_key):
        return self._recommendations.get(parameter_key)


class _SuccessfulPowerShellEngine:
    class _Resolver:
        @staticmethod
        def get_manifest_entry(parameter_key):
            return {"supports_powershell": True, "supports_graph": False}

    resolver = _Resolver()

    async def run_collector(self, *, tenant_id, parameter, collector, assessment_id=None, environment=None):
        return {
            "parameter_key": parameter["parameter_key"],
            "status": "fail",
            "severity": parameter.get("severity") or "medium",
            "raw_value": {
                "parameter_key": parameter["parameter_key"],
                "powershell": True,
                "execution": {"duration_ms": 1, "attempts": 1, "retries": 0},
            },
            "evaluated_value": "Valid collector evidence was evaluated",
            "score_contribution": 1.0,
            "warnings": [],
            "errors": [],
            "telemetry": {"duration_ms": 1, "attempts": 1, "retries": 0},
        }


@pytest.fixture
def runtime_session(monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession):
    def session_local() -> _NoCloseSessionContext:
        return _NoCloseSessionContext(db_session)

    async def noop_publish(payload: dict) -> None:
        return None

    monkeypatch.setattr(runtime_assessment_service, "AsyncSessionLocal", session_local)
    monkeypatch.setattr(event_bus, "publish_event", noop_publish)
    small_registry = _SmallRegistry()
    monkeypatch.setattr(runtime_assessment_service, "get_registry", lambda: small_registry)
    monkeypatch.setattr(runtime_scoring_service, "get_registry", lambda: small_registry)
    monkeypatch.setattr(runtime_recommendation_service, "get_registry", lambda: small_registry)
    monkeypatch.setattr(runtime_assessment_service, "GRAPH_COLLECTORS", {})
    monkeypatch.setattr(runtime_assessment_service, "PowerShellExecutionEngine", _SuccessfulPowerShellEngine)


async def _create_job(
    db_session: AsyncSession,
    *,
    tenant_id: str,
    user_id,
) -> AssessmentJob:
    assessment = Assessment(
        tenant_id=tenant_id,
        triggered_by_user_id=user_id,
        status="queued",
        progress_pct=0.0,
    )
    db_session.add(assessment)
    await db_session.flush()
    job = AssessmentJob(
        assessment_id=assessment.id,
        tenant_id=tenant_id,
        status="queued",
        current_stage="queued",
        progress_pct=0.0,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


def test_phase7_registry_loads_runtime_json():
    registry = get_registry()
    parameters = registry.get_parameters()
    assert parameters
    first_key = parameters[0]["parameter_key"]
    assert registry.get_parameter_by_key(first_key)
    assert registry.get_rule_by_key(first_key)
    assert registry.get_collector_by_key(first_key)
    assert registry.get_recommendation_by_key(first_key)
    assert "domain_weights" in registry.get_scoring_config()


def test_phase7_celery_task_registered():
    assert "assessment.run" in celery_app.tasks
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]


def test_phase7_celery_task_executes_runtime(tmp_path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "celery-runtime.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    small_registry = _SmallRegistry(size=3)

    async def noop_publish(payload: dict) -> None:
        return None

    monkeypatch.setattr(runtime_assessment_service, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(event_bus, "publish_event", noop_publish)
    monkeypatch.setattr(runtime_assessment_service, "get_registry", lambda: small_registry)
    monkeypatch.setattr(runtime_scoring_service, "get_registry", lambda: small_registry)
    monkeypatch.setattr(runtime_recommendation_service, "get_registry", lambda: small_registry)
    monkeypatch.setattr(runtime_assessment_service, "GRAPH_COLLECTORS", {})
    monkeypatch.setattr(runtime_assessment_service, "PowerShellExecutionEngine", _SuccessfulPowerShellEngine)

    async def setup() -> str:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            user = User(
                microsoft_oid=str(uuid.uuid4()),
                microsoft_tid="tenant-celery",
                email="celery@example.com",
                display_name="Celery User",
                is_active=True,
                last_login=datetime.now(timezone.utc),
            )
            tenant = ConnectedTenant(
                tenant_id="tenant-celery",
                tenant_name="Celery Tenant",
                consent_status="connected",
                deployment_status="ACTIVE",
                status="ACTIVE",
            )
            session.add_all([user, tenant])
            await session.flush()
            job = await _create_job(
                session,
                tenant_id="tenant-celery",
                user_id=user.id,
            )
            return str(job.id)

    async def verify(job_id: str) -> None:
        async with session_factory() as session:
            job = await session.get(AssessmentJob, uuid.UUID(job_id))
            assessment = await session.get(Assessment, job.assessment_id)
            assert job.status == "completed"
            assert assessment.status == "completed"
            assert assessment.total_findings > 0
        await engine.dispose()

    job_id = asyncio.run(setup())
    result = run_assessment_task.apply(args=[job_id])
    assert result.successful()
    assert result.result["status"] == "completed"
    asyncio.run(verify(job_id))


async def test_phase7_runtime_lifecycle_persists_findings_scores_recommendations_and_events(
    db_session: AsyncSession,
    auth_context: dict,
    runtime_session,
):
    job = await _create_job(
        db_session,
        tenant_id=auth_context["tenant"].tenant_id,
        user_id=auth_context["user"].id,
    )

    result = await runtime_assessment_service.run_assessment_job(
        str(job.id),
        worker_id="test-worker",
    )

    assert result["status"] == "completed"
    stored_job = await db_session.get(AssessmentJob, job.id)
    stored_assessment = await db_session.get(Assessment, job.assessment_id)
    assert stored_job.status == "completed"
    assert stored_job.current_stage == "completed"
    assert stored_job.progress_pct == 100
    assert stored_assessment.status == "completed"
    assert stored_assessment.progress_pct == 100
    assert stored_assessment.overall_score is not None
    assert stored_assessment.total_findings > 0

    findings_count = await db_session.scalar(
        select(func.count()).select_from(AssessmentFinding).where(
            AssessmentFinding.assessment_id == stored_assessment.id
        )
    )
    recommendations_count = await db_session.scalar(
        select(func.count()).select_from(AssessmentRecommendation).where(
            AssessmentRecommendation.assessment_id == stored_assessment.id,
            AssessmentRecommendation.tenant_id == stored_assessment.tenant_id,
        )
    )
    reports_count = await db_session.scalar(
        select(func.count()).select_from(AssessmentReport).where(
            AssessmentReport.assessment_id == stored_assessment.id
        )
    )
    event_types = (
        await db_session.execute(
            select(AssessmentEvent.event_type).where(
                AssessmentEvent.assessment_id == stored_assessment.id,
                AssessmentEvent.tenant_id == stored_assessment.tenant_id,
            )
        )
    ).scalars().all()

    assert findings_count == result["findings"]
    assert recommendations_count == result["recommendations"]
    assert reports_count == 2
    assert "assessment.started" in event_types
    assert "finding.generated" in event_types
    assert "scoring.completed" in event_types
    assert "recommendation.generated" in event_types
    assert "report.generated" in event_types
    assert "assessment.completed" in event_types


async def test_phase7_runtime_preserves_partial_collector_failures(
    db_session: AsyncSession,
    auth_context: dict,
    runtime_session,
    monkeypatch: pytest.MonkeyPatch,
):
    job = await _create_job(
        db_session,
        tenant_id=auth_context["tenant"].tenant_id,
        user_id=auth_context["user"].id,
    )
    state = {"failed": False}

    class FlakyPowerShellEngine:
        class _Resolver:
            @staticmethod
            def get_manifest_entry(parameter_key):
                return {"supports_powershell": True, "supports_graph": False}

        resolver = _Resolver()

        async def run_collector(self, *, tenant_id, parameter, collector, assessment_id=None, environment=None):
            if not state["failed"]:
                state["failed"] = True
                raise RuntimeError("collector unavailable")
            return {
                "parameter_key": parameter["parameter_key"],
                "status": "pass",
                "severity": parameter.get("severity") or "info",
                "raw_value": {
                    "parameter_key": parameter["parameter_key"],
                    "powershell": True,
                    "execution": {"duration_ms": 1, "attempts": 1, "retries": 0},
                },
                "evaluated_value": "PowerShell collector passed",
                "score_contribution": 0.0,
                "warnings": [],
                "errors": [],
                "telemetry": {"duration_ms": 1, "attempts": 1, "retries": 0},
            }

    monkeypatch.setattr(runtime_assessment_service, "PowerShellExecutionEngine", FlakyPowerShellEngine)

    result = await runtime_assessment_service.run_assessment_job(str(job.id), worker_id="test-worker")

    assert result["status"] == "completed"
    event_types = (
        await db_session.execute(
            select(AssessmentEvent.event_type).where(AssessmentEvent.assessment_id == job.assessment_id)
        )
    ).scalars().all()
    assert "collector.failed" in event_types
    assert "assessment.collectors_incomplete" in event_types


async def test_phase7_job_and_event_endpoints_are_tenant_scoped(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
):
    other_assessment = Assessment(
        tenant_id="tenant-b",
        triggered_by_user_id=auth_context["user"].id,
        status="queued",
        progress_pct=0,
    )
    db_session.add(other_assessment)
    await db_session.flush()
    db_session.add(
        AssessmentJob(
            assessment_id=other_assessment.id,
            tenant_id="tenant-b",
            status="queued",
            progress_pct=0,
        )
    )
    db_session.add(
        AssessmentEvent(
            assessment_id=other_assessment.id,
            tenant_id="tenant-b",
            event_type="assessment.started",
            severity="info",
            event_payload={},
        )
    )
    await db_session.commit()

    for path in [
        f"/api/v1/assessments/{other_assessment.id}/job",
        f"/api/v1/assessments/{other_assessment.id}/events",
    ]:
        response = await api_client.get(path, headers=auth_context["headers"])
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_ACCESS_DENIED"
