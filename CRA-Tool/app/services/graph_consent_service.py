from __future__ import annotations

from urllib.parse import urlencode


def build_admin_consent_url(*, tenant_id: str, client_id: str, redirect_uri: str | None = None) -> str:
    query = {"client_id": client_id}
    if redirect_uri:
        query["redirect_uri"] = redirect_uri
    return f"https://login.microsoftonline.com/{tenant_id}/adminconsent?{urlencode(query)}"
