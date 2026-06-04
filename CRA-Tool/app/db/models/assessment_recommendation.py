"""
Assessment recommendation persistence model.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_model import Base, TenantMixin, UUIDMixin
from app.db.types import JSONType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AssessmentRecommendation(Base, UUIDMixin, TenantMixin):
    __tablename__ = "assessment_recommendations"
    __table_args__ = (
        Index("ix_assessment_recommendations_tenant_created", "tenant_id", "created_at"),
        Index("ix_assessment_recommendations_assessment_created", "assessment_id", "created_at"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id"), nullable=False, index=True
    )
    parameter_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    recommendation_text: Mapped[str] = mapped_column(String, nullable=False)
    remediation_steps: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)
    effort: Mapped[str | None] = mapped_column(String(50), nullable=True)
    impact: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False, index=True
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="recommendations", lazy="selectin")
