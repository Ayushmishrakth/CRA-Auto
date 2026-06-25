import json
from pathlib import Path

import pytest

from app.db.models.tenant import ConnectedTenant
from app.services import graph_cra_collector_service as collectors


def _tenant() -> ConnectedTenant:
    return ConnectedTenant(
        tenant_id="tenant-1",
        tenant_name="Tenant",
        app_client_id="client",
        encrypted_client_secret="secret",
    )


def test_teams_controls_map_to_teams_master_script():
    manifest = json.loads(Path("app/config/collector_manifest.json").read_text())
    teams = [item for item in manifest if item["service"] == "teams"]
    assert teams
    assert all(item["script"] == "app/powershell/teams/teams_master.ps1" for item in teams)
    assert Path("app/powershell/teams/teams_master.ps1").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "collector_name",
    [
        "collect_active_inactive_teams",
        "collect_activer_inactive_teams_users",
        "collect_minimum_number_of_owners",
        "collect_orphan_teams",
        "collect_teams_with_external_users",
        "collect_teams_with_external_guest_as_owner",
        "collect_sensitivity_labels_applied_to_teams",
    ],
)
async def test_teams_collectors_fail_when_teams_service_is_unavailable(monkeypatch, collector_name):
    async def unavailable(_tenant):
        return False

    async def should_not_collect(*_args, **_kwargs):
        raise AssertionError("collector continued after Teams availability failed")

    monkeypatch.setattr(collectors, "_teams_service_available", unavailable)
    monkeypatch.setattr(collectors, "_m365_report_rows", should_not_collect)
    monkeypatch.setattr(collectors, "_teams_with_owners_and_members", should_not_collect)
    monkeypatch.setattr(collectors, "_graph_client", should_not_collect)

    result = await getattr(collectors, collector_name)(_tenant())

    actual = result["raw_value"]["actual_value"]
    evidence = result["raw_value"]["evidence"]
    assert result["status"] == "fail"
    assert actual["service_available"] is False
    assert actual["service"] == "Microsoft Teams"
    assert evidence["service_available"] is False
