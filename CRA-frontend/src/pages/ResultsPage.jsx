import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import CustomizeReportModal from "../components/report/CustomizeReportModal";
import { CenteredSpinner } from "../components/ui/LoadingSpinner";
import { useToast } from "../context/ToastContext";
import { generateAssessmentReport, getAssessmentResults, startAssessment } from "../api/assessmentApi";
import { safeStringify } from "../utils/safeStringify";

const COLORS = {
  red: { fill: "#FCEBEB", text: "#A32D2D", border: "#E24B4A" },
  amber: { fill: "#FAEEDA", text: "#633806", border: "#EF9F27" },
  blue: { fill: "#E6F1FB", text: "#0C447C", border: "#378ADD" },
  green: { fill: "#EAF3DE", text: "#27500A", border: "#639922" },
  gray: { fill: "#F1EFE8", text: "#444441", border: "#888780" },
};

const SERVICE_CONFIG = [
  { key: "Entra ID", aliases: ["Entra ID"], label: "Entra ID", short: "Entra", icon: "ti-id-badge" },
  { key: "Exchange Online", aliases: ["Exchange Online"], label: "Exchange Online", short: "Exchange", icon: "ti-mail" },
  { key: "Microsoft Purview", aliases: ["Microsoft Purview"], label: "Microsoft Purview", short: "Purview", icon: "ti-shield-lock" },
  { key: "Microsoft Teams", aliases: ["Microsoft Teams"], label: "Microsoft Teams", short: "Teams", icon: "ti-brand-teams" },
  { key: "OneDrive for Business", aliases: ["OneDrive for Business", "OneDrive"], label: "OneDrive for Business", short: "OneDrive", icon: "ti-cloud" },
  { key: "SharePoint Online", aliases: ["SharePoint Online", "SharePoint"], label: "SharePoint Online", short: "SharePoint", icon: "ti-layout" },
];

const SERVICE_BY_PARAMETER_KEY = {
  custom_banned_password_list: "Entra ID",
  restricted_access_to_microsoft_entra_admin_centre: "Entra ID",
  emergency_access_accounts: "Entra ID",
  devices_without_compliance_policies: "Entra ID",
  authentication_methods_enabled: "Entra ID",
  entra_tenant_creation_by_non_admin: "Entra ID",
  global_administrator_accounts: "Entra ID",
  self_service_password_reset_authentication_method: "Entra ID",
  tenant_collaboration_invitations: "Entra ID",
  admin_consent_workflow: "Entra ID",
  cap_policies_for_risky_sign_ins: "Entra ID",
  conditional_access_policies_exclusion: "Entra ID",
  user_consent_for_applications: "Entra ID",
  entra_third_party_app_integrations: "Entra ID",
  users_without_mfa: "Entra ID",
  auto_expiration_policy_for_inactive_m365_groups: "Entra ID",
  customer_lockbox: "Entra ID",
  guest_invite_settings: "Entra ID",
  guest_users_count: "Entra ID",
  user_information: "Entra ID",
  account_enabled: "Entra ID",

  mailboxes_status_active_inactive: "Exchange Online",
  external_storage_providers_in_owa: "Exchange Online",
  mailbox_storage_usage: "Exchange Online",
  full_calendar_schedules_able_to_be_shared_externally: "Exchange Online",
  number_of_emails_read_received: "Exchange Online",
  number_of_emails_sent: "Exchange Online",

  audit_logs_enabled: "Microsoft Purview",
  secure_score_percentage: "Microsoft Purview",
  sensitivity_labels_configured_and_applied: "Microsoft Purview",
  sensitivity_labels_applied_to_teams: "Microsoft Purview",
  compliance_score_overview: "Microsoft Purview",
  information_protection_labels_applied: "Microsoft Purview",
  dlp_rules_configured: "Microsoft Purview",
  audit_log_retention_duration: "Microsoft Purview",

  copilot_integration_enabled: "Microsoft Teams",
  third_party_apps_allowed: "Microsoft Teams",
  active_inactive_teams: "Microsoft Teams",
  minimum_number_of_owners: "Microsoft Teams",
  teams_with_external_users: "Microsoft Teams",
  meeting_policies_configuration: "Microsoft Teams",
  orphan_teams: "Microsoft Teams",
  teams_with_external_guest_as_owner: "Microsoft Teams",
  meeting_transcription_enabled: "Microsoft Teams",
  guest_access_enabled_disabled: "Microsoft Teams",
  teams_lobby_bypass: "Microsoft Teams",
  teams_file_storage_option: "Microsoft Teams",
  activer_inactive_teams_users: "Microsoft Teams",
  teams_meeting_chat: "Microsoft Teams",
  meeting_recording_retention_policies: "Microsoft Teams",
  teams_channel_email_addresses: "Microsoft Teams",

  external_sharing_settings: "OneDrive for Business",
  days_to_retain_a_deleted_user_s_onedrive: "OneDrive for Business",
  total_active_users_on_onedrive: "OneDrive for Business",

  permission_setting_for_anyone_links: "SharePoint Online",
  getting_all_sites_with_sensitivity_keywords_on_a_tenant: "SharePoint Online",
  sharing_settings_external_internal: "SharePoint Online",
  sharepoint_and_onedrive_guest_access_expiry: "SharePoint Online",
  expiration_policy_for_anyone_links: "SharePoint Online",
  inactive_site_policies: "SharePoint Online",
  active_sites_count: "SharePoint Online",
  site_ownership_policies: "SharePoint Online",
  active_users_on_sharepoint: "SharePoint Online",
  sharepoint_modern_authentication: "SharePoint Online",
  storage_quota_consumption: "SharePoint Online",
};

