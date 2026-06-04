import json
from pathlib import Path


def test_sharepoint_controls_map_to_sharepoint_master_script():
    manifest = json.loads(Path("app/config/collector_manifest.json").read_text())
    sharepoint = [item for item in manifest if item["service"] == "sharepoint"]
    assert sharepoint
    assert all(item["script"] == "app/powershell/sharepoint/sharepoint_master.ps1" for item in sharepoint)
    assert Path("app/powershell/sharepoint/sharepoint_master.ps1").exists()
