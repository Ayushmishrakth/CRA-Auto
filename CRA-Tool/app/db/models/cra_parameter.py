"""
Production CRA parameter, evidence, and result models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_model import Base, TenantMixin, TimestampMixin, UUIDMixin
from app.db.types import JSONType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CraParameterVersion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cra_parameter_versions"

    version: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    source_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    imported_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    validation_report: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)

    parameters: Mapped[list["CraParameter"]] = relationship(
        back_populates="version_record",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CraParameter(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cra_parameters"
    __table_args__ = (
        UniqueConstraint("version_id", "parameter_key", name="uq_cra_parameters_version_key"),
        Index("ix_cra_parameters_version_active", "version_id", "is_active"),
    )

    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cra_parameter_versions.id"),
        nullable=False,
        index=True,
    )
    parameter_key: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    technology: Mapped[str | None] = mapped_column(String(150), nullable=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    weight: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    pass_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    fail_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria_expression: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)
    collector_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    graph_endpoint: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    powershell_mapping: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portal_mapping: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    copilot_relevance: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    source_ref: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)

    version_record: Mapped[CraParameterVersion] = relationship(back_populates="parameters", lazy="selectin")


class CraParameterEvidence(Base, UUIDMixin):
    __tablename__ = "cra_parameter_evidence"
    __table_args__ = (
        Index("ix_cra_parameter_evidence_assessment_parameter", "assessment_id", "parameter_id"),
        Index("ix_cra_parameter_evidence_tenant_collected", "tenant_id", "collected_at"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessments.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parameter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cra_parameters.id"), nullable=False, index=True)
    collector_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    graph_endpoint: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    evidence: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)
    raw_response: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    parameter: Mapped[CraParameter] = relationship(lazy="selectin")


class CraAssessmentResult(Base, UUIDMixin, TenantMixin):
    __tablename__ = "cra_assessment_results"
    __table_args__ = (
        UniqueConstraint("assessment_id", "parameter_id", name="uq_cra_assessment_results_assessment_parameter"),
        Index("ix_cra_assessment_results_assessment_status", "assessment_id", "status"),
        Index("ix_cra_assessment_results_tenant_evaluated", "tenant_id", "evaluated_at"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessments.id"), nullable=False, index=True)
    parameter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cra_parameters.id"), nullable=False, index=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cra_parameter_evidence.id"), nullable=True, index=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    gap_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False, index=True)
    criteria_snapshot: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)

    parameter: Mapped[CraParameter] = relationship(lazy="selectin")
    evidence_record: Mapped[CraParameterEvidence | None] = relationship(lazy="selectin")
