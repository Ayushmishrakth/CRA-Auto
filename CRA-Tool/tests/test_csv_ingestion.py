from pathlib import Path

import pytest

from app.services.csv_ingestion import CsvIngestionError, parse_csv_evidence


def test_csv_ingestion_normalizes_real_rows(tmp_path: Path):
    csv_path = tmp_path / "Graph_Report.csv"
    csv_path.write_text("status,value,message\npass,enabled,ok\n", encoding="utf-8")

    rows = parse_csv_evidence(
        csv_path=csv_path,
        parameter_key="authentication_methods_enabled",
        service="entra",
        severity="high",
        source_script="entra-master.ps1",
    )

    assert rows[0]["parameter_key"] == "authentication_methods_enabled"
    assert rows[0]["pass_fail"] == "pass"
    assert rows[0]["source_csv"] == str(csv_path)


def test_csv_ingestion_fails_when_csv_missing(tmp_path: Path):
    with pytest.raises(CsvIngestionError):
        parse_csv_evidence(
            csv_path=tmp_path / "missing.csv",
            parameter_key="missing",
            service="entra",
            severity="high",
        )
