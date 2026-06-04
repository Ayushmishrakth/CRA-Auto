"""
Assessment registry API routes.
"""

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.auth import get_current_active_user
from app.core.responses import SuccessResponse, success_response
from app.db.models.user import User
from app.services.registry_service import get_registry

router = APIRouter(prefix="/registry", tags=["Registry"])


@router.get(
    "/parameters",
    response_model=SuccessResponse[list[dict[str, Any]]],
)
async def list_registry_parameters(
    request: Request,
    _: User = Depends(get_current_active_user),
) -> SuccessResponse[list[dict[str, Any]]]:
    registry = get_registry()
    data = []

    for parameter in registry.get_parameters():
        key = parameter["parameter_key"]
        data.append(
            {
                **parameter,
                "rule": registry.get_rule_by_key(key) or {},
                "collector": registry.get_collector_by_key(key) or {},
                "recommendation": registry.get_recommendation_by_key(key) or {},
            }
        )

    return success_response(
        message="Assessment registry parameters retrieved",
        data=data,
        request_id=request.state.request_id,
    )
