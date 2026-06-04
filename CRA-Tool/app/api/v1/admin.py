"""
Admin API routes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.pagination import PaginationParams, get_pagination_params
from app.core.responses import SuccessResponse, success_response
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.schemas.admin import AssessmentParameterResponse, RuleUpdateRequest
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/parameters",
    response_model=SuccessResponse[list[AssessmentParameterResponse]],
)
async def list_parameters(
    request: Request,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> SuccessResponse[list[AssessmentParameterResponse]]:
    parameters = await admin_service.list_parameters(db, pagination=pagination)
    return success_response(
        message="Assessment parameters retrieved",
        data=[AssessmentParameterResponse.model_validate(item) for item in parameters],
        request_id=request.state.request_id,
    )


@router.put("/parameters/{id}/rule", response_model=SuccessResponse[dict])
async def update_parameter_rule(
    id: UUID,
    payload: RuleUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> SuccessResponse[dict]:
    rule = await admin_service.upsert_parameter_rule(db, parameter_id=id, payload=payload)
    return success_response(
        message="Assessment rule updated",
        data={"id": str(rule.id), "parameter_id": str(rule.parameter_id)},
        request_id=request.state.request_id,
    )


@router.post("/reset-tenant/{tenant_id}")
async def reset_tenant_assessment_data(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    return await admin_service.reset_tenant_assessment_data(db, tenant_id=tenant_id)
