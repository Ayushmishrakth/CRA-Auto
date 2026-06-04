"""
Authentication API schemas — Microsoft login + CRA JWT only.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MicrosoftLoginRequest(BaseModel):
    """
    Sent by MSAL React after Microsoft login.

    The frontend passes the Microsoft ID token; backend validates and returns CRA JWT.
    """

    id_token: str = Field(
        ...,
        min_length=10,
        description="Microsoft ID token from MSAL acquireTokenSilent / loginPopup",
    )


class TokenResponse(BaseModel):
    """CRA tokens used for all subsequent API requests."""

    access_token: str = Field(..., description="CRA JWT access token")
    refresh_token: str = Field(..., description="CRA JWT refresh token")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(..., description="Access token lifetime in seconds")


class RefreshTokenRequest(BaseModel):
    """Body for POST /api/v1/auth/refresh."""

    refresh_token: str = Field(..., description="CRA refresh token from login response")


class LogoutRequest(BaseModel):
    """Optional refresh token to revoke on logout."""

    refresh_token: str | None = Field(
        default=None,
        description="Revoke this refresh token; access token revoked via Authorization header",
    )


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    """Authenticated user profile from GET /api/v1/auth/me."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    microsoft_oid: str
    microsoft_tid: str
    email: EmailStr
    display_name: str
    role: str
    is_active: bool
    connected_tenants: list[str]
    created_at: datetime
    last_login: datetime | None