const PILLAR_BY_PARAMETER_KEY = {
  custom_banned_password_list: "Best Practice",
  restricted_access_to_microsoft_entra_admin_centre: "Best Practice",
  emergency_access_accounts: "Best Practice",
  devices_without_compliance_policies: "Best Practice",
  authentication_methods_enabled: "Security",
  global_administrator_accounts: "Security",
  self_service_password_reset_authentication_method: "Security",
  tenant_collaboration_invitations: "Security",
  user_consent_for_applications: "Security",
  entra_third_party_app_integrations: "Governance",
  auto_expiration_policy_for_inactive_m365_groups: "Security",
  entra_tenant_creation_by_non_admin: "Best Practice",
  admin_consent_workflow: "Best Practice",
  cap_policies_for_risky_sign_ins: "Governance",
  conditional_access_policies_exclusion: "Best Practice",
  users_without_mfa: "Security",
  customer_lockbox: "Security",
  guest_invite_settings: "Security",
  guest_users_count: "Governance",
  user_information: "Best Practice",
  account_enabled: "Security",

  mailboxes_status_active_inactive: "Governance",
  external_storage_providers_in_owa: "Security",
  mailbox_storage_usage: "Best Practice",
  full_calendar_schedules_able_to_be_shared_externally: "Security",
  number_of_emails_read_received: "Best Practice",
  number_of_emails_sent: "Best Practice",

  audit_logs_enabled: "Security",
  secure_score_percentage: "Security",
  sensitivity_labels_configured_and_applied: "Security",
  sensitivity_labels_applied_to_teams: "Security",
  compliance_score_overview: "Governance",
  information_protection_labels_applied: "Security",
  dlp_rules_configured: "Security",
  audit_log_retention_duration: "Governance",

  copilot_integration_enabled: "Governance",
  third_party_apps_allowed: "Governance",
  active_inactive_teams: "Security",
  minimum_number_of_owners: "Governance",
  teams_with_external_users: "Governance",
  meeting_policies_configuration: "Governance",
  orphan_teams: "Governance",
  teams_with_external_guest_as_owner: "Security",
  meeting_transcription_enabled: "Governance",
  guest_access_enabled_disabled: "Security",
  teams_lobby_bypass: "Governance",
  teams_file_storage_option: "Security",
  activer_inactive_teams_users: "Best Practice",
  teams_meeting_chat: "Governance",
  meeting_recording_retention_policies: "Best Practice",
  teams_channel_email_addresses: "Governance",

  external_sharing_settings: "Security",
  days_to_retain_a_deleted_user_s_onedrive: "Governance",
  total_active_users_on_onedrive: "Governance",

  permission_setting_for_anyone_links: "Security",
  getting_all_sites_with_sensitivity_keywords_on_a_tenant: "Security",
  sharing_settings_external_internal: "Security",
  sharepoint_and_onedrive_guest_access_expiry: "Security",
  expiration_policy_for_anyone_links: "Security",
  inactive_site_policies: "Best Practice",
  active_sites_count: "Governance",
  site_ownership_policies: "Governance",
  active_users_on_sharepoint: "Governance",
  sharepoint_modern_authentication: "Best Practice",
  storage_quota_consumption: "Governance",
};

const PILLAR_CONFIG = [
  { key: "Security", icon: "ti-shield", title: "Security", colorFor: (pct) => (pct > 60 ? COLORS.red : COLORS.green) },
  { key: "Governance", icon: "ti-adjustments", title: "Governance", colorFor: (pct) => (pct > 50 ? COLORS.amber : COLORS.green) },
  { key: "Best Practice", icon: "ti-checklist", title: "Best Practice", colorFor: () => COLORS.blue },
];

const SEVERITY_CONFIG = [
  { key: "critical", label: "Critical", color: COLORS.red },
  { key: "high", label: "High", color: COLORS.amber },
  { key: "medium", label: "Medium", color: COLORS.blue },
  { key: "low", label: "Low", color: COLORS.green },
  { key: "informational", label: "Informational", short: "Info", color: COLORS.gray },
];

const TABS = [
  { key: "findings", label: "Service findings" },
  { key: "observations", label: "Key observations" },
  { key: "risks", label: "Risks & recommendations" },
  { key: "activity", label: "Activity" },
];

function fmtDate(value) {
  if (!value) return "No completion date";
  return new Date(value).toLocaleDateString("en-GB", { dateStyle: "medium" });
}

function number(value, digits = 0) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 0;
  return Number(parsed.toFixed(digits));
}

function pct(value) {
  return `${number(value, 2)}%`;
}

function scorePct(value) {
  return `${number(value, 2).toFixed(2)}%`;
}

