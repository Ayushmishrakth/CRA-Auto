from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ParameterImportResponse(BaseModel):
    version_id: UUID
    version: str
    source_hash: str
    source_filename: str
    parameter_count: int
    is_active: bool
    validation_report: dict[str, Any] | list[Any] | None
    already_imported: bool = False


class ParameterVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version: str
    source_filename: str
    source_hash: str
    imported_by: UUID | None
    imported_at: datetime
    is_active: bool
    validation_report: dict[str, Any] | list[Any] | None
