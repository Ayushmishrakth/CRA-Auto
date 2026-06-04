"""
Health check routes.

Mounted under /api/v1 in main.py — full path: GET /api/v1/health
"""

from fastapi import APIRouter

from app.schemas.health_schema import HealthResponse
from app.services import health_service

# Prefix is only the resource path; API version prefix is applied in main.py
router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns server status. Use for load balancers and uptime monitors.",
)
def health_check() -> HealthResponse:
    """Delegate to service layer — route handles HTTP, service handles logic."""
    return health_service.get_health_status()
