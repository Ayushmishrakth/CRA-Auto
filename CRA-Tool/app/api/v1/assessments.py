"""
Assessment API routes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.pagination import PaginationParams, get_pagination_params
from app.core.responses import SuccessResponse, success_response
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.assessment import (
    AssessmentEventResponse,
    AssessmentEvidenceResponse,
    AssessmentFailureResponse,
    AssessmentFindingResponse,
    AssessmentJobResponse,
    AssessmentRecommendationResponse,
    AssessmentResponse,
    AssessmentScoreResponse,
    AssessmentStartRequest,
)
from app.schemas.dashboard import (
    AssessmentListResponse,
    AssessmentResultsResponse,
)
from app.schemas.report import GenerateReportResponse, ReportBundleResponse
from app.schemas.report_customization import ReportCustomization, ReportCustomizationResponse
from app.services import assessment_service, dashboard_service
from app.services.reporting import cra_report_service

from fastapi import UploadFile, File
from pathlib import Path
import uuid as uuid_module

router = APIRouter(tags=["Assessments"])


@router.post("/assessments/customize/upload-logo")
async def upload_report_logo(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
):
    """Upload company logo for white-label reports."""
    try:
        # Validate file type
        allowed_types = {"image/png", "image/jpeg", "image/svg+xml"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: PNG, JPG, SVG"
            )

        # Validate file size (max 5MB)
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")

        # Create logo directory
        logo_dir = Path("storage/logos")
        logo_dir.mkdir(parents=True, exist_ok=True)

        # Save with unique filename
        file_extension = Path(file.filename).suffix
        logo_filename = f"{current_user.id}_{uuid_module.uuid4()}{file_extension}"
        logo_path = logo_dir / logo_filename

        with open(logo_path, "wb") as f:
            f.write(content)

        return success_response(
            message="Logo uploaded successfully",
            data={
                "logo_path": str(logo_path),
                "filename": logo_filename,
                "size": len(content)
            },
            request_id=request.state.request_id if request else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logo upload failed: {str(e)}")


@router.post("/assessments/{assessment_id}/customize")
async def customize_report(
    assessment_id: UUID,
    company_name: str = Form(None),
    company_address: str = Form(None),
    report_format: str = Form("docx"),
    logo: UploadFile = File(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Save report customization settings for assessment - NOW ACCEPTS FILE UPLOADS!"""
    try:
        import logging
        from pathlib import Path as PathlibPath
        logger = logging.getLogger(__name__)

        # Verify assessment exists
        from sqlalchemy import select
        import app.db.base  # noqa
        from app.db.models.assessment import Assessment
        from app.services.reporting.report_customization import store_customization

        stmt = select(Assessment).where(Assessment.id == assessment_id)
        result = await db.execute(stmt)
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # Handle logo file upload if provided
        logo_path = None
        if logo and logo.filename:
            logger.info(f"[CUSTOMIZE] Logo file received: {logo.filename}")

            # Validate file type
            allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/svg+xml"}
            if logo.content_type not in allowed_types:
                raise HTTPException(status_code=400, detail=f"Invalid file type. Use PNG, JPG, or SVG")

            # Read and validate size
            content = await logo.read()
            if len(content) > 5 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Logo too large (max 5MB)")

            # Save logo file
            logo_dir = PathlibPath("storage/temp/logos").resolve()
            logo_dir.mkdir(parents=True, exist_ok=True)

            import uuid as uuid_module
            file_ext = PathlibPath(logo.filename).suffix
            logo_filename = f"{assessment_id}_{uuid_module.uuid4()}{file_ext}"
            logo_path = logo_dir / logo_filename

            with open(logo_path, "wb") as f:
                f.write(content)

            logger.info(f"[CUSTOMIZE] Logo saved (absolute): {logo_path.resolve()}")
            logger.info(f"[CUSTOMIZE] File exists after save: {logo_path.exists()}")

        # Store customization in the cache for report generation
        logger.info(f"[CUSTOMIZE] ========================================")
        logger.info(f"[CUSTOMIZE] STORING CUSTOMIZATION FOR {assessment_id}")
        logger.info(f"[CUSTOMIZE] ========================================")
        logger.info(f"[CUSTOMIZE]   company_name: {company_name}")
        logger.info(f"[CUSTOMIZE]   company_address: {company_address}")
        logger.info(f"[CUSTOMIZE]   logo_path: {logo_path}")
        logger.info(f"[CUSTOMIZE]   report_format: {report_format}")

        # Print to console
        print(f"\n{'='*60}")
        print(f"✅ CUSTOMIZATION RECEIVED:")
        print(f"  company_name: {company_name}")
        print(f"  company_address: {company_address}")
        print(f"  logo_path: {logo_path}")
        print(f"  report_format: {report_format}")
        print(f"{'='*60}\n")

        # Save to cache
        store_customization(
            assessment_id,
            logo_path=str(logo_path) if logo_path else None,
            address=company_address,
            company_name=company_name,
            output_format=report_format
        )

        logger.info(f"[CUSTOMIZE] ✅ Customization stored in cache")

        return success_response(
            message="Report customization saved",
            data={
                "assessment_id": str(assessment_id),
                "company_name": company_name,
                "company_address": company_address,
                "logo_path": str(logo_path) if logo_path else None,
                "report_format": report_format,
            },
            request_id=request.state.request_id if request else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"[CUSTOMIZE] ❌ Failed: {e}")
        raise HTTPException(status_code=500, detail=f"Customization failed: {str(e)}")


