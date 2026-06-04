from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from app.services.csv_ingestion.evidence_normalizer import normalize_evidence_row


class CsvIngestionError(RuntimeError):
    pass


def read_csv_rows(path: str | Path, *, required_fields: list[str] | None = None) -> list[dict[str, Any]]:
    csv_path = Path(path)
    if not csv_path.exists() or not csv_path.is_file():
        raise CsvIngestionError(f"CSV evidence file not found: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise CsvIngestionError(f"CSV evidence file is malformed or missing headers: {csv_path}")
        if any(name is None or not str(name).strip() for name in reader.fieldnames):
            raise CsvIngestionError(f"CSV evidence file contains invalid headers: {csv_path}")
        missing = set(required_fields or []) - set(reader.fieldnames)
        if missing:
            raise CsvIngestionError(f"CSV evidence file missing required fields {sorted(missing)}: {csv_path}")
        rows = [dict(row) for row in reader]
        if any(None in row for row in rows):
            raise CsvIngestionError(f"CSV evidence file contains malformed rows: {csv_path}")
        seen = set()
        for row in rows:
            key = tuple((field, row.get(field)) for field in reader.fieldnames)
            if key in seen:
                raise CsvIngestionError(f"CSV evidence file contains duplicate rows: {csv_path}")
            seen.add(key)
        return rows


def parse_csv_evidence(
    *,
    csv_path: str | Path,
    parameter_key: str,
    service: str,
    severity: str,
    source_script: str | None = None,
    required_fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    rows = read_csv_rows(csv_path, required_fields=required_fields)
    if not rows:
        raise CsvIngestionError(f"CSV evidence file is empty: {csv_path}")
    return [
        normalize_evidence_row(
            parameter_key=parameter_key,
            service=service,
            severity=severity,
            row=row,
            source_script=source_script,
            source_csv=str(csv_path),
        )
        for row in rows
    ]
