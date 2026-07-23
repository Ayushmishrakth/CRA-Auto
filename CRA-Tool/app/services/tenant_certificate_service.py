"""
Per-tenant certificate lifecycle for PowerShell app-only authentication.

The MicrosoftTeams and PnP.PowerShell modules cannot authenticate app-only with a
client secret — they require a certificate. This service generates a self-signed
certificate per connected tenant, stores the PFX (private key) + password encrypted
at rest with the app secret key, and hands the decrypted PFX to the assessment
runtime so Connect-CraTeams / Connect-CraPnP can use it automatically.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import secrets
from typing import Any

from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from app.core.config import settings
from app.db.models.tenant import ConnectedTenant

CERT_VALID_DAYS = 730  # 2 years


def _fernet() -> Fernet:
    # Same derivation as tenant_secret_service so all tenant secrets share one key.
    key_material = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key_material))


def generate_tenant_certificate(tenant_id: str) -> dict[str, Any]:
    """Generate an RSA-2048 self-signed cert (CN=CRA-{tenant_id}) valid 2 years.

    Returns pfx_bytes (private key + cert), a random pfx_password, der_bytes
    (public cert for Azure keyCredentials upload) and the SHA-1 thumbprint
    (the value Azure AD / the local cert store use to identify the cert).
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"CRA-{tenant_id}")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=CERT_VALID_DAYS))
        .sign(key, hashes.SHA256())
    )
    password = secrets.token_urlsafe(24)
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=f"CRA-{tenant_id}".encode("utf-8"),
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode("utf-8")),
    )
    der_bytes = cert.public_bytes(serialization.Encoding.DER)
    thumbprint = cert.fingerprint(hashes.SHA1()).hex().upper()
    return {
        "pfx_bytes": pfx_bytes,
        "pfx_password": password,
        "der_bytes": der_bytes,
        "thumbprint": thumbprint,
    }


def store_certificate_on_tenant(tenant: ConnectedTenant, cert: dict[str, Any]) -> None:
    """Encrypt and persist the certificate material onto the tenant row."""
    fernet = _fernet()
    tenant.cert_pfx_encrypted = fernet.encrypt(cert["pfx_bytes"]).decode("ascii")
    tenant.cert_pfx_password_encrypted = fernet.encrypt(cert["pfx_password"].encode("utf-8")).decode("ascii")
    tenant.cert_thumbprint = cert["thumbprint"]
    tenant.cert_der_b64 = base64.b64encode(cert["der_bytes"]).decode("ascii")
    tenant.cert_status = "generated"


def load_certificate_from_tenant(tenant: ConnectedTenant) -> tuple[bytes, str] | None:
    """Return (pfx_bytes, pfx_password) for a tenant, or None if no cert stored."""
    if not tenant.cert_pfx_encrypted:
        return None
    fernet = _fernet()
    pfx_bytes = fernet.decrypt(tenant.cert_pfx_encrypted.encode("ascii"))
    password = ""
    if tenant.cert_pfx_password_encrypted:
        password = fernet.decrypt(tenant.cert_pfx_password_encrypted.encode("ascii")).decode("utf-8")
    return pfx_bytes, password


def certificate_der_b64(tenant: ConnectedTenant) -> str | None:
    """Base64 DER of the public cert, for manual keyCredentials upload if needed."""
    return tenant.cert_der_b64
