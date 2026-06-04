"""
CRA Assessment routes (Phase 2 stubs).

Full path: GET /api/v1/assessment/summary
"""

from fastapi import APIRouter

from app.schemas.assessment_schema import AssessmentSummaryResponse
from app.services import assessment_service

router = APIRouter(prefix="/assessment", tags=["Assessment"])


@router.get(
    "/summary",
    response_model=AssessmentSummaryResponse,
    summary="Assessment summary",
    description="Placeholder until Copilot Readiness Assessment logic is implemented.",
)
def assessment_summary() -> AssessmentSummaryResponse:
    return assessment_service.get_assessment_summary()
