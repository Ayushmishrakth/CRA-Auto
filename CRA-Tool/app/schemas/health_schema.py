"""
Pydantic schemas for Health API responses.

`response_model` in routes uses these classes for validation and OpenAPI docs.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Standard health check payload returned by GET /api/v1/health."""

    status: str = Field(
        ...,
        description="Human-readable server status message",
        examples=["Server Running Successfully"],
    )
