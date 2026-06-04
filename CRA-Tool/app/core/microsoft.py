"""
Microsoft Identity Platform — ID token validation.

Frontend (MSAL React) obtains the ID token; this module validates it server-side
before issuing CRA internal JWTs.

Uses PyJWT + JWKS (RS256). MSAL is used for authority/metadata alignment and
future server-side flows (Graph, admin consent, token exchange).
"""

from dataclasses import dataclass
from typing import Any

import jwt
from jwt import PyJWKClient

from app.core.config import settings
from app.utils.logger import logger

# MSAL is required for Phase 4 (Graph API, admin consent, OBO).
# Phase 3 validates ID tokens via PyJWT + Entra JWKS (standard API pattern).
import msal  # noqa: F401


@dataclass(frozen=True)
class MicrosoftUserClaims:
    """Normalized claims extracted from a validated Microsoft ID token."""

    oid: str
    tid: str
    email: str
    name: str
    raw: dict[str, Any]


class MicrosoftTokenValidationError(Exception):
    """Raised when a Microsoft ID token fails validation."""


def _extract_email(payload: dict[str, Any]) -> str | None:
    """Resolve email from standard Entra ID token claim names."""
    for key in ("email", "preferred_username", "upn"):
        value = payload.get(key)
        if value and isinstance(value, str):
            return value.lower()
    return None


def _validate_issuer(issuer: str, tenant_id: str) -> bool:
    """
    Accept issuer formats for single-tenant and multi-tenant tokens.

    Examples:
      https://login.microsoftonline.com/{tid}/v2.0
      https://sts.windows.net/{tid}/
    """
    allowed_prefixes = (
        f"https://login.microsoftonline.com/{tenant_id}",
        "https://login.microsoftonline.com/",
        f"https://sts.windows.net/{tenant_id}",
        "https://sts.windows.net/",
    )
    return any(issuer.startswith(prefix) for prefix in allowed_prefixes)


def validate_microsoft_id_token(id_token: str) -> MicrosoftUserClaims:
    """
    Validate a Microsoft ID token from MSAL React and return normalized claims.

    Validates signature (JWKS), expiry, audience, and required claims (oid, tid).
    """
    if not id_token or not id_token.strip():
        raise MicrosoftTokenValidationError("ID token is required")

    try:
        jwk_client = PyJWKClient(settings.microsoft_jwks_uri)
        signing_key = jwk_client.get_signing_key_from_jwt(id_token)

        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.microsoft_login_client_id,
            options={
                "verify_exp": True,
                "verify_aud": True,
                "verify_signature": True,
            },
        )
    except jwt.PyJWTError as exc:
        logger.warning("Microsoft ID token validation failed: %s", exc)
        raise MicrosoftTokenValidationError(
            f"Invalid Microsoft ID token: {exc}. "
            "Ensure AZURE_LOGIN_CLIENT_ID matches the frontend VITE_MSAL_CLIENT_ID."
        ) from exc

    oid = payload.get("oid")
    tid = payload.get("tid")
    name = payload.get("name") or ""
    email = _extract_email(payload)
    issuer = payload.get("iss", "")

    if not oid or not tid:
        raise MicrosoftTokenValidationError("Token missing required claims: oid, tid")

    if not email:
        raise MicrosoftTokenValidationError("Token missing email claim")

    if not _validate_issuer(issuer, tid):
        raise MicrosoftTokenValidationError("Invalid token issuer")

    logger.info(
        "Microsoft ID token validated — oid=%s tid=%s authority=%s",
        oid,
        tid,
        settings.microsoft_authority,
    )

    return MicrosoftUserClaims(
        oid=str(oid),
        tid=str(tid),
        email=email,
        name=str(name),
        raw=payload,
    )