function wholePct(value) {
  return `${number(value)}%`;
}

function normalizeStatus(value) {
  return String(value || "").trim().toLowerCase();
}

function normalizeSeverity(value) {
  const severity = String(value || "").trim().toLowerCase();
  if (severity === "info") return "informational";
  return severity || "informational";
}

function normalizeCategory(value) {
  const raw = String(value || "").trim();
  const lower = raw.toLowerCase();
  if (lower === "onedrive") return "OneDrive for Business";
  if (lower === "sharepoint") return "SharePoint Online";
  if (lower === "teams") return "Microsoft Teams";
  return raw;
}

function inferPillar(finding) {
  if (PILLAR_BY_PARAMETER_KEY[finding?.parameter_key]) {
    return PILLAR_BY_PARAMETER_KEY[finding.parameter_key];
  }
  const explicit = String(finding?.pillar || finding?.domain || "").trim().toLowerCase();
  if (explicit.includes("security")) return "Security";
  if (explicit.includes("governance")) return "Governance";
  if (explicit.includes("best")) return "Best Practice";

  const key = String(finding?.parameter_key || finding?.parameter_name || "").toLowerCase();
  if (/mfa|auth|admin|guest|conditional|password|sign|legacy|permission|sharing|sensitivity|dlp|audit|secure/.test(key)) {
    return "Security";
  }
  if (/policy|owner|consent|group|invitation|meeting|retention|lockbox|compliance|active|account/.test(key)) {
    return "Governance";
  }
  return "Best Practice";
}

function readinessMeta(score, fallbackLevel) {
  const numeric = number(score, 2);
  if (numeric >= 80) return { label: "Ready", key: "ready", color: COLORS.green };
  if (numeric >= 50) return { label: "Needs improvement", key: "needs improvement", color: COLORS.amber };
  if (fallbackLevel && numeric === 0) return { label: fallbackLevel, key: String(fallbackLevel).toLowerCase(), color: COLORS.red };
  return { label: "Not ready", key: "not ready", color: COLORS.red };
}

function scoreColor(score) {
  if (score >= 80) return COLORS.green;
  if (score >= 50) return COLORS.amber;
  return COLORS.red;
}

function serviceForFinding(finding) {
  if (SERVICE_BY_PARAMETER_KEY[finding?.parameter_key]) {
    return SERVICE_BY_PARAMETER_KEY[finding.parameter_key];
  }
  const category = normalizeCategory(finding?.category);
  const match = SERVICE_CONFIG.find((service) => service.aliases.includes(category));
  return match?.key || category || "Other";
}

function rawStatus(finding) {
  return normalizeStatus(finding?.status);
}

function serviceDisplayStatus(finding) {
  return rawStatus(finding);
}

function serviceDisplaySeverity(finding) {
  return normalizeSeverity(finding?.severity);
}

function buildDashboardModel(result) {
  const assessment = result?.assessment || {};
  const findings = Array.isArray(result?.findings?.items) ? result.findings.items : [];
  const totalParams = findings.length;
  const passCount = findings.filter((item) => rawStatus(item) === "pass").length;
  const failCount = findings.filter((item) => rawStatus(item) === "fail").length;
  // Prefer the authoritative score computed by the backend scoring engine
  // (assessment.overall_score). Fall back to a local pass-ratio only when the
  // backend score is unavailable (e.g. an assessment that has not been scored yet).
  const computedReadiness = totalParams ? Math.round((passCount / totalParams) * 10000) / 100 : 0;
  const backendOverall = Number(assessment.overall_score);
  const readinessScore = Number.isFinite(backendOverall) && backendOverall > 0 ? backendOverall : computedReadiness;
  const readiness = readinessMeta(readinessScore, assessment.readiness_level);

  const pillarData = PILLAR_CONFIG.map((pillar) => {
    const rows = findings.filter((item) => inferPillar(item) === pillar.key);
    const gaps = rows.filter((item) => rawStatus(item) === "fail").length;
    const failPct = rows.length ? number((gaps / rows.length) * 100) : 0;
    return { ...pillar, failPct, gaps, total: rows.length, color: pillar.colorFor(failPct) };
  });

  const serviceData = SERVICE_CONFIG.map((service) => {
    const rows = findings.filter((item) => serviceForFinding(item) === service.key);
    const failed = rows.filter((item) => serviceDisplayStatus(item) === "fail");
    const passed = rows.filter((item) => serviceDisplayStatus(item) === "pass");
    // Every parameter that is neither a clean PASS nor a clean FAIL (e.g. warning,
    // not_collected) belongs to the "review" bucket so it is always rendered. This keeps
    // total_count === fail + pass + review and prevents the UI from silently hiding a
    // parameter that was counted in the service total.
    const reviewed = rows.filter((item) => {
      const status = serviceDisplayStatus(item);
      return status !== "fail" && status !== "pass";
    });
    const severity = Object.fromEntries(SEVERITY_CONFIG.map((item) => [item.key, 0]));
    failed.forEach((item) => {
      const key = serviceDisplaySeverity(item);
      severity[key] = (severity[key] || 0) + 1;
    });
    const failPct = rows.length ? number((failed.length / rows.length) * 100) : 0;
    return {
      ...service,
      fail_count: failed.length,
      pass_count: passed.length,
      review_count: reviewed.length,
      total_count: rows.length,
      fail_pct: failPct,
      severity_breakdown: severity,
    };
  });

  return {
    assessment,
    findings,
    tenantName: assessment.tenant_name || "Assessment",
    assessmentDate: assessment.completed_at || assessment.started_at,
    preparedBy: "CRA Tool",
    readinessScore,
    readiness,
    failCount,
    passCount,
    totalParams,
    pillarData,
    serviceData,
    eligibleCopilotUsers: number(assessment.copilot_eligible_user_count),
    totalUsers: number(assessment.total_user_count || totalParams),
    onedriveActivePct: activityPercent(findings, ["total_active_users_on_onedrive", "onedrive_active_users", "active_users_per_site"]),
    teamsActivePct: activityPercent(findings, ["activer_inactive_teams_users", "active_inactive_teams_users"]),
    outlookActivePct: activityPercent(findings, ["mailboxes_status_active_inactive", "email_active_users"]),
    sharepointActivePct: activityPercent(findings, ["active_users_on_sharepoint"]),
  };
}

