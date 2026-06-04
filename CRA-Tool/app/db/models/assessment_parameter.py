"""
Assessment Parameter model for dynamic criteria definitions.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_model import Base, TimestampMixin, UUIDMixin


class AssessmentParameter(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessment_parameters"

    parameter_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    parameter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    collection_method: Mapped[str] = mapped_column(String(50), nullable=False)
    collector_module: Mapped[str | None] = mapped_column(String(100), nullable=True)
    graph_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    copilot_relevance: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    excel_row_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
