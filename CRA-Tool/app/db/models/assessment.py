"""
Assessment model for tracking readiness evaluation runs.
"""

import uuid
from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_model import Base, TenantMixin, TimestampMixin, UUIDMixin


class Assessment(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "assessments"
    __table_args__ = (
        Index("ix_assessments_tenant_status_created_at", "tenant_id", "status", "created_at"),
    )

    triggered_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False, index=True)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    identity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    security_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    collaboration_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    licensing_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    copilot_eligible_user_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    total_findings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    critical_findings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    high_findings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    report_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    findings: Mapped[list["AssessmentFinding"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", lazy="selectin"
    )
    jobs: Mapped[list["AssessmentJob"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", lazy="selectin"
    )
    events: Mapped[list["AssessmentEvent"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", lazy="selectin"
    )
    recommendations: Mapped[list["AssessmentRecommendation"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", lazy="selectin"
    )
