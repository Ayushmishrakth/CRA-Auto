"""
User session and JWT tracking model.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_model import Base, TimestampMixin, UUIDMixin


class UserSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_revoked_expires", "user_id", "revoked_at", "expires_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    jwt_jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions", lazy="selectin")
