from pathlib import Path

import pytest

from app.services.csv_ingestion.csv_ingestion_service import CsvIngestionError, read_csv_rows


def test_csv_validation_rejects_missing_headers(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(CsvIngestionError):
        read_csv_rows(path)


def test_csv_validation_rejects_duplicate_rows(tmp_path: Path):
    path = tmp_path / "dupes.csv"
    path.write_text("id,value\n1,a\n1,a\n", encoding="utf-8")
    with pytest.raises(CsvIngestionError):
        read_csv_rows(path)


def test_csv_validation_rejects_missing_required_fields(tmp_path: Path):
    path = tmp_path / "schema.csv"
    path.write_text("id,value\n1,a\n", encoding="utf-8")
    with pytest.raises(CsvIngestionError):
        read_csv_rows(path, required_fields=["status"])
