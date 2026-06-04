"""
Health and monitoring schemas.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    status: str
    details: dict[str, Any] = {}


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    components: dict[str, ComponentHealth]
