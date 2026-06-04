"""
Raw runtime evidence and collector execution artifacts.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_model import Base, TenantMixin, UUIDMixin
from app.db.types import JSONType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AssessmentArtifact(Base, UUIDMixin, TenantMixin):
    __tablename__ = "assessment_artifacts"
    __table_args__ = (
        Index("ix_assessment_artifacts_assessment_parameter", "assessment_id", "parameter_key"),
        Index("ix_assessment_artifacts_tenant_created", "tenant_id", "created_at"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessment_jobs.id"), nullable=True, index=True
    )
    parameter_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    parameter_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    service: Mapped[str | None] = mapped_column(String(100), nullable=True)
    collector_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graph_endpoint: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_script: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_csv: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    actual_value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONType, nullable=True)
    expected_value: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    raw_evidence_json: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)
    collection_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stdout: Mapped[str | None] = mapped_column(String, nullable=True)
    stderr: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False, index=True
    )

    assessment: Mapped["Assessment"] = relationship(lazy="selectin")
