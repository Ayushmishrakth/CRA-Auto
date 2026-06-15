"""
Report API routes - Complete report generation with white-label support.
"""

import asyncio
import imghdr
import logging
import zipfile
import tempfile
from uuid import UUID
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.responses import SuccessResponse, success_response
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.report import ReportCustomizationRequest, ReportResponse
from app.services import report_service

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
    """
    Complete report generation with white-label customization.

    Steps:
    1. Upload logo (optional)
    2. Enter company name and address
    3. Select report format (pdf, docx, or both)
    4. Generate and download
    """
    try:
        logger.info(
            "[REPORT] Starting generation for assessment=%s, user=%s, format=%s",
            assessment_id,
            current_user.id,
            report_format,
        )
        logger.info(
            "[REPORT] Parameters: company_name=%s (len=%d), address=%s (len=%d), has_logo=%s",
            bool(company_name),
            len(company_name) if company_name else 0,
            bool(company_address),
            len(company_address) if company_address else 0,
            bool(logo),
        )
        if logo:
            logger.info(
                "[REPORT] Logo file: filename=%s, content_type=%s, size=%s bytes",
                logo.filename,
                logo.content_type,
                len(await logo.read()) if logo else "unknown",
            )
            # Reset file pointer after reading size
            await logo.seek(0)

        # Step 1: Handle logo upload
        logo_path = None
        if logo and logo.filename:
            try:
                logger.info(f"[REPORT] Processing logo: {logo.filename}")

                if logo.content_type not in ALLOWED_MIME_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid logo format. Allowed: PNG, JPG, SVG"
                    )

                content = await logo.read()
                if len(content) > MAX_LOGO_SIZE_BYTES:
                    raise HTTPException(status_code=400, detail="Logo file too large (max 5MB)")

                if len(content) == 0:
                    raise HTTPException(status_code=400, detail="Logo file is empty")

                # Validate file content
                detected_type = imghdr.what(None, h=content)
                if detected_type not in {"png", "jpeg", "webp"}:
                    logger.warning(f"[REPORT] File detection returned: {detected_type}, allowing based on extension")

                # Save logo
                logo_dir = Path("storage/logos")
                logo_dir.mkdir(parents=True, exist_ok=True)

                import uuid as uuid_module
                file_ext = Path(logo.filename).suffix
                logo_filename = f"{current_user.id}_{uuid_module.uuid4()}{file_ext}"
                logo_path = logo_dir / logo_filename

                with open(logo_path, "wb") as f:
                    f.write(content)

                # Verify file was saved
                import os
                file_exists = os.path.exists(logo_path)
                file_size = os.path.getsize(logo_path) if file_exists else 0

                logger.info(f"[REPORT] Logo saved: {logo_path} ({len(content)} bytes)")
                logger.info(f"[REPORT] Logo file verification - exists: {file_exists}, size: {file_size}")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[REPORT] Logo upload failed: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Logo upload failed: {str(e)}")

        # Step 2: Fetch assessment data
        logger.info(f"[REPORT] Fetching assessment data from database...")
        from app.services.reporting.assessment_report_data_service import AssessmentReportDataService

        assessment_data = await AssessmentReportDataService.get_assessment_report_data(db, assessment_id)

        if not assessment_data:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # Step 3: Apply customization
        if company_name:
            logger.info(f"[REPORT] Applying company name: {company_name}")
            assessment_data['tenant_name'] = company_name
            if 'summary' not in assessment_data:
                assessment_data['summary'] = {}
            assessment_data['summary']['tenant_name'] = company_name
            assessment_data['summary']['organization_name'] = company_name

        if company_address:
            logger.info(f"[REPORT] Applying address: {company_address}")
            assessment_data['company_address'] = company_address

        if logo_path:
            logo_path_str = str(logo_path)
            logger.info(f"[REPORT] Setting logo path: {logo_path_str}")
            logger.info(f"[REPORT] Logo file exists: {logo_path.exists()}")
            logger.info(f"[REPORT] Logo file size: {logo_path.stat().st_size if logo_path.exists() else 'N/A'}")
            assessment_data['logo_path'] = logo_path_str
        else:
            logger.info(f"[REPORT] No logo provided (logo_path is None)")
            assessment_data['logo_path'] = None

        logger.info(f"[REPORT] Data ready: {len(assessment_data.get('findings', []))} findings, "
                   f"company={assessment_data.get('tenant_name')}, "
                   f"address={assessment_data.get('company_address', 'N/A')}, "
                   f"logo_path={'yes' if logo_path else 'no'}")

        # Step 4: Generate report
        logger.info(f"[REPORT] Generating report...")
        from app.services.reporting.enhanced_report_generator import EnhancedReportGenerator

        def gen_report():
            gen = EnhancedReportGenerator(assessment_data, logo_path=str(logo_path) if logo_path else None)
            return gen.generate()

        report_bytes = await asyncio.to_thread(gen_report)
        logger.info(f"[REPORT] Report generated: {len(report_bytes.getvalue())} bytes")

        # Step 5: Save and return
        Path("storage/reports").mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_company_name = sanitize_filename(company_name or "Assessment")

        format_lower = (report_format or "pdf").lower().strip()
        if format_lower not in {"pdf", "docx", "both"}:
            format_lower = "pdf"

        # Always generate DOCX first
        word_path = Path(f"storage/reports/{safe_company_name}_{timestamp}.docx")
        with open(word_path, "wb") as f:
            f.write(report_bytes.getvalue())
        logger.info(f"[REPORT] DOCX saved: {word_path}")

        if format_lower == "docx":
            return FileResponse(
                path=str(word_path),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                filename=f"Assessment_Report_{safe_company_name}_{timestamp}.docx"
            )

        elif format_lower == "pdf":
            pdf_path = Path(f"storage/reports/{safe_company_name}_{timestamp}.pdf")

            def convert_pdf():
                logger.info(f"[REPORT] Converting DOCX to PDF...")
                try:
                    from docx2pdf import convert
                    convert(str(word_path), str(pdf_path))
                    logger.info(f"[REPORT] PDF conversion complete: {pdf_path}")
                    return pdf_path
                except Exception as e:
                    logger.error(f"[REPORT] PDF conversion failed: {e}")
                    raise

            try:
                pdf_file = await asyncio.to_thread(convert_pdf)
                return FileResponse(
                    path=str(pdf_file),
                    media_type="application/pdf",
                    filename=f"Assessment_Report_{safe_company_name}_{timestamp}.pdf"
                )
            except Exception as e:
                logger.warning(f"[REPORT] PDF conversion failed, returning DOCX instead: {e}")
                return FileResponse(
                    path=str(word_path),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    filename=f"Assessment_Report_{safe_company_name}_{timestamp}.docx"
                )

        elif format_lower == "both":
            # Generate both PDF and DOCX, return as ZIP
            pdf_path = Path(f"storage/reports/{safe_company_name}_{timestamp}.pdf")

            def convert_and_zip():
                logger.info(f"[REPORT] Converting DOCX to PDF for ZIP...")
                try:
                    from docx2pdf import convert
                    convert(str(word_path), str(pdf_path))
                    logger.info(f"[REPORT] PDF conversion complete: {pdf_path}")
                except Exception as e:
                    logger.error(f"[REPORT] PDF conversion failed, ZIP will contain DOCX only: {e}")
                    pdf_path = None

                # Create ZIP with both files
                zip_path = Path(f"storage/reports/{safe_company_name}_{timestamp}.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(word_path, arcname=word_path.name)
                    if pdf_path and pdf_path.exists():
                        zf.write(pdf_path, arcname=pdf_path.name)

                logger.info(f"[REPORT] ZIP created: {zip_path}")
                return zip_path

            try:
                zip_file = await asyncio.to_thread(convert_and_zip)
                return FileResponse(
                    path=str(zip_file),
                    media_type="application/zip",
                    filename=f"Assessment_Report_{safe_company_name}_{timestamp}.zip"
                )
            except Exception as e:
                logger.error(f"[REPORT] ZIP creation failed: {e}")
                # Fallback to DOCX
                return FileResponse(
                    path=str(word_path),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    filename=f"Assessment_Report_{safe_company_name}_{timestamp}.docx"
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
