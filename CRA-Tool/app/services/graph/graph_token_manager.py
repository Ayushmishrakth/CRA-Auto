from __future__ import annotations

from app.services.graph.graph_auth_service import GraphAuthError


class GraphTokenManager:
    async def refresh_token(self, *, tenant_id: str, refresh_token: str | None = None) -> str:
        if not refresh_token:
            raise GraphAuthError("Missing Microsoft Graph refresh token for tenant-scoped collection")
        raise GraphAuthError("Microsoft Graph refresh flow is not wired to a tenant token store yet")
