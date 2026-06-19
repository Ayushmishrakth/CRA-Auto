"""
Report API routes - Complete report generation with white-label support.
"""

import imghdr
import logging
from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.responses import SuccessResponse, success_response
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.report import ReportResponse
from app.services import report_service
from app.services.reporting import cra_report_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])

ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/svg+xml"}
MAX_LOGO_SIZE_BYTES = 5 * 1024 * 1024  # 5MB


def sanitize_filename(name: str) -> str:
    """Sanitize filename by removing special characters."""
    import re
    return re.sub(r'[^a-zA-Z0-9_\-.]', '_', name)[:255]


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
    "/assessments/{assessment_id}/generate",
    name="generate_report_with_customization"
)
async def generate_assessment_report(
    assessment_id: UUID,
    company_name: str = Form(default=""),
    company_address: str = Form(default=""),
    report_format: str = Form(default="pdf"),
    logo: UploadFile = File(default=None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        logo_path_str = None
        if logo and hasattr(logo, "filename") and logo.filename:
            logo_bytes = await logo.read()
            if logo_bytes:
                import uuid as _uuid

                ext = Path(logo.filename).suffix.lower() or ".png"
                logo_dir = Path("storage/logos")
                logo_dir.mkdir(parents=True, exist_ok=True)
                lf = (logo_dir / f"{assessment_id}_{_uuid.uuid4().hex}{ext}").resolve()
                lf.write_bytes(logo_bytes)
                logo_path_str = str(lf)

        partner = (company_name or '').strip() or None
        address = (company_address or '').strip() or None

        payload = await cra_report_service.generate_report_bundle(
            assessment_id=str(assessment_id),
            db=db,
            current_user=current_user,
            report_type=report_format,
            partner_name=partner,
            logo_path=logo_path_str,
            company_address=address,
        )

        if isinstance(payload, dict):
            arts = payload.get("artifacts", [])
            fp = (
                payload.get("file_path")
                or payload.get("docx_path")
                or (arts[0].get("file_path") or arts[0].get("storage_path") if arts else None)
            )
        else:
            fp = str(payload)

        if not fp:
            raise HTTPException(status_code=500, detail="Report generation did not return a file path")

        return FileResponse(
            path=fp,
            filename=f'CRA_Report_{assessment_id}.docx',
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except ValueError as ve:
        logger.error("[REPORT] Validation error: %s", str(ve), exc_info=True)
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "[REPORT] Unexpected error during generation for assessment=%s: %s",
            assessment_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(exc)}"
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
    if logo:
        if logo.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: PNG, JPEG, WebP"
            )

        content = await logo.read()

        if len(content) > MAX_LOGO_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="Logo must be under 5MB")

        detected_type = imghdr.what(None, h=content)
        if detected_type not in {"png", "jpeg", "webp"}:
            raise HTTPException(
                status_code=400,
                detail="File content does not match declared type"
            )

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
