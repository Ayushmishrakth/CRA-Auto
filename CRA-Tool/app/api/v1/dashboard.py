"""
Dashboard API routes.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.responses import SuccessResponse, success_response
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.dashboard import DashboardStatsResponse
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/stats",
    response_model=SuccessResponse[DashboardStatsResponse],
    summary="Dashboard statistics",
)
async def get_dashboard_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[DashboardStatsResponse]:
    stats = await dashboard_service.get_dashboard_stats(db, current_user=current_user)
    return success_response(
        message="Dashboard statistics retrieved",
        data=stats,
        request_id=request.state.request_id,
    )
