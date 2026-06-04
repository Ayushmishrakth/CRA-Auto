"""
Assessment API routes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
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
from app.schemas.report import GenerateReportResponse, ReportBundleResponse
from app.services import assessment_service
from app.services.reporting import cra_report_service

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[GenerateReportResponse]:
    payload = await cra_report_service.generate_report_bundle(
        db,
        current_user=current_user,
        assessment_id=assessment_id,
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


@router.get("/assessments/{assessment_id}/report/download")
async def download_assessment_report(
    assessment_id: UUID,
    report_type: str = Query(default="pdf", pattern="^(pdf|docx)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    try:
        artifact = await cra_report_service.get_report_artifact(
            db,
            current_user=current_user,
            assessment_id=assessment_id,
            report_type=report_type,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    media_type = (
        "application/pdf"
        if report_type == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        artifact.storage_path,
        media_type=media_type,
        filename=f"copilot-readiness-assessment.{report_type}",
    )


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
