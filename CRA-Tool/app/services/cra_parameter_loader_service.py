from __future__ import annotations

import hashlib
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicException
from app.db.models.cra_parameter import CraParameter, CraParameterVersion
from app.db.models.user import User
from scripts.build_registry import ValidationReport, build_registries, extract_records


def _utc_version() -> str:
    return datetime.now(timezone.utc).strftime("cra-%Y%m%d%H%M%S")


def _source_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _decimal_weight(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("1.0")


async def import_parameter_workbook(
    db: AsyncSession,
    *,
    current_user: User,
    filename: str,
    content: bytes,
    activate: bool = True,
) -> dict[str, Any]:
    if not content:
        raise BusinessLogicException("Uploaded CRA parameter workbook is empty")
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise BusinessLogicException("CRA parameter import requires an .xlsx or .xlsm workbook")

    source_hash = _source_hash(content)
    existing = await db.scalar(
        select(CraParameterVersion).where(CraParameterVersion.source_hash == source_hash)
    )
    if existing is not None:
        parameter_count = await db.scalar(
            select(func.count(CraParameter.id)).where(CraParameter.version_id == existing.id)
        )
        return {
            "version_id": existing.id,
            "version": existing.version,
            "source_hash": existing.source_hash,
            "source_filename": existing.source_filename,
            "parameter_count": int(parameter_count or 0),
            "is_active": existing.is_active,
            "validation_report": existing.validation_report,
            "already_imported": True,
        }

    suffix = Path(filename).suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)

    try:
        extraction_report = ValidationReport()
        records = extract_records(temp_path, extraction_report)
        if not records:
            raise BusinessLogicException("No CRA parameter records were found in the uploaded workbook")
        registries, report = build_registries(records)
        report.errors.extend(extraction_report.errors)
        report.warnings.extend(extraction_report.warnings)
        report.stats["source_filename"] = filename
        report.stats["source_hash"] = source_hash
        report.stats["source_records"] = len(records)
        validation_report = {
            "errors": report.errors,
            "warnings": report.warnings,
            "stats": report.stats,
        }
        if report.errors:
            raise BusinessLogicException(
                "CRA parameter workbook failed validation",
                details=validation_report,
            )
    finally:
        temp_path.unlink(missing_ok=True)

    if activate:
        await db.execute(update(CraParameterVersion).values(is_active=False))

    version = CraParameterVersion(
        version=_utc_version(),
        source_filename=filename,
        source_hash=source_hash,
        imported_by=current_user.id,
        imported_at=datetime.now(timezone.utc),
        is_active=activate,
        validation_report=validation_report,
    )
    db.add(version)
    await db.flush()

    for item in registries["parameters"]:
        db.add(
            CraParameter(
                version_id=version.id,
                parameter_key=item["parameter_key"],
                display_name=item["display_name"],
                domain=item["domain"],
                category=item.get("category"),
                technology=item.get("technology"),
                severity=item["severity"],
                weight=_decimal_weight(item.get("scoring_weight")),
                pass_criteria=item.get("pass_criteria"),
                fail_criteria=item.get("fail_criteria"),
                criteria_expression=(
                    next(
                        (
                            rule.get("expression")
                            for rule in registries["rules"]
                            if rule.get("parameter_key") == item["parameter_key"]
                        ),
                        None,
                    )
                ),
                collector_type=item["collector_type"],
                graph_endpoint=item.get("graph_endpoint") or None,
                powershell_mapping=item.get("powershell_mapping") or None,
                portal_mapping=item.get("portal_mapping") or None,
                expected_output=item.get("expected_output") or None,
                copilot_relevance=item.get("copilot_relevance") or None,
                is_active=True,
                source_ref=item.get("source_refs"),
            )
        )

    await db.commit()
    await db.refresh(version)
    return {
        "version_id": version.id,
        "version": version.version,
        "source_hash": version.source_hash,
        "source_filename": version.source_filename,
        "parameter_count": len(registries["parameters"]),
        "is_active": version.is_active,
        "validation_report": version.validation_report,
        "already_imported": False,
    }


async def list_parameter_versions(db: AsyncSession) -> list[CraParameterVersion]:
    result = await db.execute(
        select(CraParameterVersion).order_by(CraParameterVersion.imported_at.desc())
    )
    return list(result.scalars().all())
