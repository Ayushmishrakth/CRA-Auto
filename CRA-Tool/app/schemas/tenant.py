"""
Tenant API schemas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TenantConnectRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=64)
    tenant_name: str | None = Field(default=None, max_length=255)
    granted_permissions: list[str] | None = None


class TenantDeploymentRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=64)
    graph_access_token: str = Field(..., min_length=20)
    redirect_uri: str | None = Field(default=None, max_length=1000)


class TenantDeploymentResponse(BaseModel):
    exchange_admin_role: str | None = None
    tenant_id: str
    tenant_name: str | None
    status: str
    deployment_status: str
    consent_status: str
    app_registration_id: str | None
    app_client_id: str | None
    application_object_id: str | None = None
    application_client_id: str | None = None
    service_principal_id: str | None
    admin_consent_url: str | None
    consent_url: str | None = None
    granted_permissions: dict[str, Any] | list[Any] | None
    secret_expires_at: datetime | None
    secret_expiration: datetime | None = None
    deployment_step: str | None = None
    deployment_timestamp: datetime | None = None
    redirect_uri: str | None = None
    deployment_error: str | None
    # Per-tenant certificate + Teams-role state for the "Connect Tenant" UI cert box.
    # Without this field the response_model silently strips it and the UI always
    # renders the "Certificate not yet generated" fallback.
    certificate: dict[str, Any] | None = None


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: str
    tenant_name: str | None
    consent_status: str
    deployment_status: str
    granted_permissions: dict[str, Any] | list[Any] | None
    status: str
    app_client_id: str | None = None
    application_client_id: str | None = None
    application_object_id: str | None = None
    service_principal_id: str | None = None
    admin_consent_url: str | None = None
    consent_url: str | None = None
    secret_expires_at: datetime | None = None
    secret_expiration: datetime | None = None
    deployment_step: str | None = None
    deployment_timestamp: datetime | None = None
    redirect_uri: str | None = None
    deployment_error: str | None = None
    last_assessment_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TenantPermissionsResponse(BaseModel):
    tenant_id: str
    permissions: dict[str, Any] | list[Any]
    consent_status: str
    status: str


class TenantDeploymentDebugResponse(BaseModel):
    tenant_id: str | None = None
    application_client_id: str | None = None
    application_object_id: str | None = None
    consent_url: str | None = None
    redirect_uri: str | None = None
    application_id: str | None
    client_id: str | None
    redirect_uri_expected: str | None
    redirect_uri_actual: list[str]
    service_principal_id: str | None
    deployment_status: str
    deployment_step: str | None
    deployment_error: str | None


class TenantDeploymentRuntimeDebugResponse(BaseModel):
    application_client_id: str | None
    application_object_id: str | None
    service_principal_id: str | None
    tenant_id: str | None
    redirect_uri: str | None
    consent_url: str | None
    deployment_status: str | None
    consent_status: str | None
    consent_url_client_id: str | None = None
    consent_url_matches_application_client_id: bool = False
    deployment_service_version: str


class TenantDeploymentValidationResponse(BaseModel):
    tenant_id: str
    deployment_valid: bool
    app_exists: bool
    app_id: str | None
    object_id: str | None
    service_principal_exists: bool
    redirect_uri_valid: bool
    consent_url: str | None


class TenantRepairResponse(BaseModel):
    needs_reconsent: bool
    consent_url: str
    tenant_id: str
    app_client_id: str | None
    permissions_patched: bool
    primary_domain: str | None
    exchange_admin_role: str | None = None
