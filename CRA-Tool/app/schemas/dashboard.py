"""
Schemas for dashboard stats, assessment list, and combined results endpoints.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    total_assessments: int
    completed_assessments: int
    in_progress_assessments: int
    failed_assessments: int
    connected_tenants: int
    average_score: float
    last_assessment_date: datetime | None


class AssessmentListItemResponse(BaseModel):
    id: UUID
    tenant_id: str
    tenant_name: str | None
    status: str
    overall_score: float | None
    identity_score: float | None
    security_score: float | None
    compliance_score: float | None
    collaboration_score: float | None
    licensing_score: float | None
    total_findings: int | None
    critical_findings: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class AssessmentListResponse(BaseModel):
    items: list[AssessmentListItemResponse]
    total: int
    page: int
    per_page: int


# ── Combined results ────────────────────────────────────────────────────────


class AssessmentResultsSummary(BaseModel):
    id: UUID
    tenant_id: str
    status: str
    overall_score: float | None
    tenant_name: str | None
    started_at: datetime | None
    completed_at: datetime | None
    copilot_eligible_user_count: int | None = None
    total_user_count: int | None = None


class AssessmentResultsScores(BaseModel):
    overall: float | None
    identity: float | None
    security: float | None
    compliance: float | None
    collaboration: float | None
    licensing: float | None


class FindingItem(BaseModel):
    id: UUID
    parameter_key: str | None
    parameter_name: str | None
    category: str | None
    status: str
    severity: str | None
    raw_value: dict[str, Any] | list[Any] | None
    evaluated_value: str | None = None
    score_contribution: float | None


class FindingsSummary(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int
    passed: int
    items: list[FindingItem]


class RecommendationItem(BaseModel):
    id: UUID
    parameter_key: str
    title: str
    severity: str
    recommendation_text: str
    remediation_steps: list[Any] | None
    effort: str | None
    impact: str | None


class ReportStatus(BaseModel):
    exists: bool
    generated_at: datetime | None
    pdf_available: bool
    docx_available: bool


class ReadinessTier(BaseModel):
    tier: str
    label: str
    copilot_blocking_issues: int
    description: str


class AssessmentResultsResponse(BaseModel):
    assessment: AssessmentResultsSummary
    scores: AssessmentResultsScores
    findings: FindingsSummary
    recommendations: list[RecommendationItem]
    report: ReportStatus
    readiness: ReadinessTier
