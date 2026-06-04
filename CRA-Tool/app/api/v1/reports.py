"""
Report API routes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.responses import SuccessResponse, success_response
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.report import ReportResponse
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/assessments/{assessment_id}",
    response_model=SuccessResponse[ReportResponse],
)
async def get_report_status(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[ReportResponse]:
    report = await report_service.get_report_status(
        db, current_user=current_user, assessment_id=assessment_id
    )
    return success_response(
        message="Report status retrieved",
        data=report,
        request_id=request.state.request_id,
    )
