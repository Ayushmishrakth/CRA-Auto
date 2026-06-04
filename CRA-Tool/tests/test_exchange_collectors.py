import json
from pathlib import Path


def test_exchange_controls_map_to_exchange_master_script():
    manifest = json.loads(Path("app/config/collector_manifest.json").read_text())
    exchange = [item for item in manifest if item["service"] == "exchange"]
    assert exchange
    assert all(item["script"] == "app/powershell/exchange/exchange_master.ps1" for item in exchange)
    assert Path("app/powershell/exchange/exchange_master.ps1").exists()
