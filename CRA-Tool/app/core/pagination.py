"""
Reusable pagination, sorting, filtering, and search dependencies.
"""

from typing import Literal

from fastapi import Query
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    page: int | None = Field(default=None, ge=1)
    sort_by: str | None = Field(default=None, max_length=100)
    order: Literal["asc", "desc"] = "desc"
    search: str | None = Field(default=None, max_length=255)

    @property
    def resolved_offset(self) -> int:
        if self.page is None:
            return self.offset
        return (self.page - 1) * self.limit


def get_pagination_params(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    page: int | None = Query(default=None, ge=1),
    sort_by: str | None = Query(default=None, max_length=100),
    order: Literal["asc", "desc"] = Query(default="desc"),
    search: str | None = Query(default=None, max_length=255),
) -> PaginationParams:
    return PaginationParams(
        limit=limit,
        offset=offset,
        page=page,
        sort_by=sort_by,
        order=order,
        search=search,
    )
