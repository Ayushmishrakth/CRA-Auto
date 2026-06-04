from __future__ import annotations

from typing import Any

from app.services.graph.graph_auth_service import GraphAuthService
from app.services.graph.graph_client import GraphClient
from app.services.graph.graph_retry_service import retry_graph_call


class GraphRuntime:
    def __init__(self, *, auth_service: GraphAuthService | None = None) -> None:
        self.auth_service = auth_service or GraphAuthService()

    async def collect_endpoint(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        endpoint: str,
    ) -> dict[str, Any]:
        token = await self.auth_service.get_delegated_token(tenant_id=tenant_id, user_id=user_id)
        client = GraphClient(access_token=token)
        return await retry_graph_call(lambda: client.get(endpoint))
