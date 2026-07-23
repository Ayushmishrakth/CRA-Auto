from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_artifact import AssessmentArtifact
from app.db.models.assessment_recommendation import AssessmentRecommendation
from app.db.models.assessment_report import AssessmentReport
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User
from app.services.assessment_service import get_assessment
from app.services.reporting.cra_chart_service import build_chart_data
from app.services.reporting.cra_narrative_service import build_narrative
from app.services.reporting.cra_risk_engine import aggregate_findings
from app.services.reporting.cra_summary_service import build_summary
from app.services.reporting.report_customization import get_customization_for_pdf, clear_customization
from app.services.registry_service import get_registry


REPORT_ROOT = Path("storage/reports")
DEFAULT_REPORT_COMPANY_NAME = "TechPlusTalent"
DEFAULT_REPORT_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "techplustalent-logo.png"


def resolve_report_branding(
    *,
    partner_name: str | None = None,
    logo_path: str | None = None,
    company_address: str | None = None,
) -> dict[str, str | None]:
    """Apply default report branding when no customization is supplied. Logo only, NOT customer names."""
    resolved_logo = (logo_path or "").strip() or None
    if not resolved_logo and DEFAULT_REPORT_LOGO_PATH.exists():
        resolved_logo = str(DEFAULT_REPORT_LOGO_PATH)

    return {
        "partner_name": (partner_name or "").strip() or None,
        "logo_path": resolved_logo,
        "company_address": (company_address or "").strip() or None,
    }


SERVICE_ORDER = [
    "Entra ID",
    "Exchange Online",
    "Microsoft Purview",
    "Microsoft Teams",
    "OneDrive",
    "SharePoint",
    "Licensing",
    "Microsoft 365",
]
SEVERITY_MAP = {
    'critical': 'Critical',
    'high': 'High',
    'medium': 'Medium',
    'low': 'Low',
    'info': 'Informational',
    'informational': 'Informational',
    'none': 'Informational',
    '': 'Informational',
}

CANONICAL_PARAMETER_TITLES = {
    "entra - tenant creation by non-admin": "Entra - Tenant Creation by Non-Admins",
    "cap policies for risky sign-ins": "CAP Policies for Risky Sign-Ins",
    "entra - third party app integrations": "Entra - Third-Party App Integrations",
    "tenant collaboration invitations": "Tenant Collaboration Invitation",
    "account enabled": "Number of accounts enabled",
    "admin consent workflow": "Administrator Consent Workflows",
    "devices without compliance policies": "Device without Compliance Policies",
    "mailboxes status (active/inactive)": "Mailbox Status (Active/Inactive)",
    "active /inactive teams": "Active/Inactive Teams",
    "third-party apps allowed": "Third Party apps allowed",
    "guest access enabled / disabled": "Guest access enabled/disabled",
    "activer/inactive teams users": "Active/Inactive Teams Users",
}

CANONICAL_SERVICE_OVERRIDES = {
    "teams - channel email addresses": "Microsoft Teams",
    "customer lockbox": "Entra ID",
}


def _as_number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_percent(value: Any) -> int:
    number = _as_number(value, 0.0)
    if 0 < number <= 1:
        number *= 100
    return round(number)


def _evidence_actual(evidence: Any) -> Any:
    if not isinstance(evidence, dict):
        return {}
    actual = evidence.get("actual_value")
    if actual is not None:
        return actual
    payload = evidence.get("payload")
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, dict):
            raw = result.get("raw_value")
            if isinstance(raw, dict):
                return raw.get("actual_value", raw)
    return evidence


def _ratio_from_counts(actual: dict[str, Any]) -> int:
    active = actual.get("active_users")
    total = actual.get("total_users") or actual.get("all_users")
    if isinstance(total, list):
        total = len(total)
    if isinstance(active, list):
        active = len(active)
    active_num = _as_number(active, 0.0)
    total_num = _as_number(total, 0.0)
    if total_num > 0:
        return round((active_num / total_num) * 100)
    return 0


def _activity_pct(parameter_rows: list[dict[str, Any]], parameter_key: str, ratio_keys: tuple[str, ...]) -> int:
    for row in parameter_rows:
        if row.get("parameter_key") != parameter_key:
            continue
        actual = _evidence_actual(row.get("evidence"))
        if not isinstance(actual, dict):
            return 0
        for ratio_key in ratio_keys:
            if ratio_key in actual:
                if ratio_key == "inactive_ratio":
                    active = _as_number(actual.get("active_users"), 0.0)
                    inactive = _as_number(actual.get("inactive_users"), 0.0)
                    if active + inactive <= 0:
                        return 0
                    return round(100 - _normalize_percent(actual.get(ratio_key)))
                return _normalize_percent(actual.get(ratio_key))
        for pct_key in ("active_pct", "active_percent", "active_percentage", "percentage"):
            if pct_key in actual:
                return _normalize_percent(actual.get(pct_key))
        return _ratio_from_counts(actual)
    return 0


def _copilot_license_counts(parameter_rows: list[dict[str, Any]]) -> tuple[int, int]:
    keys = {
        "copilot_prerequisite_licenses",
        "copilot_license_eligibility",
        "users_eligible_for_copilot_license",
        "m365_copilot_license_eligibility",
    }
    for row in parameter_rows:
        key = str(row.get("parameter_key") or "")
        if key not in keys and "eligible" not in key and "license" not in key:
            continue
        actual = _evidence_actual(row.get("evidence"))
        if not isinstance(actual, dict):
            continue
        eligible = actual.get("eligible_users") or actual.get("copilot_eligible_users") or actual.get("licensed_users")
        total = actual.get("total_users") or actual.get("user_count") or actual.get("users")
        if isinstance(eligible, list):
            eligible = len(eligible)
        if isinstance(total, list):
            total = len(total)
        eligible_num = int(_as_number(eligible, 0))
        total_num = int(_as_number(total, 0))
        if eligible_num or total_num:
            return eligible_num, total_num
    return 0, 0


def _tenant_user_count(parameter_rows: list[dict[str, Any]]) -> int:
    for preferred_key in ("user_information", "account_enabled", "users_without_mfa", "guest_users_count"):
        for row in parameter_rows:
            if row.get("parameter_key") != preferred_key:
                continue
            actual = _evidence_actual(row.get("evidence"))
            if not isinstance(actual, dict):
                continue
            for key in ("total_users", "user_count", "users"):
                value = actual.get(key)
                if isinstance(value, list):
                    value = len(value)
                count = int(_as_number(value, 0))
                if count:
                    return count
    return 0


def _extract_active_pct(all_findings: list[dict[str, Any]], param_key: str) -> int:
    """Extract active percentage from report finding evidence."""
    for finding in all_findings:
        if str(finding.get("parameter_key", "")) != param_key:
            continue
        try:
            raw = finding.get("raw_value", {})
            if isinstance(raw, str):
                import json
                raw = json.loads(raw)
            if not isinstance(raw, dict):
                continue
            actual = raw.get("actual_value")
            if isinstance(actual, dict):
                raw = actual
            # NOTE: the collectors store *_ratio fields as percentages (0-100) via _percent(),
            # NOT as 0-1 fractions. _normalize_percent multiplies by 100 ONLY when the value is
            # a 0-1 fraction, so it correctly handles both forms. The previous unconditional
            # "* 100" produced impossible values (e.g. 80 -> 8000%, inactive 20 -> -1900%).
            if "active_ratio" in raw:
                return max(0, min(100, _normalize_percent(raw["active_ratio"])))
            if "read_ratio" in raw:
                return max(0, min(100, _normalize_percent(raw["read_ratio"])))
            if "active_pct" in raw:
                return max(0, min(100, round(float(raw["active_pct"]))))
            if "active_percent" in raw:
                return max(0, min(100, round(float(raw["active_percent"]))))
            if "inactive_ratio" in raw:
                active = _as_number(raw.get("active_users"), 0.0)
                inactive = _as_number(raw.get("inactive_users"), 0.0)
                if active + inactive <= 0:
                    return 0
                return max(0, min(100, round(100 - _normalize_percent(raw["inactive_ratio"]))))
            active_users = raw.get("active_users", 0)
            total_users = raw.get("total_users", 0)
            if total_users and float(total_users) > 0:
                return max(0, min(100, round(float(active_users) / float(total_users) * 100)))
        except Exception:
            pass
    return 0

