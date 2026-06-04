import pytest

from app.services.graph import GraphAuthError, GraphRuntime


async def test_graph_runtime_fails_closed_without_tenant_token():
    runtime = GraphRuntime()
    with pytest.raises(GraphAuthError):
        await runtime.collect_endpoint(
            tenant_id="tenant-a",
            user_id="user-a",
            endpoint="/users",
        )
