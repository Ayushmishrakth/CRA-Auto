import json
from pathlib import Path


def test_entra_controls_map_to_entra_master_script():
    manifest = json.loads(Path("app/config/collector_manifest.json").read_text())
    entra = [item for item in manifest if item["service"] == "entra"]
    assert entra
    assert all(item["script"] == "app/powershell/entra/entra_master.ps1" for item in entra)
    assert Path("app/powershell/entra/entra_master.ps1").exists()
