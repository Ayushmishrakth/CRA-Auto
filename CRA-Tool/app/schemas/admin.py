"""
Admin API schemas.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssessmentParameterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parameter_key: str
    parameter_name: str
    category: str
    collection_method: str
    collector_module: str | None
    graph_endpoint: str | None
    copilot_relevance: str | None
    is_active: bool
    excel_row_reference: str | None


class RuleUpdateRequest(BaseModel):
    rule_type: str = Field(..., max_length=50)
    pass_threshold: str | None = Field(default=None, max_length=255)
    warning_threshold: str | None = Field(default=None, max_length=255)
    pass_condition: dict[str, Any] | list[Any] | None = None
    severity: str = Field(..., max_length=50)
    scoring_weight: float = Field(default=1.0, ge=0)
    copilot_blocking: bool = False
