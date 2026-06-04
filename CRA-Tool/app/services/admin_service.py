"""
Admin API business logic.
"""

import shutil
from uuid import UUID

from pathlib import Path

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.pagination import PaginationParams
from app.db.models.assessment import Assessment
from app.db.models.assessment_artifact import AssessmentArtifact
from app.db.models.assessment_event import AssessmentEvent
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_job import AssessmentJob
from app.db.models.assessment_parameter import AssessmentParameter
from app.db.models.assessment_recommendation import AssessmentRecommendation
from app.db.models.assessment_report import AssessmentReport
from app.db.models.assessment_rule import AssessmentRule
from app.db.models.audit_log import AuditLog
from app.schemas.admin import RuleUpdateRequest


REPORT_ROOT = Path("storage/reports")
ARTIFACT_ROOT = Path("artifacts")


async def list_parameters(
    db: AsyncSession,
    *,
    pagination: PaginationParams,
) -> list[AssessmentParameter]:
    result = await db.execute(
        select(AssessmentParameter)
        .offset(pagination.resolved_offset)
        .limit(pagination.limit)
    )
    return list(result.scalars().all())


async def upsert_parameter_rule(
    db: AsyncSession,
    *,
    parameter_id: UUID,
    payload: RuleUpdateRequest,
) -> AssessmentRule:
    parameter = await db.get(AssessmentParameter, parameter_id)
    if parameter is None:
        raise NotFoundException("Assessment parameter not found")

    result = await db.execute(
        select(AssessmentRule).where(AssessmentRule.parameter_id == parameter_id)
    )
    rule = result.scalars().first()
    if rule is None:
        rule = AssessmentRule(parameter_id=parameter_id, **payload.model_dump())
        db.add(rule)
    else:
        for key, value in payload.model_dump().items():
            setattr(rule, key, value)
    await db.commit()
    await db.refresh(rule)
    return rule


async def reset_tenant_assessment_data(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> dict:
    assessment_ids = list(
        (
            await db.execute(
                select(Assessment.id).where(Assessment.tenant_id == tenant_id)
            )
        ).scalars().all()
    )

    result = {
        "tenant_id": tenant_id,
        "assessments_deleted": 0,
        "jobs_deleted": 0,
        "events_deleted": 0,
        "findings_deleted": 0,
        "recommendations_deleted": 0,
        "artifacts_deleted": 0,
        "reports_deleted": 0,
        "assessment_audit_logs_deleted": 0,
        "report_files_deleted": 0,
        "artifact_directories_deleted": 0,
        "status": "success",
    }

    if not assessment_ids:
        return result

    report_paths = list(
        (
            await db.execute(
                select(AssessmentReport.storage_path).where(
                    AssessmentReport.assessment_id.in_(assessment_ids)
                )
            )
        ).scalars().all()
    )

    counts = {
        "assessments_deleted": select(func.count()).select_from(Assessment).where(
            Assessment.id.in_(assessment_ids)
        ),
        "jobs_deleted": select(func.count()).select_from(AssessmentJob).where(
            AssessmentJob.assessment_id.in_(assessment_ids)
        ),
        "events_deleted": select(func.count()).select_from(AssessmentEvent).where(
            AssessmentEvent.assessment_id.in_(assessment_ids)
        ),
        "findings_deleted": select(func.count()).select_from(AssessmentFinding).where(
            AssessmentFinding.assessment_id.in_(assessment_ids)
        ),
        "recommendations_deleted": select(func.count()).select_from(AssessmentRecommendation).where(
            AssessmentRecommendation.assessment_id.in_(assessment_ids)
        ),
        "artifacts_deleted": select(func.count()).select_from(AssessmentArtifact).where(
            AssessmentArtifact.assessment_id.in_(assessment_ids)
        ),
        "reports_deleted": select(func.count()).select_from(AssessmentReport).where(
            AssessmentReport.assessment_id.in_(assessment_ids)
        ),
        "assessment_audit_logs_deleted": select(func.count()).select_from(AuditLog).where(
            _assessment_audit_log_filter(tenant_id)
        ),
    }
    for key, statement in counts.items():
        result[key] = int(await db.scalar(statement) or 0)

    await db.execute(
        delete(AssessmentReport).where(AssessmentReport.assessment_id.in_(assessment_ids))
    )
    await db.execute(
        delete(AssessmentArtifact).where(AssessmentArtifact.assessment_id.in_(assessment_ids))
    )
    await db.execute(
        delete(AssessmentRecommendation).where(
            AssessmentRecommendation.assessment_id.in_(assessment_ids)
        )
    )
    await db.execute(
        delete(AssessmentFinding).where(AssessmentFinding.assessment_id.in_(assessment_ids))
    )
    await db.execute(
        delete(AssessmentEvent).where(AssessmentEvent.assessment_id.in_(assessment_ids))
    )
    await db.execute(
        delete(AssessmentJob).where(AssessmentJob.assessment_id.in_(assessment_ids))
    )
    await db.execute(delete(AuditLog).where(_assessment_audit_log_filter(tenant_id)))
    await db.execute(delete(Assessment).where(Assessment.id.in_(assessment_ids)))
    await db.commit()

    result["report_files_deleted"] = _delete_report_files(report_paths)
    result["artifact_directories_deleted"] = _delete_artifact_directories(assessment_ids)
    return result


def _assessment_audit_log_filter(tenant_id: str):
    return (
        (AuditLog.tenant_id == tenant_id)
        & or_(
            AuditLog.resource == "assessments",
            AuditLog.action.like("assessment.%"),
            AuditLog.event_type.like("ASSESSMENT_%"),
        )
    )


def _safe_delete_path(path: Path, *, root: Path) -> bool:
    root_resolved = root.resolve()
    target = path.resolve()
    if root_resolved not in target.parents and target != root_resolved:
        return False
    if target.is_dir():
        shutil.rmtree(target)
        return True
    if target.is_file():
        target.unlink()
        return True
    return False


def _delete_report_files(paths: list[str | None]) -> int:
    deleted = 0
    for item in paths:
        if not item:
            continue
        path = Path(item)
        if not path.is_absolute():
            path = Path.cwd() / path
        if _safe_delete_path(path, root=Path.cwd() / REPORT_ROOT):
            deleted += 1
    return deleted


def _delete_artifact_directories(assessment_ids: list[UUID]) -> int:
    deleted = 0
    for assessment_id in assessment_ids:
        directory = Path.cwd() / ARTIFACT_ROOT / str(assessment_id)
        if _safe_delete_path(directory, root=Path.cwd() / ARTIFACT_ROOT):
            deleted += 1
    return deleted
