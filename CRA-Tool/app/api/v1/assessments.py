"""
Assessment API routes.
"""

import uuid
from uuid import UUID
from typing import Optional

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
from app.schemas.report import ReportBundleResponse
from app.services import assessment_service, dashboard_service
from app.services.reporting import cra_report_service

from pathlib import Path

router = APIRouter(tags=["Assessments"])



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


@router.post("/assessments/{assessment_id}/generate-report")
async def generate_assessment_report(
    request: Request,
    assessment_id: UUID,
    report_type: str = Query(default="docx", pattern="^(docx|pdf|both)$"),
    company_name: Optional[str] = Form(default=None),
    company_address: Optional[str] = Form(default=None),
    logo_file: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    logo_abs_path = None
    if logo_file and logo_file.filename:
        data = await logo_file.read()
        if data:
            ext = Path(logo_file.filename).suffix.lower() or '.png'
            logo_dir = Path('storage/logos')
            logo_dir.mkdir(parents=True, exist_ok=True)
            lf = (logo_dir / f'{assessment_id}_{uuid.uuid4().hex}{ext}').resolve()
            lf.write_bytes(data)
            logo_abs_path = str(lf)

    payload = await cra_report_service.generate_report_bundle(
        assessment_id=str(assessment_id),
        db=db,
        current_user=current_user,
        report_type=report_type,
        partner_name=(company_name or '').strip() or None,
        logo_path=logo_abs_path,
        company_address=(company_address or '').strip() or None,
    )

    if isinstance(payload, dict):
        artifacts = payload.get("artifacts", [])
        selected_artifact = next(
            (item for item in artifacts if item.get("report_type") == report_type),
            artifacts[0] if artifacts else None,
        )
        fp = (
            payload.get("file_path")
            or payload.get("docx_path")
            or (selected_artifact.get("file_path") or selected_artifact.get("storage_path") if selected_artifact else None)
        )
    else:
        fp = str(payload)
    if not fp:
        raise HTTPException(status_code=500, detail="Report generation did not return a file path")

    media_type = (
        "application/pdf"
        if report_type == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        path=fp,
        filename=f'CRA_Report_{assessment_id}.{report_type}',
        media_type=media_type,
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
    from app.core.exceptions import AppException

    try:
        try:
            artifact = await cra_report_service.get_report_artifact(
                db,
                current_user=current_user,
                assessment_id=assessment_id,
                report_type=report_type,
            )
        except FileNotFoundError:
            payload = await cra_report_service.generate_report_bundle(
                assessment_id=str(assessment_id),
                db=db,
                current_user=current_user,
                report_type=report_type,
                partner_name=(company_name or '').strip() or None,
                logo_path=logo_path,
                company_address=(company_address or '').strip() or None,
            )
            artifacts = payload.get("artifacts", []) if isinstance(payload, dict) else []
            artifact_payload = next(
                (item for item in artifacts if item.get("report_type") == report_type),
                artifacts[0] if artifacts else None,
            )
            if not artifact_payload:
                raise HTTPException(status_code=500, detail="Report generation did not return a file path")
            path = artifact_payload.get("storage_path") or artifact_payload.get("file_path")
        else:
            path = artifact.storage_path

        media_type = (
            "application/pdf"
            if report_type == "pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        return FileResponse(
            path=str(path),
            media_type=media_type,
            filename=f"Assessment_{assessment_id}.{report_type}",
        )

    except (HTTPException, AppException):
        raise
    except Exception as exc:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.exception(f"[DOWNLOAD] Failed: {exc}")
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
