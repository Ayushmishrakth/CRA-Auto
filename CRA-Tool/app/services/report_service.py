"""
Report API business logic.
"""

import os
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.schemas.report import ReportResponse
from app.services.assessment_service import get_assessment
from app.services.reporting.cra_report_service import get_report_bundle
from app.services.reporting.report_customization import store_customization


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

    LOGO_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    logo_path = None
    if logo_file:
        allowed_formats = os.getenv("LOGO_ALLOWED_FORMATS", "png,jpg,jpeg,svg").split(",")
        file_ext = logo_file.filename.split(".")[-1].lower()

        if file_ext not in allowed_formats:
            raise ValueError(f"Invalid file format. Allowed: {allowed_formats}")

        logo_filename = f"{assessment_id}_{logo_file.filename}"
        logo_path = LOGO_TEMP_DIR / logo_filename

        with open(logo_path, "wb") as f:
            content = await logo_file.read()
            f.write(content)

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
