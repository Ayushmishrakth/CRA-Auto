"""Dump findings for assessment 1a788844-ea6d-49e4-8bff-8999728dc5c7."""
import asyncio, sys, json
sys.path.insert(0, ".")

from app.db.session import AsyncSessionLocal
from sqlalchemy import text

ASSESSMENT_ID = "1a788844ea6d49e48bff8999728dc5c7"

NINE = {
    "secure_score_percentage",
    "compliance_score_overview",
    "audit_log_retention_duration",
    "active_sites_count",
    "restricted_access_to_microsoft_entra_admin_centre",
    "self_service_password_reset_authentication_method",
    "user_consent_for_applications",
    "emergency_access_accounts",
    "custom_banned_password_list",
}


async def check():
    async with AsyncSessionLocal() as db:
        # Assessment header
        r = await db.execute(text(
            "SELECT id, status, overall_score, identity_score, security_score, "
            "compliance_score, collaboration_score FROM assessments WHERE id=:id"
        ), {"id": ASSESSMENT_ID})
        a = r.fetchone()
        if not a:
            print("Not found - trying hex without dashes")
            return

        print(f"Assessment: {a[0]}")
        print(f"  status={a[1]}  overall={a[2]}")
        print(f"  identity={a[3]}  security={a[4]}  compliance={a[5]}  collab={a[6]}")
        print()

        # Get all findings
        fr = await db.execute(text(
            "SELECT id, status, raw_value, severity, score_contribution "
            "FROM assessment_findings WHERE assessment_id=:id ORDER BY status"
        ), {"id": ASSESSMENT_ID})
        findings = fr.fetchall()
        print(f"Total findings: {len(findings)}")
        print()

        by_status: dict[str, list] = {}
        for f in findings:
            fid, fstatus, raw_json, sev, score_c = f
            raw = json.loads(raw_json) if raw_json else {}
            key = raw.get("parameter_key", "unknown")
            ct = raw.get("collector_type", raw.get("collection_method", "?"))
            by_status.setdefault(fstatus or "unknown", []).append((key, ct, raw))

        for status, items in sorted(by_status.items()):
            print(f"=== {status.upper()} ({len(items)}) ===")
            for key, ct, raw in items:
                marker = " <<< TARGET" if key in NINE else ""
                print(f"  [{ct:12}] {key}{marker}")

        print()
        print("=== 9 TARGET PARAMETERS ===")
        all_by_key = {}
        for f in findings:
            fid, fstatus, raw_json, sev, score_c = f
            raw = json.loads(raw_json) if raw_json else {}
            key = raw.get("parameter_key", "unknown")
            all_by_key[key] = (fstatus, raw)

        for key in sorted(NINE):
            if key in all_by_key:
                fstatus, raw = all_by_key[key]
                av = raw.get("actual_value", "N/A")
                print(f"  {key}")
                print(f"    status={fstatus}  actual={str(av)[:100]}")
            else:
                print(f"  {key}  — NOT IN FINDINGS")


if __name__ == "__main__":
    asyncio.run(check())
