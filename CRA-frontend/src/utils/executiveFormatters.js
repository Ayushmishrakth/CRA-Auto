import { numberOrZero } from "./assessmentFormatters";

const STATUS_LABELS = {
  PASS: "PASS",
  FAIL: "FAIL",
  FAILED: "COLLECTION ERROR",
  FAILED_COLLECTOR: "COLLECTION ERROR",
  COLLECTION_ERROR: "COLLECTION ERROR",
  LICENSING_REQUIRED: "FAIL",
  MANUAL_VALIDATION: "FAIL",
  MANUAL_VALIDATION_REQUIRED: "FAIL",
  NOT_COLLECTED: "NOT COLLECTED",
  WARNING: "WARNING",
};

const DOMAIN_ALIASES = {
  "Entra ID": "Identity",
  "Microsoft Entra ID": "Identity",
  "Exchange Online": "Exchange",
  "Microsoft Teams": "Teams",
  "SharePoint Online": "SharePoint",
  "Microsoft Purview": "Purview",
  OneDrive: "OneDrive",
};

const FRIENDLY_NAMES = {
  global_administrator_accounts: "Global Administrators",
  guest_users_count: "Guest User Ratio",
  users_without_mfa: "Users Without MFA",
  external_storage_providers_in_owa: "External Storage Providers in Outlook",
  full_calendar_schedules_able_to_be_shared_externally: "External Calendar Sharing",
  sharepoint_and_onedrive_guest_access_expiry: "Guest Access Expiry",
  audit_log_retention_duration: "Audit Log Retention",
  customer_lockbox: "Customer Lockbox",
};

export function executiveStatus(status = "") {
  const normalized = String(status || "NOT_COLLECTED").toUpperCase();
  return STATUS_LABELS[normalized] || normalized.replaceAll("_", " ").toLowerCase();
}

export function statusTone(status = "") {
  const normalized = String(status || "").toUpperCase();
  if (normalized === "PASS") return "success";
  if (normalized === "FAIL") return "critical";
  if (["FAILED", "FAILED_COLLECTOR", "COLLECTION_ERROR", "WARNING"].includes(normalized)) return "warning";
  if (["LICENSING_REQUIRED", "MANUAL_VALIDATION", "MANUAL_VALIDATION_REQUIRED"].includes(normalized)) return "critical";
  return "neutral";
}

export function businessName(item = {}) {
  const key = item.parameter_key || item.parameter || "";
  if (FRIENDLY_NAMES[key]) return FRIENDLY_NAMES[key];
  const raw = item.parameter_name || item.title || item.parameter || key || "Assessment control";
  return String(raw)
    .replace(/^graph\./i, "")
    .replace(/^powershell\./i, "")
    .replaceAll("_", " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function businessDomain(item = {}) {
  const service = item.service || item.category || item.domain || "Microsoft 365";
  const lower = String(service).toLowerCase();
  if (lower.includes("identity") || lower.includes("entra")) return "Identity";
  if (lower.includes("exchange") || lower.includes("mailbox") || lower.includes("outlook")) return "Exchange";
  if (lower.includes("team")) return "Teams";
  if (lower.includes("sharepoint")) return "SharePoint";
  if (lower.includes("purview") || lower.includes("compliance")) return "Purview";
  if (lower.includes("onedrive")) return "OneDrive";
  return DOMAIN_ALIASES[service] || service;
}

export function displayResult(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value !== "object") return String(value);
  const entries = Object.entries(value).filter(([, entryValue]) => entryValue !== null && entryValue !== undefined);
  if (!entries.length) return "-";
  return entries
    .slice(0, 3)
    .map(([key, entryValue]) => {
      const label = key
        .replaceAll("_", " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
      if (typeof entryValue === "boolean") return `${label}: ${entryValue ? "Yes" : "No"}`;
      if (Array.isArray(entryValue)) return `${label}: ${entryValue.length}`;
      if (typeof entryValue === "object") return `${label}: ${Object.keys(entryValue).length} items`;
      return `${label}: ${String(entryValue)}`;
    })
    .join("; ");
}

export function foundText(item = {}) {
  if (["FAILED", "FAILED_COLLECTOR", "COLLECTION_ERROR"].includes(item.status)) return item.failure_reason || "Collector could not complete";
  if (item.status === "LICENSING_REQUIRED") return "Requires Microsoft licensing";
  if (["MANUAL_VALIDATION", "MANUAL_VALIDATION_REQUIRED"].includes(item.status)) return "Requires business review";
  if (item.status === "NOT_COLLECTED") return "Not collected";
  return displayResult(item.actual_value ?? item.finding);
}

export function expectedText(item = {}) {
  return displayResult(item.expected_value);
}

export function riskRating(score) {
  const value = numberOrZero(score);
  if (value >= 80) return "Low";
  if (value >= 65) return "Moderate";
  if (value >= 45) return "High";
  return "Critical";
}

export function coveragePercent(coverage = {}) {
  const total = numberOrZero(coverage.total_parameters);
  if (!total) return 0;
  return Math.round((numberOrZero(coverage.collected) / total) * 100);
}

export function sortBusinessPriority(items = []) {
  const severityRank = { critical: 5, high: 4, medium: 3, low: 2, info: 1 };
  const statusRank = { FAIL: 6, COLLECTION_ERROR: 5, FAILED_COLLECTOR: 5, FAILED: 5, LICENSING_REQUIRED: 4, MANUAL_VALIDATION: 3, MANUAL_VALIDATION_REQUIRED: 3, NOT_COLLECTED: 2, WARNING: 1, PASS: 0 };
  return [...items].sort((a, b) => {
    const statusDelta = (statusRank[b.status] ?? 0) - (statusRank[a.status] ?? 0);
    if (statusDelta) return statusDelta;
    return (severityRank[String(b.severity || "info").toLowerCase()] ?? 0) - (severityRank[String(a.severity || "info").toLowerCase()] ?? 0);
  });
}

export function findingToExecutiveRow(finding = {}, recommendation = null) {
  const raw = finding.raw_value && typeof finding.raw_value === "object" ? finding.raw_value : {};
  const status = String(finding.status || raw.status || "WARNING").toUpperCase();
  return {
    parameter_key: finding.parameter_key || raw.parameter_key || finding.id,
    parameter_name: finding.parameter_name || finding.parameter || raw.parameter_name || raw.parameter_key || "Assessment control",
    service: finding.category || raw.category || raw.collector_type || "Microsoft 365",
    status,
    severity: finding.severity || raw.severity || "info",
    actual_value: finding.actual_value ?? raw.actual_value ?? raw.evidence?.actual_value ?? finding.value,
    expected_value: finding.expected_value ?? raw.expected_value,
    finding: finding.evaluated_value || finding.value,
    recommendation,
    evidence: raw.evidence || raw.raw_response || raw,
  };
}
