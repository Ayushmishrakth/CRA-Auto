"""
Report API business logic.
"""

import os
import shutil
import logging
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.schemas.report import ReportResponse
from app.services.assessment_service import get_assessment
from app.services.reporting.cra_report_service import get_report_bundle
from app.services.reporting.report_customization import store_customization

logger = logging.getLogger(__name__)
LOGO_STORAGE_DIR = Path("storage/logos")
LOGO_TEMP_DIR = Path("storage/temp/logos")


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


async def validate_and_save_logo(
    logo_file: UploadFile,
    user_id: UUID,
    max_size_bytes: int = 5 * 1024 * 1024,
) -> Path:
    """Validate and save logo file. Returns path to saved logo."""
    if not logo_file or not logo_file.filename:
        return None

    # Validate file type
    allowed_mime_types = {"image/png", "image/jpeg", "image/svg+xml"}
    if logo_file.content_type not in allowed_mime_types:
        raise ValueError(f"Invalid logo format. Allowed: PNG, JPG, SVG (got {logo_file.content_type})")

    # Read and validate file size
    content = await logo_file.read()
    if len(content) > max_size_bytes:
        raise ValueError(f"Logo file too large. Maximum size: {max_size_bytes / (1024*1024):.1f}MB")

    if len(content) == 0:
        raise ValueError("Logo file is empty")

    # Validate file extension
    allowed_extensions = {".png", ".jpg", ".jpeg", ".svg"}
    file_ext = Path(logo_file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise ValueError(f"Invalid file extension. Allowed: {allowed_extensions}")

    # Save logo with sanitized filename
    LOGO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    import uuid as uuid_module
    safe_filename = f"logo_{user_id}_{uuid_module.uuid4()}{file_ext}"
    logo_path = LOGO_STORAGE_DIR / safe_filename

    with open(logo_path, "wb") as f:
        f.write(content)

    logger.info(f"Logo saved for user {user_id}: {logo_path} ({len(content)} bytes)")
    return logo_path


async def handle_report_customization(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
    logo_file: UploadFile = None,
    address: str = None,
    company_name: str = None,
    output_format: str = "docx",
) -> dict:
    await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    output_format = (output_format or "docx").strip().lower()
    if output_format not in {"docx", "pdf", "both"}:
        raise ValueError("Invalid report output format. Allowed: docx, pdf, both")

    logo_path = None
    try:
        if logo_file:
            logo_path = await validate_and_save_logo(logo_file, current_user.id)
    except ValueError as e:
        logger.error(f"Logo validation failed: {e}")
        raise

    # Sanitize company name and address
    company_name = (company_name or "").strip()[:200] if company_name else None
    address = (address or "").strip()[:500] if address else None

    # Store in-memory for use during report generation
    store_customization(assessment_id, str(logo_path) if logo_path else None, address, company_name, output_format)

    return {
        "assessment_id": str(assessment_id),
        "logo_path": str(logo_path) if logo_path else None,
        "address": address,
        "company_name": company_name,
        "output_format": output_format,
        "message": "Report customization saved successfully",
    }
