import json
from pathlib import Path


def test_teams_controls_map_to_teams_master_script():
    manifest = json.loads(Path("app/config/collector_manifest.json").read_text())
    teams = [item for item in manifest if item["service"] == "teams"]
    assert teams
    assert all(item["script"] == "app/powershell/teams/teams_master.ps1" for item in teams)
    assert Path("app/powershell/teams/teams_master.ps1").exists()