function activityPercent(findings, keys) {
  const row = findings.find((item) => keys.includes(item.parameter_key));
  if (!row) return null;
  const actual = row?.raw_value?.actual_value;
  if (actual && typeof actual === "object") {
    const totalUsers = Number(actual.total_users ?? actual.active_users ?? 0) + Number(actual.inactive_users ?? 0);
    if (Number(actual.total_users ?? totalUsers) === 0) {
      const status = serviceDisplayStatus(row);
      if (status === "pass") return 100;
      if (status === "fail") return 0;
      return null;
    }
    if (actual.active_ratio !== undefined) return number(Number(actual.active_ratio) <= 1 ? actual.active_ratio * 100 : actual.active_ratio);
    if (actual.active_users !== undefined && actual.inactive_users !== undefined) {
      const total = Number(actual.active_users || 0) + Number(actual.inactive_users || 0);
      return total > 0 ? number((Number(actual.active_users || 0) / total) * 100) : 0;
    }
    if (actual.percentage !== undefined) return number(actual.percentage);
  }
  const status = serviceDisplayStatus(row);
  if (status === "pass") return 100;
  if (status === "fail") return 0;
  return null;
}

function Pill({ children, color }) {
  return (
    <span
      className="inline-flex items-center rounded-[10px] border px-2 py-0.5 text-[11px] font-medium"
      style={{ backgroundColor: color.fill, color: color.text, borderColor: color.border }}
    >
      {children}
    </span>
  );
}

function ClickablePill({ children, color, active, onClick, ariaLabel }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      className="inline-flex items-center rounded-[10px] border px-2 py-0.5 text-[11px] font-medium transition hover:brightness-95"
      style={{
        backgroundColor: color.fill,
        color: color.text,
        borderColor: active ? color.border : "transparent",
        borderWidth: active ? "1.5px" : "1px",
      }}
    >
      {children}
      <span className="ml-1 text-[10px] opacity-70">{active ? "▲" : "▼"}</span>
    </button>
  );
}

function Icon({ name, className = "", style }) {
  return <i className={`ti ${name || "ti-circle"} ${className}`} style={style} aria-hidden="true" />;
}

