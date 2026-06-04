from __future__ import annotations

import asyncio
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.db.base  # noqa: F401
from app.db.models.assessment_parameter import AssessmentParameter
from app.db.models.assessment_rule import AssessmentRule
from app.db.session import AsyncSessionLocal
from app.services.registry_service import get_registry
from app.services.runtime_assessment_service import ensure_registry_seeded


async def main() -> None:
    registry = get_registry()
    official_keys = {item["parameter_key"] for item in registry.get_parameters()}

    async with AsyncSessionLocal() as db:
        await ensure_registry_seeded(db)
        await db.commit()

        parameters = list((await db.execute(select(AssessmentParameter))).scalars().all())
        active = [item for item in parameters if item.is_active]
        rules = list((await db.execute(select(AssessmentRule))).scalars().all())
        rule_parameter_ids = {item.parameter_id for item in rules}
        active_rule_count = sum(1 for item in active if item.id in rule_parameter_ids)
        db_keys = {item.parameter_key for item in active}
        duplicates = {
            key: count
            for key, count in Counter(item.parameter_key for item in active).items()
            if count > 1
        }

        print(f"official_parameters={len(official_keys)}")
        print(f"database_active_parameters={len(active)}")
        print(f"database_active_rules={active_rule_count}")
        print(f"database_inactive_legacy_parameters={len(parameters) - len(active)}")
        print(f"missing_active_parameters={sorted(official_keys - db_keys)}")
        print(f"legacy_active_parameters={sorted(db_keys - official_keys)}")
        print(f"duplicate_active_parameters={duplicates}")


if __name__ == "__main__":
    asyncio.run(main())
