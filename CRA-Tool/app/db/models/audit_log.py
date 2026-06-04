"""
Enterprise audit logging model.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_model import Base, UUIDMixin
from app.db.types import JSONType


class AuditLog(Base, UUIDMixin):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_tenant_event_created_at", "tenant_id", "event_type", "created_at"),
    )

    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    metadata_payload: Mapped[dict | list | None] = mapped_column(JSONType, nullable=True)
    
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    user: Mapped["User | None"] = relationship(lazy="selectin")
