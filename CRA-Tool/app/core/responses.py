"""
Standard API response envelopes.
"""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | list[Any] | None = None


class SuccessResponse(BaseModel, Generic[DataT]):
    success: bool = True
    message: str
    data: DataT | None = None
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


def success_response(
    *,
    message: str,
    data: Any = None,
    request_id: str | None = None,
) -> SuccessResponse[Any]:
    return SuccessResponse(message=message, data=data, request_id=request_id)
