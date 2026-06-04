"""
Report API business logic.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.schemas.report import ReportResponse
from app.services.assessment_service import get_assessment
from app.services.reporting.cra_report_service import get_report_bundle


async def get_report_status(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> ReportResponse:
    assessment = await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    bundle = await get_report_bundle(db, current_user=current_user, assessment_id=assessment_id)
    pdf_artifact = next(
        (item for item in bundle["artifacts"] if item["report_type"] == "pdf"),
        None,
    )
    return ReportResponse(
        assessment_id=assessment.id,
        status=bundle["status"],
        report_path=pdf_artifact["storage_path"] if pdf_artifact else assessment.report_path,
        download_ready=bundle["download_ready"],
    )
