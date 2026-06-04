"""
Assessment Rule model for evaluating parameter logic.
"""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_model import Base, TimestampMixin, UUIDMixin
from app.db.types import JSONType


class AssessmentRule(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessment_rules"

    parameter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessment_parameters.id"), nullable=False, index=True)
    
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    pass_threshold: Mapped[str | None] = mapped_column(String(255), nullable=True)
    warning_threshold: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pass_condition: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)
    
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    scoring_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    
    copilot_blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
