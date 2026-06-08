"""
Exchange Online OAuth token acquisition using client credentials flow.

Exchange PowerShell app-only auth requires an access token for
https://outlook.office365.com/.default — client secrets work here
(unlike Connect-ExchangeOnline certificate auth, which is a separate flow).
"""

from __future__ import annotations

import httpx

from app.utils.logger import logger


_EXCHANGE_SCOPE = "https://outlook.office365.com/.default"


async def get_exchange_access_token(
    tenant_id: str,
    client_id: str,
    client_secret: str,
) -> str | None:
    """Return an Exchange Online access token or None if the tenant has no Exchange licence."""
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.post(
                url,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": _EXCHANGE_SCOPE,
                    "grant_type": "client_credentials",
                },
            )
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                logger.info("[EXCHANGE_TOKEN] Exchange Online access token acquired for tenant %s", tenant_id)
                return token
            logger.warning("[EXCHANGE_TOKEN] Token response 200 but no access_token field for tenant %s", tenant_id)
            return None
        # 400 with AADSTS errors such as AADSTS500014 means Exchange is not provisioned — not a hard failure
        body = response.text[:300]
        logger.warning(
            "[EXCHANGE_TOKEN] Could not acquire Exchange Online token for tenant %s: HTTP %s %s",
            tenant_id, response.status_code, body,
        )
        return None
    except Exception as exc:
        logger.warning("[EXCHANGE_TOKEN] Exception acquiring Exchange Online token for tenant %s: %s", tenant_id, exc)
        return None
