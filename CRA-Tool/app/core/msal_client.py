"""
MSAL client factory — Phase 4+ (Microsoft Graph, admin consent, token exchange).

Phase 3 login uses ID tokens from MSAL React; this module prepares server-side MSAL.
"""

from typing import Optional

import msal

from app.core.config import settings


def get_confidential_client() -> Optional[msal.ConfidentialClientApplication]:
    """
    Build MSAL confidential client when client secret is configured.

    Used for:
    - Microsoft Graph API calls
    - Admin consent / app registration workflows
    - On-behalf-of (OBO) token exchange
    """
    if not settings.azure_client_secret:
        return None

    return msal.ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        client_credential=settings.azure_client_secret,
        authority=settings.microsoft_authority,
    )
