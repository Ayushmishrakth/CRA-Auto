"""
Centralized application settings — Microsoft Entra ID + CRA JWT.

Pydantic Settings best practices:
- Explicit fields for every supported .env variable
- extra="ignore" so unknown env keys never crash startup
- @lru_cache singleton for performance
- Validators for security-sensitive values
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and .env.

    Env names are case-insensitive (ORGANIZATION_NAME → organization_name).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Prevent crashes when .env has extra keys (e.g. future vars, comments mis-parsed)
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "CRA Backend"
    app_version: str = "2.0.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    organization_name: str = Field(
        default="",
        description="Customer organization display name (CRA branding / reports)",
    )
    cra_frontend_url: str = Field(
        default="http://localhost:3000",
        description="Public CRA frontend base URL used for tenant deployment redirects",
    )
    cra_word_template_path: str | None = Field(
        default=None,
        description="Optional path to the master CRA Word report template",
    )
    rate_limit_requests_per_minute: int = Field(
        default=180,
        ge=1,
        le=10000,
        description="Maximum HTTP requests per client IP per rolling minute.",
    )
    max_parameter_workbook_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1024,
        description="Maximum uploaded CRA parameter workbook size in bytes.",
    )

    # --- CORS (CRA React frontend) ---
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        description="Allowed origins for browser clients (MSAL React)",
    )

    # --- Database ---
    database_url: str = "sqlite:///./cra.db"

    # --- Redis / Celery runtime ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    celery_task_always_eager: bool = False
    celery_task_time_limit_seconds: int = 1800
    celery_task_soft_time_limit_seconds: int = 1740

    # --- CRA internal JWT ---
    secret_key: str = Field(
        default="CHANGE-ME-use-openssl-rand-hex-32",
        description="Signing key for CRA JWT tokens",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Microsoft Entra ID ---
    azure_client_id: str = Field(
        default="00000000-0000-0000-0000-000000000000",
        description="App registration Application (client) ID",
    )
    azure_login_client_id: str | None = Field(
        default=None,
        description="SPA Application (client) ID whose Microsoft ID tokens are accepted for login",
    )
    azure_tenant_id: str = Field(
        default="common",
        description="Entra tenant ID, or 'common' / 'organizations' for multi-tenant",
    )
    azure_client_secret: str | None = None
    azure_authority: str | None = None
    azure_redirect_uri: str | None = None

    # --- Certificate app-only auth (PnP/SharePoint + Teams collectors) ---
    # MicrosoftTeams and PnP.PowerShell cannot authenticate app-only with a
    # client secret — they require a certificate. These configure the per-tenant
    # cert used by Connect-CraPnP / Connect-CraTeams in cra_common.ps1.
    cra_cert_pfx_path: str | None = Field(
        default=None,
        description="Path to the app-registration certificate PFX (private key). Defaults to <repo>/secrets/cra_cert.pfx when unset.",
    )
    cra_cert_pfx_password: str | None = Field(
        default=None,
        description="Password protecting the certificate PFX (env CRA_CERT_PFX_PASSWORD).",
    )
    cra_cert_thumbprint: str | None = Field(
        default=None,
        description="Optional certificate thumbprint (alternative to the PFX path; loads from the local certificate store).",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_mode(cls, value):
        """Accept common deployment mode strings from process environments."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "yes", "on"}:
                return True
        return value

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_not_be_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("SECRET_KEY must not be empty")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        """Allow comma-separated string in .env: CORS_ORIGINS=http://localhost:3000,..."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def microsoft_authority(self) -> str:
        if self.azure_authority:
            return self.azure_authority.rstrip("/")
        return f"https://login.microsoftonline.com/{self.azure_tenant_id}"

    @property
    def microsoft_login_client_id(self) -> str:
        return self.azure_login_client_id or self.azure_client_id

    @property
    def microsoft_jwks_uri(self) -> str:
        return f"{self.microsoft_authority}/discovery/v2.0/keys"

    @property
    def deployment_success_redirect_uri(self) -> str:
        return f"{self.cra_frontend_url.rstrip('/')}/tenant/deployment-success"

    @property
    def resolved_celery_broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def resolved_celery_result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    """Cached settings — call get_settings() in tests to override via env."""
    return Settings()


settings = get_settings()
