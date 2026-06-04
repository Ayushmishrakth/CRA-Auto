"""
Assessment runtime job model.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_model import Base, TenantMixin, UUIDMixin
from app.db.types import JSONType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AssessmentJob(Base, UUIDMixin, TenantMixin):
    __tablename__ = "assessment_jobs"
    __table_args__ = (
        Index("ix_assessment_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_assessment_jobs_assessment_created", "assessment_id", "created_at"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    worker_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_payload: Mapped[dict | list | None] = mapped_column("metadata", JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False, index=True
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="jobs", lazy="selectin")