SKU_FRIENDLY_NAMES = {
    "6fd2c87f-b296-42f0-b197-1e91e994b900": "Office 365 E1",
    "18181a46-0d4e-45cd-891e-60aabd171b4e": "Office 365 E1",
    "c7df2760-2c81-4ef7-b578-5b5392b571df": "Office 365 E5",
    "b05e124f-c7cc-45a0-a6aa-8cf78c946968": "Enterprise Mobility + Security E5",
    "f30db892-07e9-47e9-837c-80727f46fd3d": "Microsoft Flow Free",
    "bc946dac-7877-4271-b2f7-99d2db13cd2c": "Microsoft Forms (Plan E1)",
    "57ff2da0-773e-42df-b2af-ffb7a2317929": "Microsoft Teams",
    "0f9b09cb-62d1-4ff4-9129-43f4996f83f4": "Exchange Online (Kiosk)",
    "o365biz": "Business Basic",
    "spo_e1": "SharePoint Online (Plan 1)",
}


def _chart_actual(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("evidence") or row.get("raw_value") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return {}
    if not isinstance(raw, dict):
        return {}
    actual = _evidence_actual(raw)
    if isinstance(actual, dict) and "users" not in actual:
        # The per-user list (with assignedLicenses) lives in the nested "evidence"
        # block; _evidence_actual collapses to actual_value, which omits it. Re-attach
        # it so the license / user-info charts can read real per-user data instead of
        # falling back to a 0-licensed placeholder.
        nested = raw.get("evidence")
        if isinstance(nested, dict) and isinstance(nested.get("users"), list):
            actual = {**actual, "users": nested["users"]}
    return actual if isinstance(actual, dict) else raw


def _chart_lookup(parameter_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in parameter_rows:
        key = str(row.get("parameter_key") or "")
        if key:
            lookup[key] = _chart_actual(row)
    return lookup


def _assigned_licenses(user: dict[str, Any]) -> list[Any]:
    for key in ("assignedLicenses", "assigned_licenses", "licenses", "licenseDetails"):
        value = user.get(key)
        if isinstance(value, list):
            return value
    return []


def _license_name(plan: Any) -> str:
    if isinstance(plan, dict):
        sku = str(
            plan.get("skuId")
            or plan.get("sku_id")
            or plan.get("skuPartNumber")
            or plan.get("sku_part_number")
            or plan.get("name")
            or ""
        )
    else:
        sku = str(plan or "")
    return SKU_FRIENDLY_NAMES.get(sku, sku[:20] if sku else "Unknown")


# Priority-ordered mapping of subscribed-SKU part-number token -> friendly license category.
# Each user is placed in the first (highest-tier) category any of their SKUs match, so the
# license chart shows the manual's category breakdown instead of a Licensed/Unlicensed split.
LICENSE_CATEGORY_RULES: list[tuple[str, str]] = [
    ("COPILOT", "Copilot"),
    ("SPE_E5", "Microsoft 365 E5"),
    ("ENTERPRISEPREMIUM", "Office 365 E5"),
    ("SPE_E3", "Microsoft 365 E3"),
    ("ENTERPRISEPACK", "Office 365 E3"),
    ("SPB", "Business Premium"),
    ("O365_BUSINESS_PREMIUM", "Business Standard"),
    ("BUSINESS_STANDARD", "Business Standard"),
    ("STANDARDWOFFPACK", "Business Standard"),
    ("O365_BUSINESS_ESSENTIALS", "Business Basic"),
    ("BUSINESS_BASIC", "Business Basic"),
    ("O365_BUSINESS", "Apps for Business"),
    ("EXCHANGEENTERPRISE", "Exchange Online"),
    ("EXCHANGESTANDARD", "Exchange Online"),
]


def _license_category_for_parts(parts: list[str]) -> str:
    upper = [str(p or "").upper() for p in parts if p]
    for token, name in LICENSE_CATEGORY_RULES:
        if any(token in part for part in upper):
            return name
    return "Other Licensed"


def _subscribed_sku_map(parameter_rows: list[dict[str, Any]]) -> dict[str, str]:
    """Build a skuId -> skuPartNumber map from any finding that carries subscribedSkus."""
    def _find(node: Any) -> list | None:
        if isinstance(node, dict):
            value = node.get("value")
            if isinstance(value, list) and value and isinstance(value[0], dict) and "skuPartNumber" in value[0]:
                return value
            for child in node.values():
                found = _find(child)
                if found:
                    return found
        return None
    for row in parameter_rows:
        raw = row.get("evidence") or row.get("raw_value")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                continue
        skus = _find(raw)
        if skus:
            return {str(s.get("skuId")): str(s.get("skuPartNumber") or "") for s in skus if isinstance(s, dict)}
    return {}


def _license_chart_counts(
    rv_lookup: dict[str, dict[str, Any]],
    *,
    eligible_users: int,
    total_users: int,
    sku_id_to_part: dict[str, str] | None = None,
) -> dict[str, int]:
    users: list[Any] = []
    for key in ("guest_users_count", "account_enabled", "user_information"):
        raw_users = rv_lookup.get(key, {}).get("users")
        if isinstance(raw_users, list) and raw_users:
            users = raw_users
            break

    sku_id_to_part = sku_id_to_part or {}
    # Real per-user SKU-category breakdown (mirrors the manual license pie). Requires the
    # per-user assignedLicenses AND the subscribedSkus skuId->partNumber map. Each user is
    # counted once in their highest-tier category; users with no license are Unlicensed.
    if users and sku_id_to_part:
        category_counts: dict[str, int] = {}
        licensed_seen = False
        for user in users:
            if not isinstance(user, dict):
                continue
            assigned = _assigned_licenses(user)
            parts = [
                sku_id_to_part.get(str(item.get("skuId") or item.get("sku_id") or ""), "")
                for item in assigned if isinstance(item, dict)
            ]
            parts = [part for part in parts if part]
            if parts:
                licensed_seen = True
                category = _license_category_for_parts(parts)
            else:
                category = "Unlicensed"
            category_counts[category] = category_counts.get(category, 0) + 1
        if licensed_seen:
            return {label: count for label, count in category_counts.items() if count > 0}

    # Detailed per-SKU breakdown is unavailable — hide the chart rather than render a
    # misleading Licensed/Unlicensed-only pie that does not match the manual layout.
    return {}


def _user_info_chart_data(rv_lookup: dict[str, dict[str, Any]]) -> tuple[dict[str, int], int]:
    user_info = rv_lookup.get("user_information", {})
    total_users = int(_as_number(user_info.get("total_users") or user_info.get("user_count"), 0))
    field_completion = user_info.get("field_completion")
    if isinstance(field_completion, dict) and field_completion:
        fields = {
            str(field): max(int(_as_number(value, 0)), 0)
            for field, value in field_completion.items()
        }
        if not total_users:
            total_users = max(fields.values(), default=0)
        return fields, total_users

    users = user_info.get("users")
    if isinstance(users, list) and users:
        field_keys = [
            ("First Name", ("firstName", "givenName", "first_name")),
            ("Last Name", ("lastName", "surname", "last_name")),
            ("Job Title", ("jobTitle", "job_title")),
            ("Department", ("department",)),
            ("Manager", ("manager", "managerDisplayName", "manager_display_name")),
            ("City", ("city",)),
            ("Country", ("country", "countryOrRegion")),
            ("Office Location", ("officeLocation", "office_location")),
        ]
        total_users = len(users)
        fields: dict[str, int] = {}
        for label, keys in field_keys:
            fields[label] = sum(
                1
                for user in users
                if isinstance(user, dict) and any(user.get(key) for key in keys)
            )
        return fields, total_users

    complete_users = int(_as_number(user_info.get("complete_users"), 0))
    total_users = total_users or int(_as_number(user_info.get("total_users"), complete_users))
    if not total_users:
        return {}, 0
    return {
        "First Name": total_users,
        "Last Name": total_users,
        "Job Title": complete_users,
        "Department": complete_users,
        "Manager": complete_users,
        "City": complete_users,
        "Country": complete_users,
        "Office Location": complete_users,
    }, total_users


def _active_total(raw: dict[str, Any], *, active_key: str = "active_users", total_key: str = "total_users") -> tuple[int, int]:
    active = raw.get(active_key, 0)
    total = raw.get(total_key, 0)
    if isinstance(active, list):
        active = len(active)
    if isinstance(total, list):
        total = len(total)
    active_num = int(_as_number(active, 0))
    total_num = int(_as_number(total, 0))
    if total_num <= 0 and "inactive_users" in raw:
        total_num = active_num + int(_as_number(raw.get("inactive_users"), 0))
    if total_num <= 0:
        for ratio_key in ("active_ratio", "read_ratio"):
            if ratio_key in raw:
                return max(int(round(_normalize_percent(raw.get(ratio_key)))), 0), 100
    return max(active_num, 0), max(total_num, 0)


def _activity_chart_counts(rv_lookup: dict[str, dict[str, Any]]) -> dict[str, tuple[int, int]]:
    outlook = rv_lookup.get("number_of_emails_read_received", {})
    return {
        "SharePoint": _active_total(rv_lookup.get("active_users_on_sharepoint", {})),
        "OneDrive": _active_total(rv_lookup.get("total_active_users_on_onedrive", {})),
        "Teams": _active_total(rv_lookup.get("activer_inactive_teams_users", {})),
        "Outlook": _active_total(outlook, active_key="engaged_users", total_key="total_users"),
    }

REPORT_ORDER = {
    # Entra ID
    "custom_banned_password_list": 1,
    "restricted_access_to_microsoft_entra_admin_centre": 2,
    "emergency_access_accounts": 3,
    "devices_without_compliance_policies": 4,
    "authentication_methods_enabled": 5,
    "entra_tenant_creation_by_non_admin": 6,
    "global_administrator_accounts": 7,
    "self_service_password_reset_authentication_method": 8,
    "tenant_collaboration_invitations": 9,
    "admin_consent_workflow": 10,
    "cap_policies_for_risky_sign_ins": 11,
    "conditional_access_policies_exclusion": 12,
    "user_consent_for_applications": 13,
    "entra_third_party_app_integrations": 14,
    "users_without_mfa": 15,
    "auto_expiration_policy_for_inactive_m365_groups": 16,
    "customer_lockbox": 17,
    "guest_invite_settings": 18,
    "guest_users_count": 19,
    "user_information": 20,
    "account_enabled": 21,
    # Exchange Online
    "mailboxes_status_active_inactive": 101,
    "external_storage_providers_in_owa": 102,
    "mailbox_storage_usage": 103,
    "full_calendar_schedules_able_to_be_shared_externally": 104,
    "number_of_emails_read_received": 105,
    "number_of_emails_sent": 106,
    # Microsoft Purview
    "audit_logs_enabled": 201,
    "secure_score_percentage": 202,
    "sensitivity_labels_configured_and_applied": 203,
    "sensitivity_labels_applied_to_teams": 204,
    "compliance_score_overview": 205,
    "information_protection_labels_applied": 206,
    "dlp_rules_configured": 207,
    "audit_log_retention_duration": 208,
    # Microsoft Teams
    "copilot_integration_enabled": 301,
    "third_party_apps_allowed": 302,
    "active_inactive_teams": 303,
    "minimum_number_of_owners": 304,
    "teams_with_external_users": 305,
    "meeting_policies_configuration": 306,
    "orphan_teams": 307,
    "teams_with_external_guest_as_owner": 308,
    "meeting_transcription_enabled": 309,
    "guest_access_enabled_disabled": 310,
    "teams_lobby_bypass": 311,
    "teams_file_storage_option": 312,
    "activer_inactive_teams_users": 313,
    "teams_meeting_chat": 314,
    "meeting_recording_retention_policies": 315,
    "teams_channel_email_addresses": 316,
    # OneDrive
    "external_sharing_settings": 401,
    "days_to_retain_a_deleted_user_s_onedrive": 402,
    "total_active_users_on_onedrive": 403,
    # SharePoint
    "permission_setting_for_anyone_links": 501,
    "getting_all_sites_with_sensitivity_keywords_on_a_tenant": 502,
    "sharing_settings_external_internal": 503,
    "sharepoint_and_onedrive_guest_access_expiry": 504,
    "expiration_policy_for_anyone_links": 505,
    "inactive_site_policies": 506,
    "active_sites_count": 507,
    "site_ownership_policies": 508,
    "active_users_on_sharepoint": 509,
    "sharepoint_modern_authentication": 510,
    "storage_quota_consumption": 511,
}


async def generate_report_bundle(
    *args,
    assessment_id: str | UUID | None = None,
    db: AsyncSession | None = None,
    current_user: User = None,
    report_type: str = "docx",
    partner_name: str = DEFAULT_REPORT_COMPANY_NAME,
    logo_path: str = None,
    company_address: str = None,
) -> dict[str, Any]:
    import logging
    logger = logging.getLogger(__name__)

    branding = resolve_report_branding(
        partner_name=partner_name,
        logo_path=logo_path,
        company_address=company_address,
    )
    partner_name = branding["partner_name"]
    logo_path = branding["logo_path"]
    company_address = branding["company_address"]

    print(f'[SERVICE] START partner={partner_name} logo={logo_path}')

    try:
        if args:
            if isinstance(args[0], AsyncSession):
                db = args[0]
                if len(args) > 1:
                    assessment_id = args[1]
            else:
                assessment_id = args[0]
                if len(args) > 1:
                    db = args[1]
        if db is None or assessment_id is None:
            raise ValueError("generate_report_bundle requires db and assessment_id")

        normalized_report_type = _normalize_report_type(report_type)

        # Convert assessment_id string to UUID if needed
        if isinstance(assessment_id, str):
            assessment_id = UUID(assessment_id)

        report_data = await build_report_data(db, current_user=current_user, assessment_id=assessment_id)
        print(f'[SERVICE] build_report_data completed successfully')

        # CRITICAL: Do NOT override assessment data with branding defaults
        # Use assessment data for customer names (from actual tenant being assessed)
        # Only use branding for logos and company address
        if partner_name:
            # Only override if explicitly provided (custom branding)
            report_data['partner_name'] = partner_name

        assessment = report_data["assessment"]
        target_dir = REPORT_ROOT / str(assessment.id)
        tenant_name = _safe_report_filename(report_data["summary"].get("tenant_name") or report_data["summary"].get("customer_name") or assessment.tenant_id)
        generated_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_stem = f"Copilot_Readiness_Assessment_{tenant_name}_{generated_stamp}"

        # Generate DOCX using report_builder
        from app.services.reporting.report_builder import build_docx_report

        target_dir.mkdir(parents=True, exist_ok=True)
        docx_path = target_dir / f"{report_stem}.docx"
        print(f'[SERVICE] Building DOCX to {docx_path}')

        # Build report
        # CRITICAL: Pass None for company_name/partner_name so build_docx_report uses assessment data
        build_docx_report(
            assessment_data=report_data,
            output_path=str(docx_path),
            company_name=None,
            company_address=company_address,
            logo_path=logo_path,
            partner_name=partner_name,
        )
        print(f'[SERVICE] DOCX build completed')

        logger.info(f"[REPORT] DOCX generated successfully: {docx_path}")

        print(f'[SERVICE] Deleting old artifacts')
        await db.execute(delete(AssessmentReport).where(AssessmentReport.assessment_id == assessment.id))
        artifacts: list[AssessmentReport] = []
        if normalized_report_type in {"docx", "both"}:
            docx_artifact = AssessmentReport(
                assessment_id=assessment.id,
                report_type="docx",
                report_status="generated",
                storage_path=str(docx_path),
                generated_by=current_user.id,
                metadata_json={**report_data["metadata"], "source": "docx_template"},
            )
            db.add(docx_artifact)
            artifacts.append(docx_artifact)
            assessment.report_path = str(docx_path)

        if normalized_report_type in {"pdf", "both"}:
            pdf_path = target_dir / f"{report_stem}.pdf"
            report_data["logo_path"] = logo_path
            generated_pdf = await _convert_docx_to_pdf_async(docx_path, pdf_path)
            pdf_artifact = AssessmentReport(
                assessment_id=assessment.id,
                report_type="pdf",
                report_status="generated",
                storage_path=str(generated_pdf),
                generated_by=current_user.id,
                metadata_json={**report_data["metadata"], "source": "docx_to_pdf"},
            )
            db.add(pdf_artifact)
            artifacts.append(pdf_artifact)
            if normalized_report_type == "pdf":
                assessment.report_path = str(generated_pdf)

        print(f'[SERVICE] Committing to database')
        await db.commit()
        for artifact in artifacts:
            await db.refresh(artifact)

        # Clear customization after report generation
        clear_customization(assessment_id)

        print(f'[SERVICE] SUCCESS returning artifacts count={len(artifacts)}')
        return {
            "assessment_id": assessment.id,
            "status": "generated",
            "artifacts": [_artifact_payload(artifact) for artifact in artifacts],
            "summary": report_data["summary"],
            "analytics": report_data["analytics"],
        }
    except Exception as e:
        logger.error(f'[SERVICE] FAILED: {e}', exc_info=True)
        print(f'[SERVICE] EXCEPTION: {e}')
        raise


def _normalize_report_type(report_type: str) -> str:
    value = (report_type or "docx").strip().lower()
    if value not in {"docx", "pdf", "both"}:
        raise ValueError("Report type must be one of: docx, pdf, both")
    return value


async def get_report_bundle(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> dict[str, Any]:
    report_data = await build_report_data(db, current_user=current_user, assessment_id=assessment_id)
    result = await db.execute(
        select(AssessmentReport)
        .where(AssessmentReport.assessment_id == assessment_id)
        .order_by(AssessmentReport.generated_at.desc())
    )
    artifacts = list(result.scalars().all())
    return {
        "assessment_id": assessment_id,
        "status": "generated" if artifacts else "not_generated",
        "download_ready": bool(artifacts),
        "artifacts": [_artifact_payload(item) for item in artifacts],
        "summary": report_data["summary"],
        "analytics": report_data["analytics"],
    }


async def get_report_artifact(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
    report_type: str = "pdf",
) -> AssessmentReport:
    await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    result = await db.execute(
        select(AssessmentReport)
        .where(
            AssessmentReport.assessment_id == assessment_id,
            AssessmentReport.report_type == report_type,
        )
        .order_by(AssessmentReport.generated_at.desc())
        .limit(1)
    )
    artifact = result.scalars().first()
    if artifact is None:
        raise FileNotFoundError("Report artifact has not been generated")
    return artifact


async def get_report_debug(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> dict[str, Any]:
    report_data = await build_report_data(db, current_user=current_user, assessment_id=assessment_id)
    assessment = report_data["assessment"]
    findings = await _load_findings(db, assessment.id)
    recommendations = await _load_recommendations(db, assessment.id, assessment.tenant_id)
    artifacts = await _load_artifacts(db, assessment.id, assessment.tenant_id)
    report_result = await db.execute(
        select(AssessmentReport).where(AssessmentReport.assessment_id == assessment_id)
    )
    reports = list(report_result.scalars().all())
    scores = [
        assessment.overall_score,
        assessment.identity_score,
        assessment.security_score,
        assessment.compliance_score,
        assessment.collaboration_score,
        assessment.licensing_score,
    ]
    return {
        "assessment_status": assessment.status,
        "tenant_id": assessment.tenant_id,
        "artifact_count": len(artifacts),
        "finding_count": len(findings),
        "recommendation_count": len(recommendations),
        "report_count": len(reports),
        "findings_count": report_data["metadata"]["finding_count"],
        "scores_count": len([score for score in scores if score is not None]),
        "recommendations_count": report_data["metadata"]["recommendation_count"],
        "sections_generated": report_data["metadata"]["sections_generated"],
        "missing_sections": report_data["metadata"]["missing_sections"],
    }


async def build_report_data(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> dict[str, Any]:
    assessment = await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    tenant_result = await db.execute(
        select(ConnectedTenant).where(ConnectedTenant.tenant_id == assessment.tenant_id)
    )
    tenant = tenant_result.scalars().first()
    findings = await _load_findings(db, assessment.id)
    recommendations = await _load_recommendations(db, assessment.id, assessment.tenant_id)
    artifacts = await _load_artifacts(db, assessment.id, assessment.tenant_id)
    summary = build_summary(assessment=assessment, findings=findings, recommendations=recommendations)
    parameter_rows = _build_parameter_rows(findings, recommendations, artifacts)

    # FIX 1: READINESS SCORE - Build complete findings list from parameter_rows
    findings_list = [
        {
            'service_name': row.get('service', 'Unknown'),
            'service': row.get('service', 'Unknown'),
            'parameter_key': row.get('parameter_key', ''),
            'parameter': row.get('title', ''),
            'pillar': row.get('pillar', ''),
            'status': row.get('status', ''),
            'finding': 'Fail' if str(row.get('status', '')).strip().lower() == 'fail' else 'Pass',
            'severity': SEVERITY_MAP.get(str(row.get('severity', '')).lower().strip(), 'Informational'),
            'description': row.get('description', ''),
            'risk': row.get('risk', ''),
            'raw_value': row.get('evidence', {}),
            'evidence': row.get('evidence', {}),
        }
        for row in parameter_rows
    ]


    pass_count = len([
        f for f in findings_list
        if str(f.get('finding', '')).strip().lower() == 'pass'
    ])
    fail_count = len([
        f for f in findings_list
        if str(f.get('finding', '')).strip().lower() == 'fail'
    ])
    total = len(findings_list)

    readiness_score = round(pass_count / total * 100, 2) if total > 0 else 0

    if readiness_score >= 80:
        level = 'Ready'
    elif readiness_score >= 50:
        level = 'Needs Improvement'
    else:
        level = 'Not Ready'

    # Pillar breakdown
    sec_f = [f for f in findings_list if 'security' in f.get('pillar', '').lower()]
    gov_f = [f for f in findings_list if 'governance' in f.get('pillar', '').lower()]
    bp_f = [f for f in findings_list if 'best' in f.get('pillar', '').lower()]

    def fail_pct(lst):
        if not lst: return 0
        return round(len([
            f for f in lst
            if str(f.get('finding', '')).strip().lower() == 'fail'
        ]) / len(lst) * 100)

    eligible_users, eligible_total_users = _copilot_license_counts(parameter_rows)
    total_users = eligible_total_users or _tenant_user_count(parameter_rows) or assessment.total_findings or total
    tenant_name = tenant.tenant_name if tenant and tenant.tenant_name else assessment.tenant_id

    # Keep every report output path on the same live score calculated from the
    # current parameter rows, instead of any stale score persisted earlier.
    assessment.overall_score = readiness_score
    summary = {
        **summary,
        "tenant_id": assessment.tenant_id,
        "tenant_name": tenant_name,
        "customer_name": tenant_name,
        "parameter_total": len(parameter_rows),
        "collected_total": len([row for row in parameter_rows if row["status"] in {"pass", "warning", "fail"}]),
        "failed_total": fail_count,
        "licensing_required_total": len([row for row in parameter_rows if row["status"] in {"licensing_required", "licensing_limitation"}]),
        "manual_validation_total": len([row for row in parameter_rows if row["status"] == "manual_validation_required"]),
        "not_collected_total": len([row for row in parameter_rows if row["status"] == "not_collected"]),
        "overall_readiness": readiness_score,
        "overall_score": readiness_score,
        "readiness_score": readiness_score,
        "readiness_status": level,
        "readiness_level": level,
        "pass_total": pass_count,
        "fail_total": fail_count,
        "total_findings": total,
        "deployment_recommendation": (
            "Proceed with Copilot rollout while continuing standard governance monitoring."
            if readiness_score >= 80
            else "Moderate remediation is recommended before enabling Copilot."
            if readiness_score >= 50
            else "Significant remediation is required prior to enabling Copilot in the production environment."
        ),
    }

    # Build complete assessment_data
    assessment_data = {
        'tenant_name': tenant_name,
        'assessment_date': assessment.created_at.strftime('%d %B %Y').lstrip('0') if assessment.created_at else '',
        'overall_score': readiness_score,
        'readiness_score': readiness_score,
        'readiness_level': level,
        'partner_name': DEFAULT_REPORT_COMPANY_NAME,
        'findings': findings_list,
        'findings_list': findings_list,
        'pass_count': pass_count,
        'gaps_count': fail_count,
        'total_params': total,
        'security_pct': fail_pct(sec_f),
        'governance_pct': fail_pct(gov_f),
        'best_practices_pct': fail_pct(bp_f),
        'eligible_users': eligible_users,
        'total_users': total_users,
        'onedrive_active_pct': _extract_active_pct(findings_list, 'total_active_users_on_onedrive'),
        'teams_active_pct': _extract_active_pct(findings_list, 'activer_inactive_teams_users'),
        'outlook_active_pct': _extract_active_pct(findings_list, 'number_of_emails_read_received'),
        'sharepoint_active_pct': _extract_active_pct(findings_list, 'active_users_on_sharepoint'),
    }
    rv_lookup = _chart_lookup(parameter_rows)
    user_info_fields, user_info_total = _user_info_chart_data(rv_lookup)
    assessment_data.update({
        'license_counts': _license_chart_counts(
            rv_lookup,
            eligible_users=eligible_users,
            total_users=total_users,
            sku_id_to_part=_subscribed_sku_map(parameter_rows),
        ),
        'user_info_fields': user_info_fields,
        'user_info_total': user_info_total,
        'activity_counts': _activity_chart_counts(rv_lookup),
    })

    summary = {**summary, **assessment_data}
    analytics_raw = aggregate_findings(findings)
    analytics = _build_report_analytics(summary=summary, parameter_rows=parameter_rows, assessment=assessment)
    analytics["assessment_scores"]["overall"] = readiness_score
    narrative = build_narrative(summary=summary, analytics=analytics_raw)
    sections = _build_sections_from_rows(parameter_rows)
    report_model = _build_report_model(
        assessment=assessment,
        summary=summary,
        analytics=analytics,
        parameter_rows=parameter_rows,
        recommendations=recommendations,
    )
    sections_generated = [section["title"] for section in report_model["sections"] if section["items"] or section.get("metrics")]

    import logging
    logging.getLogger('cra').info(
        f'[REPORT] Activity pcts: '
        f'od={assessment_data["onedrive_active_pct"]} '
        f'teams={assessment_data["teams_active_pct"]} '
        f'outlook={assessment_data["outlook_active_pct"]} '
        f'sp={assessment_data["sharepoint_active_pct"]}'
    )

    print(f"[SCORE] pass={pass_count} fail={fail_count} total={total} score={readiness_score}%")
    print(f"[DATA] findings={len(findings_list)} pass={pass_count} fail={fail_count} score={readiness_score}% level={level}")
    print(f"[DATA] sec={fail_pct(sec_f)}% gov={fail_pct(gov_f)}% bp={fail_pct(bp_f)}%")

    return {
        "assessment": assessment,
        "summary": summary,
        "analytics": analytics,
        "narrative": narrative,
        "sections": sections,
        "report_model": report_model,
        "parameter_rows": parameter_rows,
        **assessment_data,
        "metadata": {
            "finding_count": len(findings),
            "recommendation_count": len(recommendations),
            "failed_collector_count": len([item for item in artifacts if item.status != "collected"]),
            "parameter_count": len(parameter_rows),
            "sections_generated": sections_generated,
            "missing_sections": [
                section["title"] for section in report_model["sections"]
                if not section["items"] and not section.get("metrics")
            ],
            "evidence_policy": "missing collectors are NOT_COLLECTED; failed collectors are FAILED",
        },
    }


async def _load_findings(db: AsyncSession, assessment_id: UUID) -> list[AssessmentFinding]:
    result = await db.execute(
        select(AssessmentFinding)
        .options(selectinload(AssessmentFinding.parameter))
        .where(AssessmentFinding.assessment_id == assessment_id)
    )
    return list(result.scalars().all())


async def _load_recommendations(
    db: AsyncSession,
    assessment_id: UUID,
    tenant_id: str,
) -> list[AssessmentRecommendation]:
    result = await db.execute(
        select(AssessmentRecommendation).where(
            AssessmentRecommendation.assessment_id == assessment_id,
            AssessmentRecommendation.tenant_id == tenant_id,
        )
    )
    return list(result.scalars().all())


async def _load_artifacts(
    db: AsyncSession,
    assessment_id: UUID,
    tenant_id: str,
) -> list[AssessmentArtifact]:
    result = await db.execute(
        select(AssessmentArtifact).where(
            AssessmentArtifact.assessment_id == assessment_id,
            AssessmentArtifact.tenant_id == tenant_id,
        )
    )
    return list(result.scalars().all())


def _build_sections(
    findings: list[AssessmentFinding],
    recommendations: list[AssessmentRecommendation],
    artifacts: list[AssessmentArtifact],
) -> dict[str, list[dict[str, Any]]]:
    rec_by_key = {item.parameter_key: item for item in recommendations}
    sections = {service: [] for service in SERVICE_ORDER}
    for finding in findings:
        parameter = finding.parameter
        raw = finding.raw_value or {}
        parameter_key = raw.get("parameter_key") or getattr(parameter, "parameter_key", None) or ""
        service = _service_for_key(parameter_key, getattr(parameter, "category", None))
        recommendation = rec_by_key.get(parameter_key)
        sev_raw = str(finding.severity or "info").lower().strip()
        item = {
            "title": getattr(parameter, "parameter_name", None) or parameter_key,
            "service": service,
            "pillar": getattr(parameter, "category", None) or "Best Practice",
            "severity": SEVERITY_MAP.get(sev_raw, "Informational"),
            "finding": finding.evaluated_value or finding.status,
            "description": getattr(parameter, "copilot_relevance", None) or "Assessment control evaluated for Copilot readiness.",
            "risk": _risk_text(finding),
            "recommendation": recommendation.recommendation_text if recommendation else "Review and remediate this control.",
            "evidence": raw,
            "documentation_link": "",
        }
        sections.setdefault(service, []).append(item)
    collected_keys = {
        (finding.raw_value or {}).get("parameter_key") or getattr(finding.parameter, "parameter_key", None)
        for finding in findings
    }
    for artifact in artifacts:
        if artifact.status == "collected" or artifact.parameter_key in collected_keys:
            continue
        service = _service_for_key(artifact.parameter_key, artifact.service)
        sections.setdefault(service, []).append(
            {
                "title": artifact.parameter_key,
                "service": service,
                "pillar": artifact.service or "Unknown",
                "severity": "Informational",
                "finding": "NOT COLLECTED",
                "description": "Collector did not produce trusted evidence.",
                "risk": "No readiness conclusion was generated for this control because evidence was unavailable.",
                "recommendation": "Resolve collector configuration and re-run the assessment.",
                "evidence": {
                    "status": artifact.status,
                    "error": artifact.stderr,
                    "source_script": artifact.source_script,
                    "source_csv": artifact.source_csv,
                },
                "documentation_link": "",
            }
        )
    return {service: sections.get(service, []) for service in SERVICE_ORDER if sections.get(service)}


def _build_parameter_rows(
    findings: list[AssessmentFinding],
    recommendations: list[AssessmentRecommendation],
    artifacts: list[AssessmentArtifact],
) -> list[dict[str, Any]]:
    registry = get_registry()
    rec_by_key = {item.parameter_key: item for item in recommendations}
    registry_rec_by_key = {
        item["parameter_key"]: item
        for item in registry.get_recommendations()
    }
    finding_by_key = {
        ((finding.raw_value or {}).get("parameter_key") or getattr(finding.parameter, "parameter_key", None)): finding
        for finding in findings
    }
    artifact_by_key: dict[str, list[AssessmentArtifact]] = {}
    for artifact in artifacts:
        artifact_by_key.setdefault(artifact.parameter_key, []).append(artifact)

    rows: list[dict[str, Any]] = []
    for parameter in registry.get_parameters():
        key = parameter["parameter_key"]
        finding = finding_by_key.get(key)
        recommendation = rec_by_key.get(key)
        registry_recommendation = registry_rec_by_key.get(key, {})
        parameter_artifacts = artifact_by_key.get(key, [])
        latest_artifact = parameter_artifacts[-1] if parameter_artifacts else None
        status = _row_status(finding, latest_artifact)
        evidence = (finding.raw_value if finding else None) or _artifact_evidence(latest_artifact)
        description = _parameter_description(
            key=key,
            evidence=evidence,
            fallback=parameter.get("description") or parameter.get("copilot_relevance") or "",
        )
        title = _canonical_parameter_title(parameter.get("display_name") or key)
        service = _canonical_parameter_service(
            title,
            _service_for_key(key, parameter.get("category") or parameter.get("domain")),
        )
        row = {
            "parameter_key": key,
            "title": title,
            "service": service,
            "pillar": str(parameter.get("domain") or parameter.get("category") or "unclassified").replace("_", " ").title(),
            "category": parameter.get("category"),
            "technology": parameter.get("technology"),
            "severity": SEVERITY_MAP.get(str(finding.severity if finding else parameter.get("severity") or "info").lower().strip(), "Informational"),
            "display_severity": parameter.get("severity") or (finding.severity if finding else None) or "informational",
            "registry_severity": parameter.get("severity") or "",
            "status": status,
            "display_status": status,
            "report_order": REPORT_ORDER.get(key),
            "score_contribution": finding.score_contribution if finding else None,
            "finding": finding.evaluated_value if finding else "NOT COLLECTED",
            "actual_result": _actual_result_text(finding, latest_artifact),
            "expected_result": parameter.get("pass_criteria") or parameter.get("expected_output") or "",
            "description": description,
            "risk": parameter.get("risk") or "",
            "pass_criteria": parameter.get("pass_criteria") or "",
            "fail_criteria": parameter.get("fail_criteria") or "",
            "expected_output": parameter.get("expected_output") or "",
            "recommendation": (
                recommendation.recommendation_text
                if recommendation
                else _registry_recommendation_text(registry_recommendation)
            ),
            "remediation_steps": (
                recommendation.remediation_steps
                if recommendation
                else registry_recommendation.get("remediation_steps", [])
            ),
            "evidence": evidence,
            "documentation_url": parameter.get("documentation_url") or parameter.get("microsoft_doc_url") or "",
            "documentation_link": parameter.get("documentation_url") or parameter.get("microsoft_doc_url") or "",
            "registry_param": parameter,
            "artifact_status": latest_artifact.status if latest_artifact else None,
            "artifact_error": latest_artifact.stderr if latest_artifact else None,
            "source_script": latest_artifact.source_script if latest_artifact else None,
            "source_csv": latest_artifact.source_csv if latest_artifact else None,
        }
        rows.append(row)
    return rows


def _canonical_parameter_title(title: str) -> str:
    text = str(title or "").strip()
    return CANONICAL_PARAMETER_TITLES.get(text.lower(), text)


def _canonical_parameter_service(title: str, service: str) -> str:
    override = CANONICAL_SERVICE_OVERRIDES.get(str(title or "").strip().lower())
    if override:
        return override
    if str(service or "").strip().lower() == "teams":
        return "Microsoft Teams"
    return service


def _actual_result_text(finding: AssessmentFinding | None, artifact: AssessmentArtifact | None) -> str:
    if finding is not None:
        raw = finding.raw_value if isinstance(finding.raw_value, dict) else {}
        actual = raw.get("actual_value")
        if actual is not None:
            return _display_value(actual)
        if finding.evaluated_value:
            return finding.evaluated_value
        return str(finding.status or "Assessed")
    if artifact is not None:
        if artifact.status == "failed":
            return artifact.stderr or "Collector execution failed"
        return str(artifact.status or "Evidence unavailable")
    return "Evidence was not collected for this assessment."


def _actual_value(evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        return {}
    actual = evidence.get("actual_value")
    if isinstance(actual, dict):
        return actual
    payload = evidence.get("payload")
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, dict):
            raw = result.get("raw_value")
            if isinstance(raw, dict) and isinstance(raw.get("actual_value"), dict):
                return raw["actual_value"]
    return {}


def _raw_actual_value(evidence: Any) -> Any:
    if isinstance(evidence, dict) and "actual_value" in evidence:
        return evidence.get("actual_value")
    return _actual_value(evidence)


def _intish(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _format_percent(value: Any) -> str:
    try:
        return f"{float(value):.2f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return "0"


def _licensing_gap_description(evidence: Any) -> str | None:
    if not isinstance(evidence, dict):
        return None
    actual = _actual_value(evidence)
    values = [evidence, actual]
    raw_status = str(evidence.get("status") or actual.get("collection_status") or "").upper()
    required_sku = actual.get("required_sku") or evidence.get("required_sku")
    for item in values:
        if isinstance(item, dict):
            text = " ".join(str(v) for v in item.values() if isinstance(v, (str, int, float)))
            if "LICENSING_GAP" in text.upper() and not required_sku:
                required_sku = item.get("sku") or item.get("license") or item.get("required_license")
    if raw_status == "LICENSING_GAP" or required_sku:
        return (
            "This parameter could not be assessed. The tenant does not have "
            f"the required license: {required_sku or 'unknown'}."
        )
    return None


def _parameter_description(*, key: str, evidence: Any, fallback: str) -> str:
    licensing = _licensing_gap_description(evidence)
    if licensing:
        return licensing

    actual = _actual_value(evidence)
    if key == "users_without_mfa":
        return f"{actual.get('users_without_mfa', 0)} out of {actual.get('total_users', 0)} users do not have MFA registered."
    if key == "global_administrator_accounts":
        raw_actual = _raw_actual_value(evidence)
        value = raw_actual if not isinstance(raw_actual, dict) else raw_actual.get("global_admin_count", raw_actual.get("global_administrator_accounts", 0))
        return f"There are {value} Global Administrator accounts."
    if key == "guest_users_count":
        return f"There are {actual.get('guest_count', 0)} guest users out of {actual.get('total_users', 0)} total users."
    if key in {"activer_inactive_teams_users", "active_inactive_teams_users"}:
        active = _intish(actual.get("active_users"))
        inactive = _intish(actual.get("inactive_users"))
        total = _intish(actual.get("total_users")) or active + inactive
        percent = actual.get("active_percent")
        if percent is None:
            percent = (float(active) / float(total) * 100) if total else 0
        return f"{active} out of {total} team users are active ({_format_percent(percent)}%)."
    if key == "account_enabled":
        enabled = _intish(actual.get("enabled_count"))
        total = _intish(actual.get("total_users"))
        percent = actual.get("enabled_percent")
        if percent is None:
            percent = (float(enabled) / float(total) * 100) if total else 0
        return f"{enabled} out of {total} accounts are enabled ({_format_percent(percent)}%)."
    if key == "user_information":
        complete = _intish(actual.get("complete_users"))
        total = _intish(actual.get("total_users"))
        missing = max(total - complete, 0)
        return f"{complete} out of {total} users have complete profile information. {missing} users are missing department or role."
    if key == "secure_score_percentage":
        score = actual.get("secure_score_percentage", 0)
        return f"Secure score is {_format_percent(score)}% which meets the recommended industry standard (80%)."
    if key == "compliance_score_overview":
        nested_evidence = evidence.get("evidence") if isinstance(evidence, dict) else None
        reasoning = nested_evidence.get("reasoning") if isinstance(nested_evidence, dict) else None
        return str(reasoning) if reasoning else (
            "Microsoft Purview Compliance Manager does not expose an officially supported public API "
            "for retrieving the overall Compliance Score; review the score directly in the Purview "
            "compliance portal (compliance.microsoft.com/compliancemanager)."
        )
    if key == "audit_log_retention_duration" and actual.get("retention_policy_source"):
        return (
            "The audit log retention period could not be confirmed automatically and should be verified "
            "manually in the Microsoft Purview compliance portal (Audit > retention policies)."
        )
    return fallback


def _display_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return f"{len(value)} item(s)"
    if isinstance(value, dict):
        parts = []
        for key, item in list(value.items())[:4]:
            label = str(key).replace("_", " ").title()
            if isinstance(item, bool):
                rendered = "Yes" if item else "No"
            elif isinstance(item, list):
                rendered = f"{len(item)} item(s)"
            elif isinstance(item, dict):
                rendered = f"{len(item)} field(s)"
            else:
                rendered = str(item)
            parts.append(f"{label}: {rendered}")
        return "; ".join(parts)
    return str(value)


def _row_status(finding: AssessmentFinding | None, artifact: AssessmentArtifact | None) -> str:
    if finding is not None:
        return str(finding.status or "warning").lower()
    if artifact is None:
        return "not_collected"
    artifact_status = str(artifact.status or "").lower()
    payload = artifact.payload if isinstance(artifact.payload, dict) else {}
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    result_status = str(result.get("status") or "").lower()
    if artifact_status == "failed":
        return "collection_error"
    if result_status in {"collection_error", "failed_collector", "collector_failed"}:
        return "collection_error"
    if result_status in {"licensing_required", "licensing_limitation"}:
        return "licensing_required"
    if result_status in {"manual_validation_required", "not_supported", "powershell_required", "graph_limitation"}:
        return "manual_validation_required"
    if artifact_status in {"evidence_collected"}:
        return "manual_validation_required"
    return result_status or artifact_status or "not_collected"


def _registry_recommendation_text(registry_recommendation: dict[str, Any]) -> str:
    if not registry_recommendation:
        return "No recommendation record exists for this parameter."
    steps = registry_recommendation.get("remediation_steps") or []
    if steps:
        return str(steps[0])
    impact = registry_recommendation.get("impact") or registry_recommendation.get("copilot_impact")
    if impact:
        return str(impact)
    return registry_recommendation.get("title") or "Recommendation source did not include remediation text."


def _artifact_evidence(artifact: AssessmentArtifact | None) -> dict[str, Any]:
    if artifact is None:
        return {"status": "missing", "message": "No finding or collector artifact exists for this parameter."}
    return {
        "status": artifact.status,
        "error": artifact.stderr,
        "source_script": artifact.source_script,
        "source_csv": artifact.source_csv,
        "payload": artifact.payload,
    }


def _build_sections_from_rows(parameter_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    sections = {service: [] for service in SERVICE_ORDER}
    for row in parameter_rows:
        sections.setdefault(row["service"], []).append({
            "title": row["title"],
            "service": row["service"],
            "pillar": row["pillar"],
            "severity": row["severity"],
            "display_severity": row.get("display_severity") or row.get("registry_severity") or row["severity"],
            "registry_severity": row.get("registry_severity") or "",
            "finding": row["finding"],
            "description": row["description"],
            "risk": row.get("risk") or _risk_text_from_row(row),
            "recommendation": row["recommendation"],
            "evidence": row["evidence"],
            "documentation_url": row.get("documentation_url") or row.get("documentation_link") or "",
            "documentation_link": row.get("documentation_url") or row.get("documentation_link") or "",
            "status": row["status"],
            "display_status": row.get("display_status", row["status"]),
            "report_order": row.get("report_order"),
        })
    return {service: items for service, items in sections.items() if items}


def _build_report_analytics(*, summary: dict, parameter_rows: list[dict[str, Any]], assessment: Any) -> dict:
    from collections import Counter

    severity = Counter(row["severity"] for row in parameter_rows)
    status = Counter(row["status"] for row in parameter_rows)
    services = Counter(row["service"] for row in parameter_rows)
    pillars = Counter(row["pillar"] for row in parameter_rows)
    licensing_rows = [row for row in parameter_rows if row["service"] == "Licensing" or "license" in row["parameter_key"]]
    licensing_status = Counter(row["status"] for row in licensing_rows)
    analytics = build_chart_data(
        summary={
            **summary,
            "pass_total": status.get("pass", 0),
            "warning_total": status.get("warning", 0),
            "fail_total": status.get("fail", 0),
        },
        analytics={
            "severity": {name: severity.get(name, 0) for name in ["critical", "high", "medium", "low", "info"]},
            "status": {
                "pass": status.get("pass", 0),
                "warning": status.get("warning", 0),
                "fail": status.get("fail", 0),
            },
            "services": dict(sorted(services.items())),
            "pillars": dict(sorted(pillars.items())),
        },
    )
    analytics["not_collected"] = status.get("not_collected", 0)
    analytics["security_governance_best_practice"] = [
        {"name": name, "value": pillars.get(name, 0)}
        for name in ["Security", "Governance", "Best Practice"]
    ]
    analytics["m365_service_scores"] = _service_scores(parameter_rows)
    analytics["pillar_scores"] = _pillar_scores(parameter_rows)
    analytics["licensing_readiness"] = [
        {"name": "Pass", "value": licensing_status.get("pass", 0)},
        {"name": "Warning", "value": licensing_status.get("warning", 0)},
        {"name": "Fail", "value": licensing_status.get("fail", 0)},
        {"name": "Not Collected", "value": licensing_status.get("not_collected", 0)},
    ]
    analytics["assessment_scores"] = {
        "overall": assessment.overall_score,
        "identity": assessment.identity_score,
        "security": assessment.security_score,
        "compliance": assessment.compliance_score,
        "collaboration": assessment.collaboration_score,
        "licensing": assessment.licensing_score,
    }
    return analytics


def _score_for_rows(rows: list[dict[str, Any]]) -> float | None:
    collected = [row for row in rows if row["status"] in {"pass", "warning", "fail"}]
    if not collected:
        return None
    points = sum(1.0 if row["status"] == "pass" else 0.5 if row["status"] == "warning" else 0.0 for row in collected)
    return round(points / len(collected) * 100, 2)


def _service_scores(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"name": service, "score": _score_for_rows([row for row in rows if row["service"] == service])}
        for service in SERVICE_ORDER
        if any(row["service"] == service for row in rows)
    ]


def _pillar_scores(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pillars = sorted({row["pillar"] for row in rows})
    return [
        {"name": pillar, "score": _score_for_rows([row for row in rows if row["pillar"] == pillar])}
        for pillar in pillars
    ]


def _build_report_model(
    *,
    assessment: Any,
    summary: dict,
    analytics: dict,
    parameter_rows: list[dict[str, Any]],
    recommendations: list[AssessmentRecommendation],
) -> dict[str, Any]:
    return {
        "title": "Copilot Readiness Assessment",
        "assessment_id": str(assessment.id),
        "tenant_id": assessment.tenant_id,
        "sections": [
            {"title": "Executive Summary", "metrics": summary, "items": []},
            {"title": "Readiness Score", "metrics": analytics["assessment_scores"], "items": []},
            {"title": "Pillar Scores", "metrics": {}, "items": analytics["pillar_scores"]},
            {"title": "M365 Service Scores", "metrics": {}, "items": analytics["m365_service_scores"]},
            {"title": "Severity Distribution", "metrics": {}, "items": analytics["severity_distribution"]},
            {"title": "Findings Summary", "metrics": {}, "items": analytics["pass_fail"] + [{"name": "Not Collected", "value": analytics["not_collected"]}]},
            {"title": "Detailed Findings", "metrics": {}, "items": parameter_rows},
            {"title": "Recommendations", "metrics": {}, "items": [
                _recommendation_payload_from_row(row)
                for row in parameter_rows
                if row.get("recommendation")
            ]},
            {"title": "Licensing Analysis", "metrics": {}, "items": analytics["licensing_readiness"]},
            {"title": "User Activity Analysis", "metrics": {}, "items": [
                row for row in parameter_rows
                if any(token in row["parameter_key"] for token in ["active", "inactive", "user", "mailbox", "onedrive"])
            ]},
            {"title": "Conclusion", "metrics": {"readiness_status": summary["readiness_status"], "deployment_recommendation": summary["deployment_recommendation"]}, "items": []},
        ],
    }


def _recommendation_payload(item: AssessmentRecommendation) -> dict[str, Any]:
    return {
        "parameter_key": item.parameter_key,
        "severity": item.severity,
        "title": item.title,
        "recommendation": item.recommendation_text,
        "remediation_steps": item.remediation_steps,
        "impact": item.impact,
    }


def _recommendation_payload_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "parameter_key": row["parameter_key"],
        "severity": row["severity"],
        "title": f"Recommendation for {row['title']}",
        "recommendation": row["recommendation"],
        "remediation_steps": row.get("remediation_steps") or [],
        "impact": row.get("description") or "",
        "status": row["status"],
    }


def _risk_text_from_row(row: dict[str, Any]) -> str:
    if row["status"] == "pass":
        return "No immediate risk was identified for this control."
    if row["status"] == "not_collected":
        return "No readiness conclusion was generated because evidence was not collected."
    if row["severity"] in {"critical", "high"}:
        return "This finding can materially increase Copilot deployment, data exposure, or governance risk."
    return "This finding should be reviewed as part of readiness improvement planning."


def _service_for_key(parameter_key: str, category: str | None) -> str:
    entra_keys = {
        "custom_banned_password_list",
        "restricted_access_to_microsoft_entra_admin_centre",
        "emergency_access_accounts",
        "devices_without_compliance_policies",
        "authentication_methods_enabled",
        "entra_tenant_creation_by_non_admin",
        "global_administrator_accounts",
        "self_service_password_reset_authentication_method",
        "tenant_collaboration_invitations",
        "admin_consent_workflow",
        "cap_policies_for_risky_sign_ins",
        "conditional_access_policies_exclusion",
        "user_consent_for_applications",
        "entra_third_party_app_integrations",
        "users_without_mfa",
        "auto_expiration_policy_for_inactive_m365_groups",
        "customer_lockbox",
        "guest_invite_settings",
        "guest_users_count",
        "user_information",
        "account_enabled",
    }
    if parameter_key in entra_keys:
        return "Entra ID"

    category_text = str(category or "").strip().lower()
    explicit_services = {
        "entra id": "Entra ID",
        "exchange online": "Exchange Online",
        "microsoft purview": "Microsoft Purview",
        "microsoft teams": "Microsoft Teams",
        "onedrive for business": "OneDrive",
        "onedrive": "OneDrive",
        "sharepoint online": "SharePoint",
        "sharepoint": "SharePoint",
        "licensing": "Licensing",
        "m365": "Microsoft 365",
        "microsoft 365": "Microsoft 365",
    }
    if category_text in explicit_services:
        return explicit_services[category_text]

    text = f"{parameter_key} {category or ''}".lower()
    if any(token in text for token in ["entra", "mfa", "identity", "admin", "guest_users"]):
        return "Entra ID"
    if any(token in text for token in ["exchange", "mailbox", "email", "calendar"]):
        return "Exchange Online"
    if any(token in text for token in ["purview", "audit", "dlp", "secure_score", "sensitivity", "lockbox"]):
        return "Microsoft Purview"
    if "teams" in text or "meeting" in text:
        return "Microsoft Teams"
    if "onedrive" in text:
        return "OneDrive"
    if any(token in text for token in ["sharepoint", "site", "sharing", "permission", "anyone_links", "anyone links"]):
        return "SharePoint"
    if "license" in text:
        return "Licensing"
    return "Microsoft 365"


def _risk_text(finding: AssessmentFinding) -> str:
    severity = (finding.severity or "info").lower()
    if finding.status == "pass":
        return "No immediate risk was identified for this control."
    if severity in {"critical", "high"}:
        return "This finding can materially increase Copilot deployment, data exposure, or governance risk."
    return "This finding should be reviewed as part of readiness improvement planning."


def _artifact_payload(item: AssessmentReport) -> dict[str, Any]:
    return {
        "id": item.id,
        "assessment_id": item.assessment_id,
        "report_type": item.report_type,
        "report_status": item.report_status,
        "storage_path": item.storage_path,
        "generated_at": item.generated_at.isoformat(),
        "generated_by": item.generated_by,
        "metadata": item.metadata_json,
    }


def _safe_report_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value).strip())
    return cleaned.strip("._") or "tenant"


def _is_valid_pdf(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size > 1000 and path.read_bytes()[:5] == b"%PDF-"
    except Exception:
        return False


async def _generate_pdf_from_docx(docx_path: str | Path, pdf_path: str | Path) -> Path:
    """
    Convert the finished DOCX report to PDF so PDF output matches Word output.
    """
    import shutil
    import subprocess

    logger = logging.getLogger("cra")
    docx_path = Path(docx_path).resolve()
    pdf_path = Path(pdf_path).resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except OSError:
            pass

    # Method 1: docx2pdf, backed by Microsoft Word on Windows.
    try:
        from docx2pdf import convert

        await asyncio.get_event_loop().run_in_executor(None, convert, str(docx_path), str(pdf_path))
        if _is_valid_pdf(pdf_path):
            logger.info(f"[PDF] docx2pdf success: {pdf_path}")
            return pdf_path
        logger.warning(f"[PDF] docx2pdf did not create a valid PDF: {pdf_path}")
    except Exception as e:
        logger.warning(f"[PDF] docx2pdf failed: {e}")

    # Method 2: LibreOffice, if installed now or added later.
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    common_soffice = Path(r"C:\Program Files\LibreOffice\program\soffice.exe")
    if not soffice and common_soffice.exists():
        soffice = str(common_soffice)
    if soffice:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    [
                        soffice,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        str(pdf_path.parent),
                        str(docx_path),
                    ],
                    capture_output=True,
                    timeout=120,
                ),
            )
            if result.returncode == 0:
                lo_output = pdf_path.parent / f"{docx_path.stem}.pdf"
                if lo_output.exists() and lo_output.resolve() != pdf_path:
                    os.replace(lo_output, pdf_path)
                if _is_valid_pdf(pdf_path):
                    logger.info(f"[PDF] LibreOffice success: {pdf_path}")
                    return pdf_path
            stderr = result.stderr.decode(errors="ignore")[:300]
            logger.warning(f"[PDF] LibreOffice failed with exit {result.returncode}: {stderr}")
        except Exception as e:
            logger.warning(f"[PDF] LibreOffice failed: {e}")
    else:
        logger.warning("[PDF] LibreOffice not installed or not on PATH")

    # Method 3: Microsoft Word COM automation on Windows.
    try:
        ps_docx = str(docx_path).replace("'", "''")
        ps_pdf = str(pdf_path).replace("'", "''")
        ps_script = f"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $null
try {{
    $doc = $word.Documents.Open('{ps_docx}', $false, $true, $false)
    $doc.ExportAsFixedFormat('{ps_pdf}', 17)
}} finally {{
    if ($doc -ne $null) {{
        $doc.Close($false)
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($doc) | Out-Null
    }}
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}}
"""
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                timeout=120,
            ),
        )
        if _is_valid_pdf(pdf_path):
            logger.info(f"[PDF] PowerShell Word success: {pdf_path}")
            return pdf_path
        stderr = result.stderr.decode(errors="ignore")[:300]
        logger.warning(f"[PDF] PowerShell Word failed with exit {result.returncode}: {stderr}")
    except Exception as e:
        logger.warning(f"[PDF] PowerShell Word failed: {e}")

    raise RuntimeError(
        "PDF conversion failed. Install Microsoft Word for docx2pdf/COM conversion "
        "or install LibreOffice and ensure soffice is on PATH."
    )


async def _convert_docx_to_pdf_async(
    docx_path: Path,
    pdf_path: Path,
    report_data: dict = None,
) -> Path:
    return await _generate_pdf_from_docx(docx_path, pdf_path)
