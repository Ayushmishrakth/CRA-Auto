"""Direct live test of all 9 target collectors against WealthScape."""
import asyncio
import sys
sys.path.insert(0, ".")

from app.db.session import AsyncSessionLocal
from app.db.models.tenant import ConnectedTenant
from sqlalchemy import select
from app.services.graph_cra_collector_service import (
    collect_secure_score_percentage,
    collect_compliance_score_overview,
    collect_audit_log_retention_duration,
    collect_active_sites_count,
    collect_restricted_access_to_microsoft_entra_admin_centre,
    collect_self_service_password_reset_authentication_method,
    collect_user_consent_for_applications,
    collect_emergency_access_accounts,
    collect_custom_banned_password_list,
)

COLLECTORS = [
    ("secure_score_percentage",                               collect_secure_score_percentage),
    ("compliance_score_overview",                             collect_compliance_score_overview),
    ("audit_log_retention_duration",                          collect_audit_log_retention_duration),
    ("active_sites_count",                                    collect_active_sites_count),
    ("restricted_access_to_microsoft_entra_admin_centre",     collect_restricted_access_to_microsoft_entra_admin_centre),
    ("self_service_password_reset_authentication_method",     collect_self_service_password_reset_authentication_method),
    ("user_consent_for_applications",                         collect_user_consent_for_applications),
    ("emergency_access_accounts",                             collect_emergency_access_accounts),
    ("custom_banned_password_list",                           collect_custom_banned_password_list),
]


async def run():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ConnectedTenant).where(
                ConnectedTenant.tenant_id == "fe4eff9a-f69c-48c0-921d-8006a6d5beb2"
            )
        )
        tenant = result.scalar_one()
        print(f"Tenant: {tenant.tenant_name}  ({tenant.tenant_id})")
        print("=" * 80)
        print(f"{'Parameter':<52} {'Status':<28} {'Actual Value'}")
        print("-" * 80)

        for key, fn in COLLECTORS:
            try:
                r = await fn(tenant)
                status = r.get("status", "unknown")
                actual = r.get("raw_value", {}).get("actual_value", "N/A")
                print(f"{key:<52} {status:<28} {str(actual)[:60]}")
            except Exception as exc:
                print(f"{key:<52} {'EXCEPTION':<28} {str(exc)[:60]}")

        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(run())
