"""
Common API schemas.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class PageMeta(BaseModel):
    limit: int
    offset: int
    count: int
    total: int | None = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    items: list[DataT]
    meta: PageMeta


class MessageData(BaseModel):
    message: str


class WebSocketEvent(BaseModel):
    event: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
