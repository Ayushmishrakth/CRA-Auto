"""
Pydantic schemas for CRA Assessment API (Phase 2 stubs).
"""

from pydantic import BaseModel, Field


class AssessmentSummaryResponse(BaseModel):
    """High-level assessment status for list/dashboard views."""

    message: str = Field(..., description="Placeholder status until assessments are implemented")
    module: str = Field(default="assessment", description="CRA module identifier")
