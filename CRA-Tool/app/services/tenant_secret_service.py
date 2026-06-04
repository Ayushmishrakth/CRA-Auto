from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import BusinessLogicException
from app.db.models.tenant import ConnectedTenant


def _fernet() -> Fernet:
    key_material = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(key_material)
    return Fernet(key)


def store_client_secret(
    tenant: ConnectedTenant,
    *,
    secret_text: str,
    secret_id: str | None = None,
    expires_at: datetime | None,
) -> None:
    if not secret_text:
        raise BusinessLogicException("Microsoft Graph did not return a client secret value")
    tenant.encrypted_client_secret = _fernet().encrypt(secret_text.encode("utf-8")).decode("ascii")
    tenant.secret_id = secret_id
    tenant.secret_expires_at = expires_at
    tenant.secret_version = str(uuid.uuid4())


def decrypt_client_secret(tenant: ConnectedTenant) -> str:
    if not tenant.encrypted_client_secret:
        raise BusinessLogicException("Tenant client secret is not available")
    try:
        return _fernet().decrypt(tenant.encrypted_client_secret.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise BusinessLogicException("Tenant client secret could not be decrypted") from exc
