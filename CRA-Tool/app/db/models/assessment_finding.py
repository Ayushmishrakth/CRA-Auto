"""
Assessment Finding model for tracking individual parameter evaluations.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_model import Base, UUIDMixin
from app.db.types import JSONType


class AssessmentFinding(Base, UUIDMixin):
    __tablename__ = "assessment_findings"

    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessments.id"), nullable=False, index=True)
    parameter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessment_parameters.id"), nullable=False, index=True)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assessment_rules.id"), nullable=True, index=True)
    
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    
    raw_value: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)
    evaluated_value: Mapped[str | None] = mapped_column(String, nullable=True)
    
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    score_contribution: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assessment: Mapped["Assessment"] = relationship(back_populates="findings", lazy="selectin")
    parameter: Mapped["AssessmentParameter"] = relationship(lazy="selectin")
    rule: Mapped["AssessmentRule"] = relationship(lazy="selectin")

    @property
    def parameter_key(self) -> str | None:
        return self.parameter.parameter_key if self.parameter else None

    @property
    def parameter_name(self) -> str | None:
        return self.parameter.parameter_name if self.parameter else None

    @property
    def category(self) -> str | None:
        return self.parameter.category if self.parameter else None
