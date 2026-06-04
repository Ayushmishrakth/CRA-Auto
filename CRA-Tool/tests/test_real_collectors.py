import json
from pathlib import Path


def test_no_generic_collector_is_mapped_in_manifest():
    manifest = json.loads(Path("app/config/collector_manifest.json").read_text())
    assert all("generic_collector.ps1" not in str(item.get("script", "")) for item in manifest)


def test_existing_collector_scripts_do_not_claim_mock_evidence():
    scripts = [
        path
        for path in Path("app/powershell").glob("**/*.ps1")
        if path.name != "generic_collector.ps1"
    ]
    mocked = [
        str(path)
        for path in scripts
        if "mock" in path.read_text(encoding="utf-8", errors="ignore").lower()
    ]
    assert mocked == []