function ActionButton({ children, onClick, disabled, variant = "primary" }) {
  const isPrimary = variant === "primary";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex h-10 items-center justify-center gap-2 rounded-lg border px-4 text-sm font-medium transition ${
        disabled ? "cursor-not-allowed opacity-60" : "hover:brightness-95"
      }`}
      style={{
        backgroundColor: isPrimary ? "#2563EB" : "#FFFFFF",
        borderColor: isPrimary ? "#2563EB" : "#D1D5DB",
        color: isPrimary ? "#FFFFFF" : "#111827",
      }}
    >
      {children}
    </button>
  );
}

function TopBar({ model, onCustomize, onQuickGenerate, quickGenerating, onRerun, rerunning, isRunning }) {
  const [quickMenuOpen, setQuickMenuOpen] = useState(false);
  const quickOptions = [
    { type: "docx", label: "Word Document (.docx)", icon: "ti-file-type-doc" },
    { type: "pdf", label: "PDF Document (.pdf)", icon: "ti-file-type-pdf" },
  ];

  const selectQuickFormat = (reportType) => {
    setQuickMenuOpen(false);
    onQuickGenerate(reportType);
  };

  return (
    <div className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
      <div className="min-w-0">
        <Link to="/assessments" className="mb-2 inline-flex items-center gap-1 text-xs text-[#6B7280] hover:text-[#111827]">
          <Icon name="ti-chevron-left" /> Assessments
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold text-[#111827]">{model.tenantName}</h1>
          <Pill color={model.readiness.color}>{model.readiness.label}</Pill>
        </div>
        <p className="mt-1 text-sm text-[#6B7280]">
          Copilot Readiness Assessment · {fmtDate(model.assessmentDate)} · Prepared by: {model.preparedBy}
        </p>
      </div>
      <div className="flex flex-col items-stretch gap-2 sm:min-w-[210px]">
        <ActionButton onClick={onCustomize}>
          <Icon name="ti-file-download" className="text-[17px]" /> Customize & Generate
        </ActionButton>
        <div className="grid grid-cols-2 gap-2">
          <div className="relative">
            <ActionButton
              variant="secondary"
              onClick={() => setQuickMenuOpen((value) => !value)}
              disabled={isRunning || quickGenerating}
            >
              <Icon name="ti-bolt" /> {quickGenerating ? "Generating" : "Quick Generate"}
            </ActionButton>
            {quickMenuOpen && !isRunning && !quickGenerating && (
              <div className="absolute right-0 z-20 mt-2 w-[220px] overflow-hidden rounded-lg border border-[#D1D5DB] bg-white shadow-lg">
                {quickOptions.map((option) => (
                  <button
                    key={option.type}
                    type="button"
                    onClick={() => selectQuickFormat(option.type)}
                    className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm text-[#111827] hover:bg-[#F8FAFC]"
                  >
                    <Icon name={option.icon} className="text-[17px] text-[#2563EB]" />
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          <ActionButton variant="secondary" onClick={onRerun} disabled={isRunning || rerunning}>
            <Icon name="ti-refresh" /> {rerunning ? "Starting" : "Re-run"}
          </ActionButton>
        </div>
      </div>
    </div>
  );
}

function ScoreBlock({ model }) {
  const mainColor = scoreColor(model.readinessScore);
  return (
    <div className="mb-4 grid gap-4 lg:grid-cols-[220px_1fr]">
      <div className="rounded-xl border border-[#E5E7EB] bg-white p-5">
        <p className="text-xs font-medium uppercase text-[#6B7280]">Readiness Score</p>
        <p className="mt-2 text-5xl font-medium leading-none" style={{ color: mainColor.text }}>
          {scorePct(model.readinessScore)}
        </p>
        <p className="mt-4 text-sm text-[#374151]">{model.failCount} out of {model.totalParams} parameters failed</p>
        <p className="mt-2 text-xs leading-5 text-[#6B7280]">Significant remediation required before enabling Copilot</p>
        <div className="mt-4">
          <Pill color={mainColor}>Readiness level: {model.readiness.key}</Pill>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {model.pillarData.map((pillar) => (
          <div key={pillar.key} className="rounded-xl border border-[#E5E7EB] bg-white p-5">
            <div className="flex items-center gap-2 text-sm font-medium text-[#111827]">
              <Icon name={pillar.icon} className="text-[18px]" style={{ color: pillar.color.text }} />
              {pillar.title}
            </div>
            <p className="mt-4 text-3xl font-medium" style={{ color: pillar.color.text }}>{wholePct(pillar.failPct)}</p>
            <p className="mt-1 text-xs text-[#6B7280]">{pillar.failPct}% failed · {pillar.gaps} gaps</p>
            <div className="mt-4 h-[5px] overflow-hidden rounded-[3px] bg-gray-100">
              <div className="h-full rounded-[3px]" style={{ width: `${Math.min(pillar.failPct, 100)}%`, backgroundColor: pillar.color.border }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCards({ model }) {
  const stats = [
    { value: model.failCount, label: "Parameters failed", color: COLORS.red },
    { value: model.passCount, label: "Parameters passed", color: COLORS.green },
    { value: model.totalParams, label: "Total assessed", color: COLORS.amber },
  ];
  return (
    <div className="mb-6 grid gap-4 md:grid-cols-3">
      {stats.map((item) => (
        <div key={item.label} className="rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] px-5 py-4">
          <p className="text-[26px] font-medium leading-none" style={{ color: item.color.text }}>{item.value}</p>
          <p className="mt-2 text-xs text-[#6B7280]">{item.label}</p>
        </div>
      ))}
    </div>
  );
}

function Tabs({ activeTab, onChange }) {
  return (
    <div className="mb-5 flex gap-6 border-b border-[#E5E7EB]">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          type="button"
          onClick={() => onChange(tab.key)}
          className="pb-3 text-sm transition"
          style={{
            borderBottom: activeTab === tab.key ? "2px solid #111827" : "2px solid transparent",
            color: activeTab === tab.key ? "#111827" : "#6B7280",
            fontWeight: activeTab === tab.key ? 500 : 400,
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function ServiceFindingsTab({ model }) {
  const [expandedService, setExpandedService] = useState(null);
  const chartRows = model.serviceData.map((service) => ({
    name: service.short,
    Failed: service.fail_count,
    Passed: service.pass_count,
  }));

  const toggleExpand = (serviceName, status) => {
    const key = `${serviceName}-${status}`;
    setExpandedService((current) => (current === key ? null : key));
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-3 text-xs text-[#6B7280]">
        {SEVERITY_CONFIG.map((sev) => (
          <span key={sev.key} className="inline-flex items-center gap-1">
            <span style={{ color: sev.color.border }}>●</span> {sev.label}
          </span>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {model.serviceData.map((service) => (
          <ServiceCard
            key={service.key}
            service={service}
            findings={model.findings}
            expandedService={expandedService}
            onToggleExpand={toggleExpand}
          />
        ))}
      </div>
      <div className="rounded-xl border border-[#E5E7EB] bg-white p-5">
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartRows} barGap={5}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EEF2F7" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#6B7280" }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#6B7280" }} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: "#F8FAFC" }} />
              <Bar dataKey="Failed" fill="#F09595" stroke="#E24B4A" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Passed" fill="#C0DD97" stroke="#639922" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-3 flex gap-4 text-xs text-[#6B7280]">
          <span className="inline-flex items-center gap-1"><span style={{ color: "#E24B4A" }}>■</span> Failed</span>
          <span className="inline-flex items-center gap-1"><span style={{ color: "#639922" }}>■</span> Passed</span>
        </div>
      </div>
    </div>
  );
}

function findingName(finding, index) {
  return (
    finding?.parameter_name ||
    finding?.title ||
    finding?.name ||
    finding?.parameter ||
    finding?.parameter_key ||
    `Parameter ${index + 1}`
  );
}

function shortEvidence(finding) {
  const raw = finding?.raw_value;
  const evidence = raw && typeof raw === "object" && !Array.isArray(raw) ? raw.evidence : null;
  const actualValue = raw && typeof raw === "object" && !Array.isArray(raw) ? raw.actual_value : null;
  const candidates = [
    finding?.description,
    finding?.evidence_summary,
    finding?.evaluated_value,
    evidence?.reason,
    evidence?.summary,
    actualValue,
    raw,
  ];
  const value = candidates.find((item) => item !== null && item !== undefined && item !== "");
  if (value === null || value === undefined || value === "") return "";
  const text = typeof value === "object" ? safeStringify(value, 0) : String(value);
  return text.length > 120 ? `${text.slice(0, 120)}...` : text;
}

function ParameterList({ serviceName, status, findings }) {
  const filtered = findings.filter((finding) => {
    if (serviceForFinding(finding) !== serviceName) return false;
    const rowStatus = serviceDisplayStatus(finding);
    // The "review" bucket surfaces every parameter that is not a clean pass/fail so no
    // parameter is ever hidden from the customer.
    if (status === "review") return rowStatus !== "fail" && rowStatus !== "pass";
    return rowStatus === status;
  });

  if (filtered.length === 0) {
    return (
      <div className="mt-3 border-t border-[#E5E7EB] pt-3 text-xs text-[#6B7280]">
        No {status} parameters found for this service.
      </div>
    );
  }

  return (
    <div className="mt-3 max-h-[320px] overflow-y-auto border-t border-[#E5E7EB] pt-3">
      {filtered.map((finding, index) => {
        const severityKey = serviceDisplaySeverity(finding);
        const severityConfig = SEVERITY_CONFIG.find((item) => item.key === severityKey) || SEVERITY_CONFIG[4];
        const description = shortEvidence(finding);
        return (
          <div
            key={finding.id || `${serviceName}-${status}-${index}`}
            className="flex items-start gap-2 border-b border-[#F3F4F6] px-1 py-2 last:border-b-0"
          >
            <span
              className="mt-[6px] h-2 w-2 shrink-0 rounded-full"
              style={{ backgroundColor: severityConfig.color.border }}
              title={severityConfig.label}
            />
            <div className="min-w-0 flex-1">
              <div className="text-xs font-medium text-[#111827]">{findingName(finding, index)}</div>
              {description && (
                <div className="mt-0.5 truncate text-[11px] text-[#6B7280]" title={description}>
                  {description}
                </div>
              )}
            </div>
            <span
              className="shrink-0 rounded-[10px] px-2 py-0.5 text-[10px] font-medium capitalize"
              style={{ backgroundColor: severityConfig.color.fill, color: severityConfig.color.text }}
            >
              {severityConfig.short || severityConfig.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function ServiceCard({ service, findings, expandedService, onToggleExpand }) {
  const barColor = service.fail_pct > 66 ? COLORS.red : service.fail_pct > 33 ? COLORS.amber : COLORS.green;
  const failKey = `${service.key}-fail`;
  const passKey = `${service.key}-pass`;
  const reviewKey = `${service.key}-review`;
  const isFailExpanded = expandedService === failKey;
  const isPassExpanded = expandedService === passKey;
  const isReviewExpanded = expandedService === reviewKey;
  const reviewCount = service.review_count || 0;
  return (
    <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 transition-all duration-200">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-[13px] font-medium text-[#111827]">
          <Icon name={service.icon} className="text-[18px] text-[#444441]" />
          {service.label}
        </div>
        <div className="flex gap-1.5">
          <ClickablePill
            color={COLORS.red}
            active={isFailExpanded}
            ariaLabel={`${isFailExpanded ? "Collapse" : "Expand"} failed ${service.label} parameters`}
            onClick={(event) => {
              event.stopPropagation();
              onToggleExpand(service.key, "fail");
            }}
          >
            {service.fail_count} fail
          </ClickablePill>
          <ClickablePill
            color={COLORS.green}
            active={isPassExpanded}
            ariaLabel={`${isPassExpanded ? "Collapse" : "Expand"} passed ${service.label} parameters`}
            onClick={(event) => {
              event.stopPropagation();
              onToggleExpand(service.key, "pass");
            }}
          >
            {service.pass_count} pass
          </ClickablePill>
          {reviewCount > 0 && (
            <ClickablePill
              color={COLORS.amber}
              active={isReviewExpanded}
              ariaLabel={`${isReviewExpanded ? "Collapse" : "Expand"} ${service.label} parameters awaiting review`}
              onClick={(event) => {
                event.stopPropagation();
                onToggleExpand(service.key, "review");
              }}
            >
              {reviewCount} review
            </ClickablePill>
          )}
        </div>
      </div>
      <div className="mt-4 h-[5px] overflow-hidden rounded-[3px] bg-gray-100">
        <div className="h-full rounded-[3px]" style={{ width: `${service.fail_pct}%`, backgroundColor: barColor.border }} />
      </div>
      <div className="mt-2 flex justify-between text-[11px] text-[#6B7280]">
        <span>{wholePct(service.fail_pct)} failed</span>
        <span>{service.total_count} params</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {SEVERITY_CONFIG.map((sev) => {
          const count = service.severity_breakdown[sev.key] || 0;
          if (count <= 0) return null;
          return <Pill key={sev.key} color={sev.color}>{count} {sev.short || sev.label}</Pill>;
        })}
      </div>
      {(isFailExpanded || isPassExpanded || isReviewExpanded) && (
        <ParameterList
          serviceName={service.key}
          status={isFailExpanded ? "fail" : isPassExpanded ? "pass" : "review"}
          findings={findings}
        />
      )}
    </div>
  );
}

function ObservationRows({ rows }) {
  return (
    <div className="rounded-xl border border-[#E5E7EB] bg-white p-5">
      {rows.map((row, index) => (
        <div
          key={index}
          className="flex gap-3 py-3 first:pt-0 last:pb-0"
          style={{ borderBottom: index === rows.length - 1 ? "none" : "0.5px solid #E5E7EB" }}
        >
          <Icon name={row.icon} className="mt-0.5 text-[15px]" style={{ color: row.color }} />
          <p className="text-[13px] leading-6 text-[#374151]">{row.text}</p>
        </div>
      ))}
    </div>
  );
}

function KeyObservationsTab({ model }) {
  const security = model.pillarData.find((item) => item.key === "Security");
  const governance = model.pillarData.find((item) => item.key === "Governance");
  const bestPractice = model.pillarData.find((item) => item.key === "Best Practice");
  const rows = [
    {
      icon: "ti-alert-triangle",
      color: COLORS.red.border,
      text: `A total of ${model.failCount} gaps out of ${model.totalParams} parameters were identified, distributed across Security, Governance, and Best Practice categories.`,
    },
    {
      icon: "ti-alert-circle",
      color: COLORS.amber.border,
      text: "Medium to Critical severity issues make up most of the findings, indicating substantial exposure to operational and compliance risks.",
    },
    {
      icon: "ti-chart-pie",
      color: COLORS.blue.border,
      text: `Failed parameters by pillar: Security ${security?.failPct || 0}%, Governance ${governance?.failPct || 0}%, Best Practices ${bestPractice?.failPct || 0}% — critical need for immediate remediation across all three areas.`,
    },
    {
      icon: "ti-license",
      color: COLORS.gray.border,
      text: `There are ${model.eligibleCopilotUsers} user accounts eligible for a M365 Copilot license. Copilot requires M365 E3, E5, Business Standard, or Business Premium.`,
    },
    {
      icon: "ti-user-x",
      color: COLORS.gray.border,
      text: "There are no users with full user information. Department and role must be completed to establish an accurate organizational hierarchy.",
    },
  ];
  return <ObservationRows rows={rows} />;
}

function RisksTab() {
  const risks = [
    "Unauthorized access to sensitive business data",
    "Inadequate auditing and monitoring of AI-driven activity",
    "Compliance violations with internal and external regulations",
    "Reduced user trust due to misconfigured policies",
  ];
  const recommendations = [
    {
      title: "Remediation of identified gaps",
      body: "Address all findings regardless of severity to meet cybersecurity baseline standards.",
    },
    {
      title: "Postpone deployment",
      body: "Due to the current maturity level, adopt Copilot only after all critical and high-priority gaps are resolved.",
    },
    {
      title: "Futureproofing",
      body: "Implementing the recommendations will reduce security risks and ensure regulatory compliance during and after Copilot integration.",
    },
  ];
  return (
    <div className="space-y-6">
      <SectionHeading>Risks of immediate deployment</SectionHeading>
      <div className="grid gap-4 md:grid-cols-2">
        {risks.map((risk) => (
          <div key={risk} className="rounded-r-xl border border-[#E5E7EB] bg-white px-5 py-4 text-[13px] leading-6 text-[#374151]" style={{ borderLeft: `3px solid ${COLORS.red.border}` }}>
            {risk}
          </div>
        ))}
      </div>
      <SectionHeading>Recommendations</SectionHeading>
      <div className="space-y-3">
        {recommendations.map((item) => (
          <div key={item.title} className="rounded-xl border border-[#E5E7EB] bg-white p-5">
            <p className="text-[13px] font-medium text-[#111827]">{item.title}</p>
            <p className="mt-2 text-xs leading-6 text-[#6B7280]">{item.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function SectionHeading({ children }) {
  return <p className="text-[13px] font-medium uppercase tracking-wide text-[#6B7280]">{children}</p>;
}

function ActivityTab({ model }) {
  const activities = [
    { value: model.onedriveActivePct, label: "OneDrive users active" },
    { value: model.teamsActivePct, label: "Teams users active" },
    { value: model.outlookActivePct, label: "Outlook users active" },
    { value: model.sharepointActivePct, label: "SharePoint users active" },
  ];
  const colorFor = (value) => {
    if (value == null) return "#444441";
    if (value === 100) return "#3B6D11";
    if (value === 0) return "#A32D2D";
    return "#BA7517";
  };
  const rows = [
    {
      icon: "ti-license",
      color: COLORS.red.border,
      text: `${model.eligibleCopilotUsers} out of ${model.totalUsers} accounts are eligible for a M365 Copilot license. Eligible base plans: M365 E3, E5, Business Standard, or Business Premium.`,
    },
    {
      icon: "ti-users",
      color: COLORS.gray.border,
      text: "No users have complete profile information (department, role). This must be resolved for Copilot to deliver accurate, context-aware insights.",
    },
  ];
  return (
    <div className="space-y-6">
      <SectionHeading>User activity in past 60 days</SectionHeading>
      <div className="grid gap-4 md:grid-cols-4">
        {activities.map((item) => (
          <div key={item.label} className="rounded-lg border border-[#E5E7EB] bg-[#F8FAFC] px-4 py-3 text-center">
            <p className="text-[22px] font-medium" style={{ color: colorFor(item.value) }}>
              {item.value == null ? "--" : `${item.value}%`}
            </p>
            <p className="mt-1 text-[11px] text-[#6B7280]">{item.label}</p>
          </div>
        ))}
      </div>
      <SectionHeading>Licensing readiness</SectionHeading>
      <ObservationRows rows={rows} />
    </div>
  );
}

export default function ResultsPage() {
  const { assessmentId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState("findings");
  const [rerunning, setRerunning] = useState(false);
  const [showCustomizeModal, setShowCustomizeModal] = useState(false);
  const [quickGenerating, setQuickGenerating] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getAssessmentResults(assessmentId);
        if (!cancelled) setResult(data);
      } catch {
        if (!cancelled) setError("Failed to load assessment results. Please try again.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [assessmentId]);

  const model = useMemo(() => buildDashboardModel(result), [result]);
  const isRunning = model.assessment.status && model.assessment.status !== "completed";

  const handleRerun = async () => {
    const tenantId = model.assessment.tenant_id;
    if (!tenantId) {
      toast.error("Tenant ID not available.");
      return;
    }
    setRerunning(true);
    try {
      const newAssessment = await startAssessment(tenantId);
      navigate(`/assessments/${newAssessment.id}/progress`);
    } catch {
      toast.error("Failed to start assessment. Please try again.");
      setRerunning(false);
    }
  };

  const handleQuickGenerate = async (reportType = "docx") => {
    setQuickGenerating(true);
    try {
      const blob = await generateAssessmentReport(assessmentId, reportType);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `CRA_Report_${model.tenantName || assessmentId}.${reportType}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success("Report generated with TechPlusTalent branding.");
    } catch {
      toast.error("Failed to generate report. Please try again.");
    } finally {
      setQuickGenerating(false);
    }
  };

  if (loading) return <CenteredSpinner label="Loading results..." />;
  if (error || !result) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24">
        <Icon name="ti-alert-circle" className="text-5xl" style={{ color: COLORS.red.border }} />
        <p className="text-base font-semibold text-[#374151]">{error || "Results not found."}</p>
        <ActionButton onClick={() => window.location.reload()}>Retry</ActionButton>
      </div>
    );
  }

  return (
    <>
      <div className="mx-auto max-w-[1320px]">
        <TopBar
          model={model}
          onCustomize={() => setShowCustomizeModal(true)}
          onQuickGenerate={handleQuickGenerate}
          quickGenerating={quickGenerating}
          onRerun={handleRerun}
          rerunning={rerunning}
          isRunning={isRunning}
        />
        {isRunning && (
          <div className="mb-4 rounded-lg border border-[#EF9F27] bg-[#FAEEDA] px-4 py-3 text-sm text-[#633806]">
            Assessment is still {model.assessment.status}. Results may be incomplete.
          </div>
        )}
        <ScoreBlock model={model} />
        <StatCards model={model} />
        <Tabs activeTab={activeTab} onChange={setActiveTab} />
        {activeTab === "findings" && <ServiceFindingsTab model={model} />}
        {activeTab === "observations" && <KeyObservationsTab model={model} />}
        {activeTab === "risks" && <RisksTab />}
        {activeTab === "activity" && <ActivityTab model={model} />}
      </div>

      {showCustomizeModal && (
        <CustomizeReportModal
          assessmentId={assessmentId}
          tenantName={model.tenantName}
          onClose={() => setShowCustomizeModal(false)}
        />
      )}
    </>
  );
}