@router.post(
    "/assessments/start",
    response_model=SuccessResponse[AssessmentResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_assessment(
    payload: AssessmentStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[AssessmentResponse]:
    assessment = await assessment_service.start_assessment(
        db, current_user=current_user, payload=payload
    )
    return success_response(
        message="Assessment queued",
        data=AssessmentResponse.model_validate(assessment),
        request_id=request.state.request_id,
    )


@router.get(
    "/assessments",
    response_model=SuccessResponse[AssessmentListResponse],
    summary="List assessments for the current user's tenant",
)
async def list_assessments(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=200),
    status: str | None = Query(default=None),
    sort: str = Query(default="newest", pattern="^(newest|oldest|score_asc|score_desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[AssessmentListResponse]:
    data = await dashboard_service.list_assessments(
        db,
        current_user=current_user,
        page=page,
        per_page=per_page,
        status=status,
        sort=sort,  # type: ignore[arg-type]
    )
    return success_response(
        message="Assessments retrieved",
        data=data,
        request_id=request.state.request_id,
    )


@router.get("/assessment/debug/latest", response_model=SuccessResponse[dict])
async def get_latest_assessment_debug(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[dict]:
    payload = await assessment_service.get_latest_assessment_debug(
        db,
        current_user=current_user,
    )
    return success_response(
        message="Latest assessment debug retrieved",
        data=payload,
        request_id=request.state.request_id,
    )


@router.get(
    "/assessments/{assessment_id}",
    response_model=SuccessResponse[AssessmentResponse],
)
async def get_assessment(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[AssessmentResponse]:
    assessment = await assessment_service.get_assessment(
        db, current_user=current_user, assessment_id=assessment_id
    )
    return success_response(
        message="Assessment retrieved",
        data=AssessmentResponse.model_validate(assessment),
        request_id=request.state.request_id,
    )


@router.get(
    "/assessments/{assessment_id}/findings",
    response_model=SuccessResponse[list[AssessmentFindingResponse]],
)
async def get_assessment_findings(
    assessment_id: UUID,
    request: Request,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[list[AssessmentFindingResponse]]:
    findings = await assessment_service.get_findings(
        db, current_user=current_user, assessment_id=assessment_id, pagination=pagination
    )
    return success_response(
        message="Assessment findings retrieved",
        data=[AssessmentFindingResponse.model_validate(finding) for finding in findings],
        request_id=request.state.request_id,
    )


@router.get(
    "/assessments/{assessment_id}/evidence",
    response_model=SuccessResponse[AssessmentEvidenceResponse],
)
async def get_assessment_evidence(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[AssessmentEvidenceResponse]:
    payload = await assessment_service.get_evidence(
        db,
        current_user=current_user,
        assessment_id=assessment_id,
    )
    return success_response(
        message="Assessment evidence retrieved",
        data=AssessmentEvidenceResponse.model_validate(payload),
        request_id=request.state.request_id,
    )


@router.get(
    "/assessment-failures/{assessment_id}",
    response_model=SuccessResponse[list[AssessmentFailureResponse]],
)
async def get_assessment_failures(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[list[AssessmentFailureResponse]]:
    payload = await assessment_service.get_assessment_failures(
        db,
        current_user=current_user,
        assessment_id=assessment_id,
    )
    return success_response(
        message="Assessment collector failures retrieved",
        data=[AssessmentFailureResponse.model_validate(item) for item in payload],
        request_id=request.state.request_id,
    )


@router.get(
    "/assessments/{assessment_id}/events",
    response_model=SuccessResponse[list[AssessmentEventResponse]],
)
async def get_assessment_events(
    assessment_id: UUID,
    request: Request,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[list[AssessmentEventResponse]]:
    events = await assessment_service.get_events(
        db, current_user=current_user, assessment_id=assessment_id, pagination=pagination
    )
    return success_response(
        message="Assessment events retrieved",
        data=[AssessmentEventResponse.model_validate(event) for event in events],
        request_id=request.state.request_id,
    )


@router.get(
    "/assessments/{assessment_id}/job",
    response_model=SuccessResponse[AssessmentJobResponse],
)
async def get_assessment_job(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[AssessmentJobResponse]:
    job = await assessment_service.get_job(
        db, current_user=current_user, assessment_id=assessment_id
    )
    return success_response(
        message="Assessment job retrieved",
        data=AssessmentJobResponse.model_validate(
            {
                "id": job.id,
                "assessment_id": job.assessment_id,
                "tenant_id": job.tenant_id,
                "status": job.status,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "current_stage": job.current_stage,
                "progress_pct": job.progress_pct,
                "worker_id": job.worker_id,
                "error_message": job.error_message,
                "metadata": job.metadata_payload,
                "created_at": job.created_at,
            }
        ),
        request_id=request.state.request_id,
    )


@router.get(
    "/assessments/{assessment_id}/recommendations",
    response_model=SuccessResponse[AssessmentRecommendationResponse],
)
async def get_assessment_recommendations(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[AssessmentRecommendationResponse]:
    payload = await assessment_service.get_recommendations(
        db, current_user=current_user, assessment_id=assessment_id
    )
    return success_response(
        message="Assessment recommendations retrieved",
        data=AssessmentRecommendationResponse.model_validate(payload),
        request_id=request.state.request_id,
    )


@router.get(
    "/assessments/{assessment_id}/score",
    response_model=SuccessResponse[AssessmentScoreResponse],
)
async def get_assessment_score(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[AssessmentScoreResponse]:
    payload = await assessment_service.get_score(
        db, current_user=current_user, assessment_id=assessment_id
    )
    return success_response(
        message="Assessment score retrieved",
        data=AssessmentScoreResponse.model_validate(payload),
        request_id=request.state.request_id,
    )


@router.get("/assessments/{assessment_id}/readiness", response_model=SuccessResponse[dict])
async def get_assessment_readiness(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[dict]:
    payload = await assessment_service.get_readiness_breakdown(
        db, current_user=current_user, assessment_id=assessment_id
    )
    return success_response(
        message="Assessment readiness retrieved",
        data=payload,
        request_id=request.state.request_id,
    )


@router.post(
    "/assessments/{assessment_id}/generate-report",
    response_model=SuccessResponse[GenerateReportResponse],
)
async def generate_assessment_report(
    assessment_id: UUID,
    request: Request,
    report_type: str = Query(default="docx", pattern="^(docx|pdf|both)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[GenerateReportResponse]:
    payload = await cra_report_service.generate_report_bundle(
        db,
        current_user=current_user,
        assessment_id=assessment_id,
        report_type=report_type,
    )
    return success_response(
        message="Assessment report generated",
        data=GenerateReportResponse.model_validate(payload),
        request_id=request.state.request_id,
    )


@router.get(
    "/assessments/{assessment_id}/report",
    response_model=SuccessResponse[ReportBundleResponse],
)
async def get_assessment_report(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[ReportBundleResponse]:
    payload = await cra_report_service.get_report_bundle(
        db,
        current_user=current_user,
        assessment_id=assessment_id,
    )
    return success_response(
        message="Assessment report retrieved",
        data=ReportBundleResponse.model_validate(payload),
        request_id=request.state.request_id,
    )


@router.get("/report-debug/{assessment_id}", response_model=SuccessResponse[dict])
@router.get("/assessment/report-debug/{assessment_id}", response_model=SuccessResponse[dict])
async def get_assessment_report_debug(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[dict]:
    payload = await cra_report_service.get_report_debug(
        db,
        current_user=current_user,
        assessment_id=assessment_id,
    )
    return success_response(
        message="Assessment report debug retrieved",
        data=payload,
        request_id=request.state.request_id,
    )


@router.post("/assessments/{assessment_id}/report/generate-debug")
async def generate_report_debug(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Debug endpoint to test simple report generation."""
    import logging
    import traceback
    from pathlib import Path as _Path

    logger = logging.getLogger(__name__)

    try:
        logger.info(f"[DEBUG] Testing simple report generation")

        from app.services.reporting.enhanced_report_generator import EnhancedReportGenerator

        # Create minimal data
        data = {
            'id': str(assessment_id),
            'tenant_id': str(assessment_id),
            'tenant_name': 'Test',
            'partner_name': 'Test',
            'created_at': __import__('datetime').datetime.now(),
            'overall_score': 50.0,
            'findings': [],
            'summary': {'total_parameters': 0, 'pass_count': 0, 'fail_count': 0,
                       'critical_count': 0, 'high_count': 0, 'medium_count': 0, 'low_count': 0},
        }

        gen = EnhancedReportGenerator(data)
        report_bytes = gen.generate()

        _Path("storage/reports").mkdir(parents=True, exist_ok=True)
        test_file = _Path("storage/reports/debug_test.docx")
        with open(test_file, 'wb') as f:
            f.write(report_bytes.getvalue())

        return {
            "status": "success",
            "message": "Report generated",
            "file_size": len(report_bytes.getvalue()),
            "file_path": str(test_file),
            "file_exists": test_file.exists(),
        }

    except Exception as exc:
        logger.error(f"[DEBUG] Failed: {exc}")
        logger.error(traceback.format_exc())

        return {
            "status": "error",
            "message": str(exc),
            "type": type(exc).__name__,
        }


@router.get("/assessments/{assessment_id}/report/download")
async def download_assessment_report(
    assessment_id: UUID,
    report_type: str = Query(default="pdf", pattern="^(pdf|docx)$"),
    company_name: str = Query(default=None),
    company_address: str = Query(default=None),
    logo_path: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Download report - fetches real assessment data and generates report with optional white-label customization."""
    from pathlib import Path as _Path
    import logging
    import asyncio
    import io as _io

    logger = logging.getLogger(__name__)

    try:
        logger.info(f"[DOWNLOAD] Starting for {assessment_id}, type={report_type}")
        logger.info(f"[DOWNLOAD] White-label: company={company_name}, address={company_address}")

        # Fetch real assessment data
        from app.services.reporting.assessment_report_data_service import AssessmentReportDataService
        from app.services.reporting.enhanced_report_generator import EnhancedReportGenerator

        logger.info(f"[DOWNLOAD] Fetching assessment data from database...")
        assessment_data = await AssessmentReportDataService.get_assessment_report_data(db, assessment_id)

        # Apply customization to assessment data
        if company_name:
            logger.info(f"[DOWNLOAD] Applying company name: {company_name}")
            assessment_data['tenant_name'] = company_name
            assessment_data['summary']['tenant_name'] = company_name
            assessment_data['summary']['organization_name'] = company_name

        if company_address:
            logger.info(f"[DOWNLOAD] Applying company address: {company_address}")
            assessment_data['company_address'] = company_address

        logger.info(f"[DOWNLOAD] Got {len(assessment_data.get('findings', []))} findings, generating report...")
        logger.info(f"[DOWNLOAD] Using logo: {logo_path if logo_path else 'None'}")
        logger.info(f"[DOWNLOAD] Company: {assessment_data.get('tenant_name')}")

        # Generate in thread to avoid blocking
        def gen_report():
            gen = EnhancedReportGenerator(assessment_data, logo_path=logo_path)
            return gen.generate()

        report_bytes = await asyncio.to_thread(gen_report)

        logger.info(f"[DOWNLOAD] Generated {len(report_bytes.getvalue())} bytes")

        # Save to disk
        _Path("storage/reports").mkdir(parents=True, exist_ok=True)
        timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')

        if report_type == "pdf":
            # Convert to PDF
            word_path = _Path(f"storage/reports/report_{timestamp}.docx")
            with open(word_path, 'wb') as f:
                f.write(report_bytes.getvalue())

            logger.info(f"[DOWNLOAD] Converting to PDF...")
            pdf_path = _Path(f"storage/reports/report_{timestamp}.pdf")

            def convert_pdf():
                from docx2pdf import convert
                convert(str(word_path), str(pdf_path))
                return pdf_path

            file_path = await asyncio.to_thread(convert_pdf)
            logger.info(f"[DOWNLOAD] PDF ready: {file_path}")

            media_type = "application/pdf"
            filename = file_path.name
        else:
            # Save Word directly
            file_path = _Path(f"storage/reports/report_{timestamp}.docx")
            with open(file_path, 'wb') as f:
                f.write(report_bytes.getvalue())

            logger.info(f"[DOWNLOAD] DOCX ready: {file_path}")
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = file_path.name

        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename,
        )

    except Exception as exc:
        logger.exception(f"[DOWNLOAD] Failed: {exc}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(exc)}")


@router.get(
    "/tenants/{tenant_id}/assessments",
    response_model=SuccessResponse[list[AssessmentResponse]],
)
async def list_tenant_assessments(
    tenant_id: str,
    request: Request,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[list[AssessmentResponse]]:
    assessments = await assessment_service.list_tenant_assessments(
        db, current_user=current_user, tenant_id=tenant_id, pagination=pagination
    )
    return success_response(
        message="Tenant assessments retrieved",
        data=[AssessmentResponse.model_validate(item) for item in assessments],
        request_id=request.state.request_id,
    )


@router.delete(
    "/assessments/{assessment_id}",
    response_model=SuccessResponse[dict],
    summary="Soft-delete an assessment",
)
async def delete_assessment(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[dict]:
    deleted_id = await dashboard_service.delete_assessment(
        db, current_user=current_user, assessment_id=assessment_id
    )
    return success_response(
        message="Assessment deleted",
        data={"success": True, "id": str(deleted_id)},
        request_id=request.state.request_id,
    )


@router.get(
    "/assessments/{assessment_id}/results",
    response_model=SuccessResponse[AssessmentResultsResponse],
    summary="Combined results for ResultsPage",
)
async def get_assessment_results(
    assessment_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[AssessmentResultsResponse]:
    data = await dashboard_service.get_assessment_results(
        db, current_user=current_user, assessment_id=assessment_id
    )
    return success_response(
        message="Assessment results retrieved",
        data=data,
        request_id=request.state.request_id,
    )
