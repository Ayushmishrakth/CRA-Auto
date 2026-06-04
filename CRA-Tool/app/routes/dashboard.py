"""
Dashboard routes (Phase 2 stubs).

Full path: GET /api/v1/dashboard/summary

Dashboard-specific service can be added in Phase 3 when metrics are implemented.
"""

from fastapi import APIRouter

from app.schemas.dashboard_schema import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Dashboard summary",
    description="Placeholder overview for CRA dashboard (Phase 3+).",
)
def dashboard_summary() -> DashboardSummaryResponse:
    return DashboardSummaryResponse(
        message="Dashboard module ready (Phase 2 stub)",
        module="dashboard",
    )
