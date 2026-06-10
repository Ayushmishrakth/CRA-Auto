"""
Report API routes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.responses import SuccessResponse, success_response
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.report import ReportCustomizationRequest, ReportResponse
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


@router.post(
    "/assessments/{assessment_id}/customize",
)
async def upload_report_customization(
    assessment_id: UUID,
    logo: UploadFile = File(None),
    address: str = Form(None),
    company_name: str = Form(None),
    output_format: str = Form("docx"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    customization = await report_service.handle_report_customization(
        db,
        current_user=current_user,
        assessment_id=assessment_id,
        logo_file=logo,
        address=address,
        company_name=company_name,
        output_format=output_format,
    )
    return success_response(
        message="Report customization uploaded",
        data=customization,
        request_id=request.state.request_id if request else None,
    )
