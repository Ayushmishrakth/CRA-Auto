"""
Assessment API schemas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssessmentStartRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=64)


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID | None = None
    tenant_id: str
    triggered_by_user_id: UUID
    status: str
    progress_pct: float
    overall_score: float | None
    identity_score: float | None
    security_score: float | None
    compliance_score: float | None
    collaboration_score: float | None
    licensing_score: float | None
    total_findings: int | None
    critical_findings: int | None
    high_findings: int | None
    report_path: str | None
    created_at: datetime
    updated_at: datetime


class AssessmentFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_id: UUID
    parameter_id: UUID
    parameter_key: str | None = None
    parameter_name: str | None = None
    category: str | None = None
    rule_id: UUID | None
    status: str
    raw_value: dict[str, Any] | list[Any] | None
    evaluated_value: str | None
    severity: str | None
    score_contribution: float | None
    collected_at: datetime | None
    evaluated_at: datetime | None


class AssessmentScoreResponse(BaseModel):
    assessment_id: UUID
    overall_score: float | None
    categories: dict[str, float | None]
    status: str


class AssessmentRecommendationResponse(BaseModel):
    assessment_id: UUID
    recommendations: list[dict[str, Any]]


class AssessmentJobResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    tenant_id: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    current_stage: str | None
    progress_pct: float
    worker_id: str | None
    error_message: str | None
    metadata: dict[str, Any] | list[Any] | None = None
    created_at: datetime


class AssessmentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_id: UUID
    tenant_id: str
    event_type: str
    severity: str
    event_payload: dict[str, Any] | list[Any] | None
    created_at: datetime


class AssessmentEvidenceParameterResponse(BaseModel):
    parameter_key: str
    parameter_name: str
    service: str
    collector: str | None
    status: str
    collector_status: str | None = None
    failure_reason: str | None = None
    collection_method: str | None = None
    evidence_source: str | None = None
    severity: str | None
    actual_value: Any | None = None
    expected_value: str | None = None
    finding: str | None = None
    recommendation: dict[str, Any] | None = None
    evidence: dict[str, Any] | list[Any] | None = None
    artifact_json: dict[str, Any] | list[Any] | None = None
    artifact_id: UUID | None = None
    collected_at: datetime | None = None
    reason: str
    failure_details: dict[str, Any] | list[Any] | None = None


class AssessmentEvidenceCoverageResponse(BaseModel):
    total_parameters: int
    implemented_collectors: int
    collected: int
    failed: int = 0
    collection_error: int = 0
    licensing_required: int = 0
    manual_validation: int = 0
    not_collected: int
    coverage_percent: float


class AssessmentEvidenceResponse(BaseModel):
    assessment_id: UUID
    tenant_id: str
    coverage: AssessmentEvidenceCoverageResponse
    parameters: list[AssessmentEvidenceParameterResponse]


class AssessmentFailureResponse(BaseModel):
    parameter: str
    collector: str | None = None
    status: str
    error: str | None = None
