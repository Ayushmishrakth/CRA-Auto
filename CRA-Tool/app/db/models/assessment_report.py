"""
Generated CRA report artifact model.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_model import Base, UUIDMixin
from app.db.types import JSONType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AssessmentReport(Base, UUIDMixin):
    __tablename__ = "assessment_reports"
    __table_args__ = (
        Index("ix_assessment_reports_assessment_type", "assessment_id", "report_type"),
        Index("ix_assessment_reports_status", "report_status"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id"), nullable=False, index=True
    )
    report_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    report_status: Mapped[str] = mapped_column(String(50), default="generated", nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False, index=True
    )
    generated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)

    assessment: Mapped["Assessment"] = relationship(lazy="selectin")
