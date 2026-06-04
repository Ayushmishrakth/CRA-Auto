"""
Tenant API routes.
"""

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.pagination import PaginationParams, get_pagination_params
from app.core.responses import SuccessResponse, success_response
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.tenant import (
    TenantConnectRequest,
    TenantDeploymentDebugResponse,
    TenantDeploymentRequest,
    TenantDeploymentResponse,
    TenantDeploymentRuntimeDebugResponse,
    TenantDeploymentValidationResponse,
    TenantPermissionsResponse,
    TenantResponse,
)
from app.services import tenant_deployment_service, tenant_service

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post(
    "/connect",
    response_model=SuccessResponse[TenantResponse],
    status_code=status.HTTP_201_CREATED,
)
async def connect_tenant(
    payload: TenantConnectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[TenantResponse]:
    tenant = await tenant_service.connect_tenant(
        db, current_user=current_user, payload=payload
    )
    return success_response(
        message="Tenant connected",
        data=TenantResponse.model_validate(tenant),
        request_id=request.state.request_id,
    )


@router.get("", response_model=SuccessResponse[list[TenantResponse]])
async def list_tenants(
    request: Request,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[list[TenantResponse]]:
    tenants = await tenant_service.list_tenants(
        db, current_user=current_user, pagination=pagination
    )
    return success_response(
        message="Tenants retrieved",
        data=[TenantResponse.model_validate(tenant) for tenant in tenants],
        request_id=request.state.request_id,
    )


@router.get(
    "/deployment/debug",
    response_model=SuccessResponse[TenantDeploymentDebugResponse],
)
async def get_tenant_deployment_debug(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[TenantDeploymentDebugResponse]:
    result = await tenant_deployment_service.get_deployment_debug(
        db,
        current_user=current_user,
    )
    return success_response(
        message="Tenant deployment debug retrieved",
        data=TenantDeploymentDebugResponse(**result),
        request_id=request.state.request_id,
    )


@router.get(
    "/deployment/runtime-debug",
    response_model=SuccessResponse[TenantDeploymentRuntimeDebugResponse],
)
async def get_tenant_deployment_runtime_debug(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[TenantDeploymentRuntimeDebugResponse]:
    result = await tenant_deployment_service.get_deployment_runtime_debug(
        db,
        current_user=current_user,
    )
    return success_response(
        message="Tenant deployment runtime debug retrieved",
        data=TenantDeploymentRuntimeDebugResponse(**result),
        request_id=request.state.request_id,
    )


@router.get(
    "/deployment/validate",
    response_model=SuccessResponse[TenantDeploymentValidationResponse],
)
async def validate_tenant_deployment(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    graph_access_token: str = Header(..., alias="X-Graph-Access-Token"),
) -> SuccessResponse[TenantDeploymentValidationResponse]:
    result = await tenant_deployment_service.validate_tenant_deployment(
        db,
        current_user=current_user,
        graph_access_token=graph_access_token,
    )
    return success_response(
        message="Tenant deployment validated",
        data=TenantDeploymentValidationResponse(**result),
        request_id=request.state.request_id,
    )


@router.get("/{tenant_id}", response_model=SuccessResponse[TenantResponse])
async def get_tenant(
    tenant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[TenantResponse]:
    tenant = await tenant_service.get_tenant(
        db, current_user=current_user, tenant_id=tenant_id
    )
    return success_response(
        message="Tenant retrieved",
        data=TenantResponse.model_validate(tenant),
        request_id=request.state.request_id,
    )


@router.delete("/{tenant_id}", response_model=SuccessResponse[TenantResponse])
async def disconnect_tenant(
    tenant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[TenantResponse]:
    tenant = await tenant_service.disconnect_tenant(
        db, current_user=current_user, tenant_id=tenant_id
    )
    return success_response(
        message="Tenant disconnected",
        data=TenantResponse.model_validate(tenant),
        request_id=request.state.request_id,
    )


@router.get(
    "/{tenant_id}/permissions",
    response_model=SuccessResponse[TenantPermissionsResponse],
)
async def get_tenant_permissions(
    tenant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[TenantPermissionsResponse]:
    tenant = await tenant_service.get_permissions(
        db, current_user=current_user, tenant_id=tenant_id
    )
    return success_response(
        message="Tenant permissions retrieved",
        data=TenantPermissionsResponse(
            tenant_id=tenant.tenant_id,
            permissions=tenant.granted_permissions or [],
            consent_status=tenant.consent_status,
            status=tenant.status,
        ),
        request_id=request.state.request_id,
    )


@router.post(
    "/deployment/start",
    response_model=SuccessResponse[TenantDeploymentResponse],
)
async def start_tenant_deployment(
    payload: TenantDeploymentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[TenantDeploymentResponse]:
    result = await tenant_deployment_service.deploy_tenant_access(
        db,
        current_user=current_user,
        tenant_id=payload.tenant_id,
        graph_access_token=payload.graph_access_token,
        redirect_uri=payload.redirect_uri,
    )
    return success_response(
        message="Tenant deployment started",
        data=TenantDeploymentResponse(**result),
        request_id=request.state.request_id,
    )


@router.post(
    "/deployment/validate-consent",
    response_model=SuccessResponse[TenantDeploymentResponse],
)
async def validate_tenant_consent(
    payload: TenantDeploymentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[TenantDeploymentResponse]:
    result = await tenant_deployment_service.validate_admin_consent(
        db,
        current_user=current_user,
        tenant_id=payload.tenant_id,
        graph_access_token=payload.graph_access_token,
    )
    return success_response(
        message="Tenant admin consent validated",
        data=TenantDeploymentResponse(**result),
        request_id=request.state.request_id,
    )
