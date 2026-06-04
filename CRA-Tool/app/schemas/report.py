"""
Report API schemas.
"""

from uuid import UUID

from pydantic import BaseModel


class ReportResponse(BaseModel):
    assessment_id: UUID
    status: str
    report_path: str | None
    download_ready: bool


class ReportArtifactResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    report_type: str
    report_status: str
    storage_path: str
    generated_at: str
    generated_by: UUID | None
    metadata: dict | list | None = None


class ReportBundleResponse(BaseModel):
    assessment_id: UUID
    status: str
    download_ready: bool
    artifacts: list[ReportArtifactResponse]
    summary: dict
    analytics: dict


class GenerateReportResponse(BaseModel):
    assessment_id: UUID
    status: str
    artifacts: list[ReportArtifactResponse]
    summary: dict
    analytics: dict
