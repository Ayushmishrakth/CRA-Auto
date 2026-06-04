"""
Health and monitoring API routes.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import SuccessResponse, success_response
from app.db.session import get_db
from app.schemas.health import ComponentHealth, HealthCheckResponse
from app.services import health_service

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=SuccessResponse[HealthCheckResponse])
async def health(request: Request) -> SuccessResponse[HealthCheckResponse]:
    payload = await health_service.get_system_health()
    return success_response(
        message="Health status retrieved",
        data=payload,
        request_id=request.state.request_id,
    )


@router.get("/db", response_model=SuccessResponse[ComponentHealth])
async def db_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ComponentHealth]:
    payload = await health_service.get_db_health(db)
    return success_response(
        message="Database health retrieved",
        data=payload,
        request_id=request.state.request_id,
    )


@router.get("/auth", response_model=SuccessResponse[ComponentHealth])
async def auth_health(request: Request) -> SuccessResponse[ComponentHealth]:
    payload = await health_service.get_auth_health()
    return success_response(
        message="Auth health retrieved",
        data=payload,
        request_id=request.state.request_id,
    )


@router.get("/system", response_model=SuccessResponse[HealthCheckResponse])
async def system_health(request: Request) -> SuccessResponse[HealthCheckResponse]:
    payload = await health_service.get_system_health()
    return success_response(
        message="System health retrieved",
        data=payload,
        request_id=request.state.request_id,
    )
