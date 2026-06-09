"""
Service functions for the four new frontend-facing endpoints:
  GET  /api/v1/dashboard/stats
  GET  /api/v1/assessments
  DELETE /api/v1/assessments/{id}
  GET  /api/v1/assessments/{id}/results
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.core.exceptions import NotFoundException
from app.db.models.assessment import Assessment
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_job import AssessmentJob
from app.db.models.assessment_recommendation import AssessmentRecommendation
from app.db.models.assessment_report import AssessmentReport
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User
from app.schemas.dashboard import (
    AssessmentListItemResponse,
    AssessmentListResponse,
    AssessmentResultsResponse,
    AssessmentResultsScores,
    AssessmentResultsSummary,
    DashboardStatsResponse,
    FindingItem,
    FindingsSummary,
    ReadinessTier,
    RecommendationItem,
    ReportStatus,
)


def _readiness_tier(score: float | None, critical_count: int) -> ReadinessTier:
    if score is None:
        return ReadinessTier(
            tier="not_assessed",
            label="Not Assessed",
            copilot_blocking_issues=critical_count,
            description="Assessment has not yet produced a score",
        )
    if score >= 85:
        return ReadinessTier(
            tier="ready",
            label="Ready",
            copilot_blocking_issues=critical_count,
            description="Your tenant meets the baseline for Copilot deployment",
        )
    if score >= 70:
        return ReadinessTier(
            tier="mostly_ready",
            label="Mostly Ready",
            copilot_blocking_issues=critical_count,
            description="Minor remediation recommended before Copilot deployment",
        )
    if score >= 50:
        return ReadinessTier(
            tier="partially_ready",
            label="Partially Ready",
            copilot_blocking_issues=critical_count,
            description="Your tenant needs remediation before Copilot deployment",
        )
    return ReadinessTier(
        tier="not_ready",
        label="Not Ready",
        copilot_blocking_issues=critical_count,
        description="Significant issues must be resolved before Copilot deployment",
    )


async def get_dashboard_stats(
    db: AsyncSession,
    *,
    current_user: User,
) -> DashboardStatsResponse:
    tenant_id = current_user.microsoft_tid

    row = (
        await db.execute(
            select(
                func.count().label("total"),
                func.count().filter(Assessment.status == "completed").label("completed"),
                func.count()
                .filter(Assessment.status.in_(["queued", "running"]))
                .label("in_progress"),
                func.count().filter(Assessment.status == "failed").label("failed"),
                func.avg(Assessment.overall_score).label("avg_score"),
                func.max(Assessment.created_at).label("last_date"),
            ).where(
                Assessment.tenant_id == tenant_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).one()

    ct_count = (
        await db.scalar(
            select(func.count()).where(ConnectedTenant.status == "ACTIVE")
        )
    ) or 0

    return DashboardStatsResponse(
        total_assessments=row.total or 0,
        completed_assessments=row.completed or 0,
        in_progress_assessments=row.in_progress or 0,
        failed_assessments=row.failed or 0,
        connected_tenants=ct_count,
        average_score=round(float(row.avg_score or 0.0), 1),
        last_assessment_date=row.last_date,
    )


async def list_assessments(
    db: AsyncSession,
    *,
    current_user: User,
    page: int = 1,
    per_page: int = 10,
    status: str | None = None,
    sort: Literal["newest", "oldest", "score_asc", "score_desc"] = "newest",
) -> AssessmentListResponse:
    tenant_id = current_user.microsoft_tid

    base_where = [
        Assessment.tenant_id == tenant_id,
        Assessment.deleted_at.is_(None),
    ]
    if status:
        base_where.append(Assessment.status == status)

    total = (
        await db.scalar(select(func.count(Assessment.id)).where(*base_where))
    ) or 0

    sort_col = {
        "newest": Assessment.created_at.desc(),
        "oldest": Assessment.created_at.asc(),
        "score_asc": Assessment.overall_score.asc(),
        "score_desc": Assessment.overall_score.desc(),
    }.get(sort, Assessment.created_at.desc())

    offset = (page - 1) * per_page
    assessments = list(
        (
            await db.execute(
                select(Assessment)
                .options(
                    noload(Assessment.findings),
                    noload(Assessment.jobs),
                    noload(Assessment.events),
                    noload(Assessment.recommendations),
                )
                .where(*base_where)
                .order_by(sort_col)
                .offset(offset)
                .limit(per_page)
            )
        ).scalars().all()
    )

    if not assessments:
        return AssessmentListResponse(items=[], total=total, page=page, per_page=per_page)

    # Resolve tenant names in one query
    tenant_ids = list({a.tenant_id for a in assessments})
    tenant_name_map: dict[str, str | None] = {
        row.tenant_id: row.tenant_name
        for row in (
            await db.execute(
                select(ConnectedTenant.tenant_id, ConnectedTenant.tenant_name).where(
                    ConnectedTenant.tenant_id.in_(tenant_ids)
                )
            )
        )
    }

    # Fetch latest job per assessment (for started_at / completed_at)
    assessment_ids = [a.id for a in assessments]
    all_jobs = list(
        (
            await db.execute(
                select(AssessmentJob)
                .options(noload(AssessmentJob.assessment))
                .where(AssessmentJob.assessment_id.in_(assessment_ids))
                .order_by(AssessmentJob.created_at.desc())
            )
        ).scalars().all()
    )
    latest_job: dict[UUID, AssessmentJob] = {}
    for job in all_jobs:
        if job.assessment_id not in latest_job:
            latest_job[job.assessment_id] = job

    items = [
        AssessmentListItemResponse(
            id=a.id,
            tenant_id=a.tenant_id,
            tenant_name=tenant_name_map.get(a.tenant_id),
            status=a.status,
            overall_score=a.overall_score,
            identity_score=a.identity_score,
            security_score=a.security_score,
            compliance_score=a.compliance_score,
            collaboration_score=a.collaboration_score,
            licensing_score=a.licensing_score,
            total_findings=a.total_findings,
            critical_findings=a.critical_findings,
            started_at=latest_job[a.id].started_at if a.id in latest_job else None,
            completed_at=latest_job[a.id].completed_at if a.id in latest_job else None,
            created_at=a.created_at,
        )
        for a in assessments
    ]

    return AssessmentListResponse(items=items, total=total, page=page, per_page=per_page)


async def delete_assessment(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> UUID:
    assessment = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.tenant_id == current_user.microsoft_tid,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalars().first()

    if assessment is None:
        raise NotFoundException("Assessment not found")

    assessment.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return assessment_id


async def get_assessment_results(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> AssessmentResultsResponse:
    assessment = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.tenant_id == current_user.microsoft_tid,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalars().first()

    if assessment is None:
        raise NotFoundException("Assessment not found")

    # Tenant name
    tenant_name = await db.scalar(
        select(ConnectedTenant.tenant_name).where(
            ConnectedTenant.tenant_id == assessment.tenant_id
        )
    )

    # Latest job (started_at / completed_at)
    job = (
        await db.execute(
            select(AssessmentJob)
            .where(
                AssessmentJob.assessment_id == assessment.id,
                AssessmentJob.tenant_id == assessment.tenant_id,
            )
            .order_by(AssessmentJob.created_at.desc())
            .limit(1)
        )
    ).scalars().first()

    # Findings
    findings = list(
        (
            await db.execute(
                select(AssessmentFinding)
                .options(selectinload(AssessmentFinding.parameter))
                .where(AssessmentFinding.assessment_id == assessment.id)
            )
        ).scalars().all()
    )

    sev_counts: dict[str, int] = {
        "critical": 0, "high": 0, "medium": 0, "low": 0, "passed": 0,
    }
    finding_items: list[FindingItem] = []
    for f in findings:
        sev = (f.severity or "").lower()
        if f.status and f.status.lower() in {"pass"}:
            sev_counts["passed"] += 1
        elif sev in sev_counts:
            sev_counts[sev] += 1
        finding_items.append(
            FindingItem(
                id=f.id,
                parameter_key=f.parameter_key,
                parameter_name=f.parameter_name,
                category=f.category,
                status=f.status,
                severity=f.severity,
                raw_value=f.raw_value,
                evaluated_value=f.evaluated_value,
                score_contribution=f.score_contribution,
            )
        )

    # Recommendations
    recommendations = list(
        (
            await db.execute(
                select(AssessmentRecommendation)
                .where(
                    AssessmentRecommendation.assessment_id == assessment.id,
                    AssessmentRecommendation.tenant_id == assessment.tenant_id,
                )
                .order_by(AssessmentRecommendation.created_at.desc())
            )
        ).scalars().all()
    )

    # Reports
    reports = list(
        (
            await db.execute(
                select(AssessmentReport).where(
                    AssessmentReport.assessment_id == assessment.id
                )
            )
        ).scalars().all()
    )
    report_types = {r.report_type for r in reports}
    latest_report = max(reports, key=lambda r: r.generated_at, default=None)

    return AssessmentResultsResponse(
        assessment=AssessmentResultsSummary(
            id=assessment.id,
            tenant_id=assessment.tenant_id,
            status=assessment.status,
            overall_score=assessment.overall_score,
            tenant_name=tenant_name,
            started_at=job.started_at if job else None,
            completed_at=job.completed_at if job else None,
            copilot_eligible_user_count=assessment.copilot_eligible_user_count,
            total_user_count=assessment.total_findings,
        ),
        scores=AssessmentResultsScores(
            overall=assessment.overall_score,
            identity=assessment.identity_score,
            security=assessment.security_score,
            compliance=assessment.compliance_score,
            collaboration=assessment.collaboration_score,
            licensing=assessment.licensing_score,
        ),
        findings=FindingsSummary(
            total=len(finding_items),
            critical=sev_counts["critical"],
            high=sev_counts["high"],
            medium=sev_counts["medium"],
            low=sev_counts["low"],
            passed=sev_counts["passed"],
            items=finding_items,
        ),
        recommendations=[
            RecommendationItem(
                id=r.id,
                parameter_key=r.parameter_key,
                title=r.title,
                severity=r.severity,
                recommendation_text=r.recommendation_text,
                remediation_steps=r.remediation_steps
                if isinstance(r.remediation_steps, list)
                else None,
                effort=r.effort,
                impact=r.impact,
            )
            for r in recommendations
        ],
        report=ReportStatus(
            exists=bool(reports),
            generated_at=latest_report.generated_at if latest_report else None,
            pdf_available="pdf" in report_types,
            docx_available="docx" in report_types,
        ),
        readiness=_readiness_tier(assessment.overall_score, sev_counts["critical"]),
    )
