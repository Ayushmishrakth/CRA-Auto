import { Fragment, useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ChevronLeft, Download, RotateCcw, Shield, Lock, Mail, Users,
  FolderOpen, CreditCard, AlertTriangle, CheckCircle2, XCircle,
  ChevronDown, ChevronUp, FileText, Loader2, Check,
  Clock, Activity, Info, ExternalLink,
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import Badge from "../components/ui/Badge";
import ScoreBar from "../components/ui/ScoreBar";
import Button from "../components/ui/Button";
import Modal from "../components/ui/Modal";
import { CenteredSpinner } from "../components/ui/LoadingSpinner";
import { useToast } from "../context/ToastContext";
import {
  getAssessmentResults,
  generateAssessmentReport,
  getAssessmentReport,
  downloadAssessmentReport,
  startAssessment,
  customizeAssessmentReport,
} from "../api/assessmentApi";

// ── Domain configuration ─────────────────────────────────────
const DOMAINS = [
  { cat: "Entra ID",             label: "Entra ID",              icon: Shield,     color: "#0078D4", bg: "#EFF6FC", pillar: "Security"     },
  { cat: "Exchange Online",      label: "Exchange Online",        icon: Mail,       color: "#107C10", bg: "#DFF6DD", pillar: "Governance"   },
  { cat: "Microsoft Purview",    label: "Microsoft Purview",      icon: Lock,       color: "#5C2D91", bg: "#F4EEF9", pillar: "Security"     },
  { cat: "Microsoft Teams",      label: "Microsoft Teams",        icon: Users,      color: "#6264A7", bg: "#F0F0F8", pillar: "Governance"   },
  { cat: "OneDrive for Business",label: "OneDrive for Business",  icon: FolderOpen, color: "#0078D4", bg: "#EFF6FC", pillar: "Best Practice"},
  { cat: "SharePoint Online",    label: "SharePoint Online",      icon: FolderOpen, color: "#038387", bg: "#E6F4F4", pillar: "Best Practice"},
  { cat: "M365",                 label: "Licensing (M365)",       icon: CreditCard, color: "#0097A7", bg: "#E0F7FA", pillar: "Best Practice"},
];

const DOMAIN_BY_CAT = Object.fromEntries(DOMAINS.map((d) => [d.cat, d]));

const PILLARS = [
  { key: "Security",     color: "#DC2626", bg: "#FEE2E2", icon: Lock    },
  { key: "Governance",   color: "#EA580C", bg: "#FFEDD5", icon: Shield  },
  { key: "Best Practice",color: "#0078D4", bg: "#DBEAFE", icon: Activity},
];

// ── Domain score bar config ───────────────────────────────────
const SCORE_DOMAINS = [
  { key: "identity",      label: "Entra ID",   color: "#0078D4", skippable: false,
    cats: ["Entra ID"] },
  { key: "security",      label: "Security",   color: "#D13438", skippable: false,
    cats: [] },
  { key: "compliance",    label: "Purview",    color: "#5C2D91", skippable: true,
    cats: ["Microsoft Purview"] },
  { key: "collaboration", label: "Teams",      color: "#6264A7", skippable: true,
    cats: ["Microsoft Teams"] },
  { key: "licensing",     label: "Licensing",  color: "#0097A7", skippable: false,
    cats: [] },
];

// Rule: A=red 0% critical failures, B=gray N/A not assessed, C=gray Excl., D=normal
function getDomainRule(domainKey, score, allFindings) {
  if (domainKey === "licensing") return "C";
  if (score != null && score > 0) return "D";
  const d = SCORE_DOMAINS.find((x) => x.key === domainKey);
  const cats = d?.cats ?? [];
  if (cats.length === 0) return score === 0 ? "A" : "B";
  const domFindings = allFindings.filter((f) => cats.includes(f.category || ""));
  if (domFindings.length === 0) return "B";
  if (domFindings.some((f) => (f.status || "").toLowerCase() === "fail")) return "A";
  return "B";
}

function getScoreBarColor(value) {
  if (value >= 90) return "#16A34A";
  if (value >= 75) return "#2563EB";
  if (value >= 40) return "#EA580C";
  return "#DC2626";
}

// ── Readiness tier ───────────────────────────────────────────
function readinessTier(score) {
  if (score == null)  return { label: "Not Assessed",      color: "#6B7280", bg: "#F3F4F6" };
  if (score < 40)     return { label: "Not Ready",         color: "#DC2626", bg: "#FEE2E2" };
  if (score < 60)     return { label: "Needs Improvement", color: "#EA580C", bg: "#FFEDD5" };
  if (score < 75)     return { label: "Partially Ready",   color: "#CA8A04", bg: "#FEF9C3" };
  if (score < 90)     return { label: "Ready",             color: "#2563EB", bg: "#DBEAFE" };
  return               { label: "Highly Ready",            color: "#16A34A", bg: "#DCFCE7" };
}

const SEV_STYLE = {
  critical: { color: "#DC2626", bg: "#FEE2E2" },
  high:     { color: "#EA580C", bg: "#FFEDD5" },
  medium:   { color: "#CA8A04", bg: "#FEF9C3" },
  low:      { color: "#6B7280", bg: "#F3F4F6" },
  info:     { color: "#2563EB", bg: "#DBEAFE" },
};

// ── Helpers ──────────────────────────────────────────────────
function fmtDate(d) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", { dateStyle: "long" });
}

function fmtKey(key) {
  return (key || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function getPillar(finding) {
  const dom = DOMAIN_BY_CAT[finding.category || ""];
  if (dom) return dom.pillar;
  const k = (finding.parameter_key || "").toLowerCase();
  if (/mfa|auth|admin|guest|lockbox|conditional_access|password|sign_in|legacy|privileged/.test(k)) return "Security";
  if (/policy|governance|consent|groups|invitation|meeting|dlp|purview|compliance/.test(k)) return "Governance";
  return "Best Practice";
}

// Clean finding value — strips raw Graph API responses and OData artifacts
function getCleanFinding(rawValue) {
  if (!rawValue) return "—";

  const val = rawValue.actual_value ?? rawValue.value ?? rawValue.finding;

  if (val === null || val === undefined) return "—";

  if (typeof val === "object") {
    if (val.displayValue !== undefined) return String(val.displayValue);
    if (val.result !== undefined) return String(val.result);
    if (val.status_text !== undefined) return String(val.status_text);
    if (val.enabled !== undefined) return val.enabled ? "Enabled" : "Disabled";
    if (val.isEnabled !== undefined) return val.isEnabled ? "Enabled" : "Disabled";
    if (val.count !== undefined) return `Count: ${val.count}`;
    if (val.value !== undefined) return String(val.value);
    // Structured dict — build a readable summary from meaningful keys
    const SKIP_KEYS = new Set(["@odata.context", "@odata.type", "id", "tenantId", "tenant_id"]);
    const entries = Object.entries(val).filter(([k]) => !SKIP_KEYS.has(k));
    if (entries.length > 0) {
      return entries
        .map(([k, v]) => {
          const label = k.replace(/_/g, " ").replace(/([A-Z])/g, " $1").trim();
          return `${label}: ${typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(1)) : v}`;
        })
        .slice(0, 3)
        .join(" · ");
    }
    return "No specific data collected";
  }

  const strVal = String(val);

  // Strip OData context URLs
  if (strVal.startsWith("@odata") || strVal.startsWith("https://") || strVal.startsWith("http://")) {
    return "—";
  }

  // Strip JSON-like strings that leaked through
  if (strVal.startsWith("{") || strVal.startsWith("[")) {
    try {
      const parsed = JSON.parse(strVal);
      if (parsed.actual_value) return String(parsed.actual_value);
      if (parsed.value) return String(parsed.value);
      if (parsed.count !== undefined) return `Count: ${parsed.count}`;
    } catch { /* not json */ }
    return strVal.slice(0, 80) + "…";
  }

  return strVal.length > 80 ? strVal.slice(0, 80) + "…" : strVal;
}

// Full version for expanded details (no truncation)
function getFullFinding(rawValue) {
  if (!rawValue) return "No specific data collected";
  const val = rawValue.actual_value ?? rawValue.value ?? rawValue.finding;
  if (val === null || val === undefined) return "No specific data collected";
  if (typeof val === "object") {
    const SKIP_KEYS = new Set(["@odata.context", "@odata.type", "tenantId", "tenant_id"]);
    const entries = Object.entries(val).filter(([k]) => !SKIP_KEYS.has(k));
    if (entries.length > 0) {
      return entries
        .map(([k, v]) => {
          const label = k.replace(/_/g, " ").replace(/([A-Z])/g, " $1").trim();
          return `${label}: ${typeof v === "object" ? JSON.stringify(v) : v}`;
        })
        .join(" · ");
    }
    return "No specific data collected";
  }
  const strVal = String(val);
  if (strVal.startsWith("@odata") || strVal.startsWith("https://")) return "No specific data collected";
  return strVal;
}

function extractDocUrl(remediationSteps, rawValue) {
  const candidates = [
    ...(Array.isArray(remediationSteps) ? remediationSteps : []),
    rawValue?.remediation,
    rawValue?.evidence?.remediation,
  ];
  for (const item of candidates) {
    if (!item) continue;
    const str = typeof item === "string" ? item : JSON.stringify(item);
    const match = str.match(/https?:\/\/(?:learn\.microsoft\.com|docs\.microsoft\.com|aka\.ms)[^\s"')>]*/i);
    if (match) return match[0];
  }
  return null;
}

function getActualValue(raw_value) {
  return getCleanFinding(raw_value);
}

// ── Finding categorizer ──────────────────────────────────────
function categorizeFinding(finding) {
  if (!finding) return "not_collected";
  const status = (finding.status || "").toLowerCase();
  if (status === "pass") return "pass";
  if (status === "not_collected") return "not_collected";

  const evalVal = String(finding.evaluated_value || "").toLowerCase();
  const rawActual =
    typeof finding.raw_value?.actual_value === "string"
      ? finding.raw_value.actual_value.toLowerCase()
      : "";
  const text = evalVal || rawActual;

  const licensingPatterns = [
    "not available in tenant",
    "not available in this tenant",
    "readiness gap",
    "sharepoint online license",
    "requires microsoft 365",
    "requires m365",
    "not licensed",
    "license not available",
    "service unavailable",
    "aadsts500014",
  ];

  const zeroActivityPatterns = [
    "0 active sharepoint",
    "0 active mailbox",
    "0 active onedrive",
    "0 active group lifecycle",
    "0 active site",
    "active ratio 0.0",
    "not applicable to target tenant",
    "average sent email count per user is 0",
    "0.0% of users",
    "0 out of 0",
  ];

  if (licensingPatterns.some((p) => text.includes(p))) return "licensing";
  if (zeroActivityPatterns.some((p) => text.includes(p))) return "activity";
  return "actionable";
}

function buildCategorized(items) {
  const cats = { actionable: [], licensing: [], activity: [], pass: [], not_collected: [] };
  (items ?? []).forEach((f) => { cats[categorizeFinding(f)].push(f); });
  return cats;
}

function severityBadge(sev) {
  const s = (sev || "").toLowerCase();
  const style = SEV_STYLE[s] || SEV_STYLE.info;
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold capitalize"
      style={{ backgroundColor: style.bg, color: style.color }}
    >
      {sev || "—"}
    </span>
  );
}

function effortBadge(e) {
  const map = { Low: "#16A34A", Medium: "#CA8A04", High: "#DC2626" };
  const col = map[e] || "#6B7280";
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border" style={{ color: col, borderColor: col }}>
      {e} effort
    </span>
  );
}

function statusIcon(status) {
  const s = (status || "").toLowerCase();
  if (s === "pass")   return <CheckCircle2 size={15} className="text-[#107C10] flex-shrink-0" />;
  if (s === "fail")   return <XCircle      size={15} className="text-[#DC2626] flex-shrink-0" />;
  if (s === "collection_error") return <AlertTriangle size={15} className="text-[#EA580C] flex-shrink-0" />;
  return <div className="w-4 h-4 rounded-full border border-[#D1D5DB] flex-shrink-0" />;
}

// ── Score Gauge ──────────────────────────────────────────────
function ScoreGauge({ score }) {
  const tier = readinessTier(score);
  const pct = (score ?? 0) / 100;
  const data = [{ value: pct }, { value: 1 - pct }];
  return (
    <div className="flex flex-col items-center py-4">
      <div className="relative w-40 h-20 overflow-hidden">
        <ResponsiveContainer width="100%" height={160}>
          <PieChart>
            <Pie
              data={data} cx="50%" cy="100%"
              startAngle={180} endAngle={0}
              innerRadius={54} outerRadius={70}
              stroke="none" dataKey="value"
            >
              <Cell fill={tier.color} />
              <Cell fill="#E5E7EB" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-x-0 bottom-0 flex flex-col items-center pb-1">
          <span className="text-3xl font-extrabold leading-none" style={{ color: tier.color }}>
            {score != null ? Math.round(score) : "—"}
          </span>
          <span className="text-xs text-[#9CA3AF]">/ 100</span>
        </div>
      </div>
      <span
        className="mt-3 px-3 py-1 rounded-full text-xs font-bold"
        style={{ backgroundColor: tier.bg, color: tier.color }}
      >
        {tier.label}
      </span>
    </div>
  );
}

// ── Activity Bar ─────────────────────────────────────────────
function ActivityBar({ label, pct, color }) {
  const v = pct ?? null;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-[#6B7280] w-24 flex-shrink-0">{label}</span>
      <div className="flex-1 bg-[#E5E7EB] rounded-full h-2">
        <div
          className="h-2 rounded-full transition-all"
          style={{ width: v !== null ? `${Math.min(v, 100)}%` : "0%", backgroundColor: color }}
        />
      </div>
      <span className="text-xs font-semibold text-[#374151] w-10 text-right">
        {v !== null ? `${v}%` : "—"}
      </span>
    </div>
  );
}

// ── Executive Summary Card ───────────────────────────────────
function ExecSummaryCard({ result }) {
  const score = result.assessment?.overall_score;
  const tier = readinessTier(score);
  const items = result.findings?.items ?? [];
  const fails = items.filter((f) => (f.status || "").toLowerCase() === "fail");
  const total = result.findings?.total ?? 0;

  const pillarFails = { Security: 0, Governance: 0, "Best Practice": 0 };
  fails.forEach((f) => {
    const p = getPillar(f);
    pillarFails[p] = (pillarFails[p] || 0) + 1;
  });
  const totalFails = fails.length;

  return (
    <div className="bg-white border-2 rounded-2xl p-6 mb-6" style={{ borderColor: tier.color }}>
      <div className="flex flex-col md:flex-row gap-6 items-start">
        <div className="flex flex-col items-center min-w-[120px]">
          <span className="text-6xl font-black" style={{ color: tier.color }}>
            {score != null ? `${Math.round(score)}%` : "—"}
          </span>
          <span
            className="mt-2 px-3 py-1 rounded-full text-sm font-bold"
            style={{ backgroundColor: tier.bg, color: tier.color }}
          >
            {tier.label}
          </span>
          <p className="text-xs text-[#6B7280] mt-2 text-center">Overall Readiness</p>
        </div>
        <div className="hidden md:block w-px self-stretch bg-[#E5E7EB]" />
        <div className="flex-1 space-y-4">
          <div>
            <p className="text-2xl font-bold text-[#111827]">
              <span style={{ color: "#DC2626" }}>{totalFails}</span>
              <span className="text-base font-medium text-[#6B7280]"> out of {total} parameters failed</span>
            </p>
            <p className="text-sm text-[#6B7280] mt-0.5">Readiness gaps identified across Security, Governance &amp; Best Practices</p>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {PILLARS.map(({ key, color, bg, icon: Icon }) => {
              const count = pillarFails[key] || 0;
              const pct = totalFails > 0 ? Math.round((count / totalFails) * 100) : 0;
              return (
                <div key={key} className="rounded-xl p-3 flex flex-col items-center gap-1 text-center" style={{ backgroundColor: bg }}>
                  <Icon size={18} style={{ color }} />
                  <p className="text-xs font-semibold" style={{ color }}>{key}</p>
                  <p className="text-lg font-black" style={{ color }}>{pct}%</p>
                  <p className="text-xs" style={{ color, opacity: 0.75 }}>{count} gaps</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Tab 1: Key Observations ──────────────────────────────────
function KeyObservationsTab({ result, categorized }) {
  const [licensingExpanded, setLicensingExpanded] = useState(false);

  const findings = result.findings ?? {};
  const items = findings.items ?? [];
  const total = findings.total ?? 0;
  const fails = items.filter((f) => (f.status || "").toLowerCase() === "fail");
  const totalFails = fails.length;

  const { actionable, licensing, activity, pass } = categorized;
  const allLicensingGaps = [...licensing, ...activity];

  // Actionable grouped by severity
  const SEV_ORDER = ["critical", "high", "medium", "low"];
  const actionableBySev = SEV_ORDER.map((sev) => ({
    sev,
    items: actionable.filter((f) => (f.severity || "").toLowerCase() === sev),
  })).filter((g) => g.items.length > 0);

  // Licensing grouped by service
  const svcGroups = { Teams: [], SharePoint: [], Exchange: [], Purview: [], Other: [] };
  allLicensingGaps.forEach((f) => {
    const ev = String(f.evaluated_value || "").toLowerCase();
    if (ev.includes("teams")) svcGroups.Teams.push(f);
    else if (ev.includes("sharepoint") || ev.includes("onedrive")) svcGroups.SharePoint.push(f);
    else if (ev.includes("exchange") || ev.includes("mailbox")) svcGroups.Exchange.push(f);
    else if (ev.includes("purview")) svcGroups.Purview.push(f);
    else svcGroups.Other.push(f);
  });

  const SEV_HEADER = {
    critical: { bg: "#FEE2E2", color: "#DC2626" },
    high:     { bg: "#FFEDD5", color: "#EA580C" },
    medium:   { bg: "#FEF9C3", color: "#CA8A04" },
    low:      { bg: "#F3F4F6", color: "#6B7280" },
  };

  const getReasonText = (f) => {
    const ev = f.evaluated_value;
    if (ev) return ev.length > 120 ? ev.slice(0, 120) + "…" : ev;
    const clean = getCleanFinding(f.raw_value);
    return clean === "—" ? "" : clean;
  };

  // Activity data for Observations
  function activityPct(key, field = "active_ratio") {
    const f = items.find((i) => i.parameter_key === key);
    if (!f?.raw_value?.actual_value || typeof f.raw_value.actual_value !== "object") return null;
    const av = f.raw_value.actual_value;
    if (field === "computed_active") {
      const active = av.active_users ?? 0;
      const inactive = av.inactive_users ?? 0;
      const tot = active + inactive;
      return tot > 0 ? Math.round((active / tot) * 100) : 0;
    }
    const v = av[field];
    if (v === null || v === undefined) return null;
    return Math.round(v <= 1 ? v * 100 : v);
  }

  const activityData = {
    onedrive:   activityPct("active_users_per_site", "active_ratio") ?? activityPct("onedrive_active_users", "active_ratio"),
    teams:      activityPct("activer_inactive_teams_users", "computed_active"),
    outlook:    activityPct("email_active_users", "active_ratio") ?? activityPct("mailboxes_status_active_inactive", "active_ratio"),
    sharepoint: activityPct("active_users_on_sharepoint", "active_ratio"),
  };

  const eligible = result.assessment?.copilot_eligible_user_count;
  const totalUsers = result.assessment?.total_user_count;

  const pillarFails = { Security: 0, Governance: 0, "Best Practice": 0 };
  fails.forEach((f) => { const p = getPillar(f); pillarFails[p] = (pillarFails[p] || 0) + 1; });
  const pillarPct = (key) => totalFails > 0 ? Math.round(((pillarFails[key] || 0) / totalFails) * 100) : 0;

  const sev = { critical: findings.critical ?? 0, high: findings.high ?? 0, medium: findings.medium ?? 0, low: findings.low ?? 0 };
  const sevTotal = sev.critical + sev.high + sev.medium + sev.low;
  const medHighCritPct = sevTotal > 0
    ? Math.round(((sev.critical + sev.high + sev.medium) / sevTotal) * 100) : 0;

  return (
    <div className="space-y-6">

      {/* ── Change 3: Priority Banner ── */}
      {actionable.length > 0 ? (
        <div className="border-l-4 border-[#DC2626] bg-[#FEF2F2] rounded-r-xl px-5 py-4">
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="text-[#DC2626] flex-shrink-0 mt-0.5" />
            <p className="text-sm text-[#7F1D1D]">
              <span className="font-bold">{actionable.length} parameters failed due to security misconfigurations</span>
              {" — fix these first. The remaining "}
              <span className="font-semibold">{allLicensingGaps.length}</span>
              {" failures are licensing or service availability gaps."}
            </p>
          </div>
        </div>
      ) : (
        <div className="border-l-4 border-[#16A34A] bg-[#F0FDF4] rounded-r-xl px-5 py-4">
          <div className="flex items-start gap-2">
            <CheckCircle2 size={16} className="text-[#16A34A] flex-shrink-0 mt-0.5" />
            <p className="text-sm text-[#14532D]">
              <span className="font-bold">No security misconfigurations found.</span>
              {" "}
              <span className="font-semibold">{allLicensingGaps.length}</span>
              {" failures are licensing gaps."}
            </p>
          </div>
        </div>
      )}

      {/* ── Change 2: 3 new metric cards ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1 — Security misconfigs (red) */}
        <div className="rounded-xl p-5 border" style={{ backgroundColor: "#FEF2F2", borderColor: "#FECACA" }}>
          <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide mb-3">Security Misconfigurations</p>
          <p className="text-5xl font-black" style={{ color: "#DC2626" }}>{actionable.length}</p>
          <p className="text-sm text-[#6B7280] mt-1">Fix these before Copilot</p>
        </div>

        {/* Card 2 — Licensing / service gaps (amber) */}
        <div className="rounded-xl p-5 border" style={{ backgroundColor: "#FFFBEB", borderColor: "#FDE68A" }}>
          <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide mb-3">Licensing / Service Gaps</p>
          <p className="text-5xl font-black" style={{ color: "#D97706" }}>{allLicensingGaps.length}</p>
          <p className="text-sm text-[#6B7280] mt-1">Upgrade or enable services</p>
        </div>

        {/* Card 3 — Passed (green) */}
        <div className="rounded-xl p-5 border" style={{ backgroundColor: "#F0FDF4", borderColor: "#BBF7D0" }}>
          <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide mb-3">Passed</p>
          <p className="text-5xl font-black" style={{ color: "#16A34A" }}>{pass.length}</p>
          <p className="text-sm text-[#6B7280] mt-1">No action needed</p>
        </div>
      </div>

      {/* ── Change 4: Security Misconfigurations section ── */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden">
        <div className="flex items-center gap-2 px-5 py-3 border-b border-[#E5E7EB] bg-[#FEF2F2]">
          <AlertTriangle size={16} className="text-[#DC2626]" />
          <p className="text-sm font-bold text-[#DC2626]">Security Misconfigurations — Fix These First</p>
          <span className="ml-auto text-xs font-semibold text-[#DC2626]">{actionable.length} issues</span>
        </div>
        {actionable.length === 0 ? (
          <div className="flex items-center gap-2 px-5 py-6">
            <CheckCircle2 size={16} className="text-[#16A34A]" />
            <p className="text-sm text-[#6B7280]">No security misconfigurations identified.</p>
          </div>
        ) : (
          <div>
            {actionableBySev.map(({ sev: s, items: grpItems }) => {
              const hs = SEV_HEADER[s] || SEV_HEADER.low;
              return (
                <div key={s}>
                  <div className="px-5 py-2 border-b border-[#F3F4F6]" style={{ backgroundColor: hs.bg }}>
                    <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: hs.color }}>
                      {s} ({grpItems.length})
                    </span>
                  </div>
                  <div className="divide-y divide-[#F9FAFB]">
                    {grpItems.map((f, i) => (
                      <div key={i} className="flex items-start justify-between gap-4 px-5 py-3 hover:bg-[#FAFAFA] transition-colors">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-[#111827] leading-snug" style={{ fontSize: 14 }}>
                            {f.parameter_name || fmtKey(f.parameter_key)}
                          </p>
                          {getReasonText(f) && (
                            <p className="mt-0.5 text-[#6B7280] leading-snug" style={{ fontSize: 12 }}>
                              {getReasonText(f)}
                            </p>
                          )}
                        </div>
                        <div className="flex-shrink-0 pt-0.5">{severityBadge(f.severity)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Change 5: Licensing gaps (collapsed) ── */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden">
        <button
          className="w-full flex items-center gap-3 px-5 py-3 hover:bg-[#FAFAFA] transition-colors text-left"
          onClick={() => setLicensingExpanded(!licensingExpanded)}
        >
          <Info size={16} className="text-[#9CA3AF] flex-shrink-0" />
          <p className="text-sm font-semibold text-[#374151] flex-shrink-0">
            Licensing gaps ({allLicensingGaps.length}) — upgrade required
          </p>
          <div className="flex items-center gap-1.5 flex-wrap flex-1 min-w-0">
            {Object.entries(svcGroups)
              .filter(([, list]) => list.length > 0)
              .map(([svc, list]) => (
                <span key={svc} className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#F3F4F6] text-[#6B7280]">
                  {svc} ({list.length})
                </span>
              ))}
          </div>
          {licensingExpanded
            ? <ChevronUp size={16} className="text-[#9CA3AF] flex-shrink-0" />
            : <ChevronDown size={16} className="text-[#9CA3AF] flex-shrink-0" />}
        </button>
        {licensingExpanded && (
          <div className="border-t border-[#E5E7EB]">
            {Object.entries(svcGroups)
              .filter(([, list]) => list.length > 0)
              .map(([svc, list]) => (
                <div key={svc} className="border-b border-[#F3F4F6] last:border-b-0">
                  <div className="px-5 py-2 bg-[#F8F9FA]">
                    <span className="text-xs font-semibold text-[#374151] uppercase tracking-wide">{svc}</span>
                  </div>
                  <div className="divide-y divide-[#F9FAFB]">
                    {list.map((f, i) => (
                      <div key={i} className="flex items-start justify-between gap-4 px-5 py-2.5">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-[#374151] leading-snug" style={{ fontSize: 14 }}>
                            {f.parameter_name || fmtKey(f.parameter_key)}
                          </p>
                          {getReasonText(f) && (
                            <p className="mt-0.5 text-[#9CA3AF] leading-snug" style={{ fontSize: 12 }}>
                              {getReasonText(f)}
                            </p>
                          )}
                        </div>
                        <div className="flex-shrink-0 pt-0.5">{severityBadge(f.severity)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* ── Observations card (kept) ── */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-6">
        <p className="text-sm font-bold text-[#111827] mb-4">Observations</p>
        <ul className="space-y-3">
          {[
            `A total of ${totalFails} gaps out of ${total} parameters were identified, distributed across Security, Governance, and Best Practice categories.`,
            `${actionable.length} of those failures are actionable security misconfigurations; the remaining ${allLicensingGaps.length} are licensing or service availability gaps.`,
            `Medium to Critical severity issues make up ${medHighCritPct}% of findings, indicating substantial exposure to operational and compliance risks.`,
            `Gap findings: Security (${pillarPct("Security")}%), Governance (${pillarPct("Governance")}%), Best Practices (${pillarPct("Best Practice")}%).`,
            eligible != null
              ? `There are ${eligible} user accounts out of ${totalUsers ?? "—"} that are eligible for a M365 Copilot license.`
              : "Licensing eligibility was not assessed.",
          ].map((text, i) => (
            <li key={i} className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-[#0078D4] flex-shrink-0 mt-1.5" />
              <span className="text-sm text-[#374151]">{text}</span>
            </li>
          ))}
          <li className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-[#0078D4] flex-shrink-0 mt-1.5" />
            <div className="flex-1">
              <span className="text-sm text-[#374151]">In the past 30 days, activity across M365 services:</span>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <ActivityBar label="OneDrive"   pct={activityData.onedrive}   color="#0078D4" />
                <ActivityBar label="Teams"      pct={activityData.teams}      color="#6264A7" />
                <ActivityBar label="Outlook"    pct={activityData.outlook}    color="#107C10" />
                <ActivityBar label="SharePoint" pct={activityData.sharepoint} color="#038387" />
              </div>
            </div>
          </li>
        </ul>
      </div>
    </div>
  );
}

// ── Tab 2: Detailed Findings ─────────────────────────────────
function DetailedFindingsTab({ result, categorized }) {
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [activeFilter, setActiveFilter] = useState("security");

  const items = result.findings?.items ?? [];
  const recs = result.recommendations ?? [];
  const recsByKey = Object.fromEntries(recs.map((r) => [r.parameter_key, r]));

  const { actionable, licensing, activity, pass } = categorized;
  const allLicensing = [...licensing, ...activity];

  const filterMap = { all: items, security: actionable, licensing: allLicensing, passed: pass };
  const filteredItems = filterMap[activeFilter] ?? items;

  const toggleRow = (id) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const FILTER_BTNS = [
    { key: "security",  label: "Security gaps", color: "#DC2626", activeBg: "#FEF2F2" },
    { key: "all",       label: "All",            color: "#374151", activeBg: "#F3F4F6" },
    { key: "licensing", label: "Licensing",      color: "#D97706", activeBg: "#FFFBEB" },
    { key: "passed",    label: "Passed",          color: "#16A34A", activeBg: "#F0FDF4" },
  ];

  const STATUS_LABELS = {
    pass: "Pass", fail: "Fail", not_collected: "Not Collected",
    manual_validation: "Manual Validation", licensing_required: "Licensing Required",
    collection_error: "Collection Error", service_unavailable: "Service Unavailable",
    skipped: "Skipped",
  };
  const STATUS_COLORS = {
    pass: "#107C10", fail: "#DC2626", licensing_required: "#7C3AED",
    manual_validation: "#D97706", collection_error: "#EA580C",
    service_unavailable: "#6B7280", not_collected: "#6B7280", skipped: "#9CA3AF",
  };

  // Shared row renderer — used by both grouped and flat views
  const renderRow = (f, i, rowKey) => {
    const isOpen = expandedRows.has(rowKey);
    const cleanFinding = getCleanFinding(f.raw_value);
    const fullFinding = getFullFinding(f.raw_value);
    const reasonText = f.evaluated_value || (cleanFinding !== "—" ? cleanFinding : "");
    const rec = recsByKey[f.parameter_key];
    const pillar = getPillar(f);
    const statusLower = (f.status || "").toLowerCase();
    const statusLabel = STATUS_LABELS[statusLower] || (f.status || "Unknown");
    const statusColor = STATUS_COLORS[statusLower] || "#6B7280";
    const docUrl = extractDocUrl(rec?.remediation_steps, f.raw_value);

    return (
      <Fragment key={rowKey}>
        <tr
          className={`border-b border-[#F3F4F6] cursor-pointer hover:bg-[#FAFAFA] transition-colors ${i % 2 === 0 ? "bg-white" : "bg-[#FAFAFA]"}`}
          onClick={() => toggleRow(rowKey)}
        >
          <td className="px-4 py-2.5 text-xs text-[#9CA3AF]">{i + 1}</td>
          <td className="px-4 py-2.5">
            <div className="flex items-start gap-2">
              <div className="mt-0.5 flex-shrink-0">{statusIcon(f.status)}</div>
              <div className="min-w-0">
                <p className="font-medium text-[#111827] truncate max-w-[220px]" style={{ fontSize: 14 }}>
                  {f.parameter_name || fmtKey(f.parameter_key)}
                </p>
                {reasonText && (
                  <p className="text-[#6B7280] truncate max-w-[260px] leading-snug" style={{ fontSize: 12 }}>
                    {reasonText.length > 110 ? reasonText.slice(0, 110) + "…" : reasonText}
                  </p>
                )}
              </div>
            </div>
          </td>
          <td className="px-4 py-2.5 hidden md:table-cell">
            <span
              className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
              style={{
                backgroundColor: pillar === "Security" ? "#FEE2E2" : pillar === "Governance" ? "#FFEDD5" : "#DBEAFE",
                color: pillar === "Security" ? "#DC2626" : pillar === "Governance" ? "#EA580C" : "#2563EB",
              }}
            >
              {pillar}
            </span>
          </td>
          <td className="px-4 py-2.5 text-[#6B7280] max-w-[200px] hidden md:table-cell">
            <span className="block truncate text-xs">{cleanFinding}</span>
          </td>
          <td className="px-4 py-2.5">{severityBadge(f.severity)}</td>
          <td className="px-2 py-2.5 text-[#9CA3AF]">
            {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </td>
        </tr>

        {isOpen && (
          <tr>
            <td
              colSpan={6}
              className="border-b border-[#E5E7EB]"
              style={{ borderLeft: `4px solid ${SEV_STYLE[(f.severity || "info").toLowerCase()]?.color ?? "#6B7280"}` }}
            >
              <div className="bg-[#F8FAFF] px-6 py-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-semibold text-[#6B7280] mb-1.5 uppercase tracking-wide">Risk Rating</p>
                    <div className="flex items-center gap-2">
                      {severityBadge(f.severity)}
                      <span className="text-xs font-medium" style={{ color: statusColor }}>– {statusLabel}</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-[#6B7280] mb-1.5 uppercase tracking-wide">Description</p>
                    <p className="text-xs text-[#374151]">
                      {fullFinding !== "No specific data collected" ? fullFinding : (f.parameter_name || fmtKey(f.parameter_key))}
                    </p>
                  </div>
                  {rec?.recommendation_text && (
                    <div>
                      <p className="text-xs font-semibold text-[#6B7280] mb-1.5 uppercase tracking-wide">Risk</p>
                      <p className="text-xs text-[#374151]">{rec.recommendation_text}</p>
                    </div>
                  )}
                  {rec?.remediation_steps?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-[#6B7280] mb-1.5 uppercase tracking-wide">Remediation Steps</p>
                      <ol className="text-xs text-[#374151] space-y-0.5 list-decimal list-inside">
                        {rec.remediation_steps.slice(0, 3).map((step, si) => (
                          <li key={si}>{String(step).slice(0, 140)}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
                {docUrl && (
                  <div className="mt-3 pt-3 border-t border-[#E5E7EB]">
                    <a
                      href={docUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs text-[#0078D4] hover:underline font-medium"
                    >
                      <ExternalLink size={12} />
                      Microsoft Documentation →
                    </a>
                  </div>
                )}
              </div>
            </td>
          </tr>
        )}
      </Fragment>
    );
  };

  // Domain-grouped structure (used for "all" filter)
  const domainOrder = DOMAINS.map((d) => d.cat);
  const grouped = {};
  items.forEach((f) => {
    const cat = f.category || "Other";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(f);
  });
  const orderedCats = [
    ...domainOrder.filter((c) => grouped[c]),
    ...Object.keys(grouped).filter((c) => !domainOrder.includes(c)),
  ];

  const TABLE_HEAD = (
    <thead>
      <tr className="bg-[#F8F9FA] border-b border-[#E5E7EB]">
        <th className="text-left text-xs font-semibold text-[#6B7280] px-4 py-2.5 w-10">#</th>
        <th className="text-left text-xs font-semibold text-[#6B7280] px-4 py-2.5">Parameter</th>
        <th className="text-left text-xs font-semibold text-[#6B7280] px-4 py-2.5 hidden md:table-cell">CRA Pillar</th>
        <th className="text-left text-xs font-semibold text-[#6B7280] px-4 py-2.5 hidden md:table-cell">Finding</th>
        <th className="text-left text-xs font-semibold text-[#6B7280] px-4 py-2.5">Severity</th>
        <th className="w-8 px-2" />
      </tr>
    </thead>
  );

  return (
    <div className="space-y-4">
      {/* ── Change 7: Filter buttons ── */}
      <div className="flex gap-2 flex-wrap items-center">
        {FILTER_BTNS.map(({ key, label, color, activeBg }) => {
          const isActive = activeFilter === key;
          const count = filterMap[key]?.length ?? 0;
          return (
            <button
              key={key}
              onClick={() => setActiveFilter(key)}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors"
              style={{
                backgroundColor: isActive ? activeBg : "white",
                color: isActive ? color : "#6B7280",
                borderColor: isActive ? color : "#E5E7EB",
              }}
            >
              {label} ({count})
            </button>
          );
        })}
      </div>

      {activeFilter === "all" ? (
        // Domain-grouped view
        <div className="space-y-6">
          {orderedCats.length === 0 && (
            <p className="text-sm text-[#6B7280] py-6 text-center">No finding details available.</p>
          )}
          {orderedCats.map((cat) => {
            const dom = DOMAIN_BY_CAT[cat] || { label: cat, color: "#6B7280", bg: "#F3F4F6", icon: Shield };
            const catFindings = grouped[cat];
            const Icon = dom.icon || Shield;
            const allSkipped = catFindings.every((f) =>
              ["skipped", "service_unavailable", "manual_validation", "licensing_required"].includes((f.status || "").toLowerCase())
            );
            return (
              <div key={cat} className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden">
                <div className="flex items-center gap-3 px-5 py-3" style={{ backgroundColor: dom.color, color: "#fff" }}>
                  <Icon size={18} />
                  <span className="font-bold text-sm">{dom.label}</span>
                  <span className="ml-auto text-xs opacity-75">{catFindings.length} parameters</span>
                </div>
                {allSkipped && (
                  <div className="flex items-center gap-2 px-5 py-2.5 bg-[#F8F9FA] border-b border-[#E5E7EB]">
                    <div className="w-2 h-2 rounded-full bg-[#9CA3AF]" />
                    <span className="text-xs text-[#6B7280]">
                      {dom.label} was not assessed — service requires delegated authentication.
                    </span>
                  </div>
                )}
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    {TABLE_HEAD}
                    <tbody>{catFindings.map((f, i) => renderRow(f, i, `${cat}-${i}`))}</tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        // Flat filtered view
        <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden">
          {filteredItems.length === 0 ? (
            <p className="text-sm text-[#6B7280] py-8 text-center">No findings in this category.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                {TABLE_HEAD}
                <tbody>{filteredItems.map((f, i) => renderRow(f, i, `flat-${activeFilter}-${i}`))}</tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Tab 3: Recommendations ────────────────────────────────────
function RecommendationsTab({ result }) {
  const recs = result.recommendations ?? [];

  const order = ["critical", "high", "medium", "low"];
  const byPriority = order
    .map((sev) => ({
      sev,
      items: recs
        .filter((r) => (r.severity || "").toLowerCase() === sev)
        .sort((a, b) => (a.title || "").localeCompare(b.title || "")),
    }))
    .filter((g) => g.items.length > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-[#EFF6FC] border border-[#DEECF9] rounded-xl p-5 space-y-2">
        <p className="text-sm font-semibold text-[#005A9E]">Remediation Priority</p>
        <p className="text-sm text-[#374151]">
          Remediation of identified gaps: Address all findings to meet cybersecurity baseline standards.
        </p>
        <p className="text-sm text-[#374151]">
          <b>Postpone Deployment:</b> Recommended to adopt Copilot after all critical and high-priority gaps are resolved.
        </p>
      </div>

      {recs.length === 0 ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-sm font-semibold text-[#6B7280]">No recommendations data available for this assessment.</p>
          <p className="text-xs text-[#9CA3AF]">Run a new assessment to generate recommendations.</p>
        </div>
      ) : (
        byPriority.map(({ sev, items }) => {
          const style = SEV_STYLE[sev] || SEV_STYLE.info;
          return (
            <div key={sev}>
              <h3
                className="text-sm font-bold uppercase tracking-wide px-4 py-2 rounded-lg mb-3"
                style={{ backgroundColor: style.bg, color: style.color }}
              >
                {sev} Priority ({items.length})
              </h3>
              <div className="space-y-3">
                {items.map((r, i) => {
                  const docUrl = extractDocUrl(r.remediation_steps, null);
                  return (
                    <div
                      key={i}
                      className="bg-white border border-[#E5E7EB] rounded-xl p-5"
                      style={{ borderLeft: `4px solid ${style.color}` }}
                    >
                      <div className="flex items-start gap-3 flex-wrap mb-3">
                        {severityBadge(r.severity)}
                        <p className="text-sm font-semibold text-[#111827] flex-1">{r.title || fmtKey(r.parameter_key)}</p>
                        {r.effort && effortBadge(r.effort)}
                      </div>
                      <p className="text-sm text-[#6B7280] mb-3">{r.recommendation_text}</p>
                      {r.remediation_steps?.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-[#6B7280] uppercase mb-2">Remediation Steps</p>
                          <ol className="text-xs text-[#374151] space-y-1 list-decimal list-inside">
                            {r.remediation_steps.map((step, si) => (
                              <li key={si}>{String(step).slice(0, 200)}</li>
                            ))}
                          </ol>
                        </div>
                      )}
                      {docUrl && (
                        <div className="mt-3 pt-3 border-t border-[#E5E7EB]">
                          <a
                            href={docUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs text-[#0078D4] hover:underline font-medium"
                          >
                            <ExternalLink size={12} />
                            Microsoft Documentation →
                          </a>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

// ── Tab 4: Roadmap ────────────────────────────────────────────
function RoadmapTab({ result }) {
  const items = result.findings?.items ?? [];
  const recs = result.recommendations ?? [];
  const recsByKey = Object.fromEntries(recs.map((r) => [r.parameter_key, r]));

  const fails = items.filter((f) => (f.status || "").toLowerCase() === "fail");

  function bucket(severities) {
    return fails.filter((f) => severities.includes((f.severity || "").toLowerCase()));
  }

  const cols = [
    { label: "30 Days",  items: bucket(["critical"]),         color: "#DC2626", bg: "#FEE2E2" },
    { label: "60 Days",  items: bucket(["high"]),             color: "#EA580C", bg: "#FFEDD5" },
    { label: "90 Days",  items: bucket(["medium", "low"]),    color: "#0078D4", bg: "#DBEAFE" },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {cols.map(({ label, items: colItems, color, bg }) => (
        <div key={label}>
          <div className="rounded-xl px-4 py-3 font-bold text-sm mb-3" style={{ backgroundColor: bg, color }}>
            {label}
            <span className="ml-2 font-normal text-xs opacity-75">({colItems.length} actions)</span>
          </div>
          <div className="space-y-2">
            {colItems.length === 0 ? (
              <p className="text-xs text-[#9CA3AF] px-2 py-3">No items for this phase.</p>
            ) : (
              colItems.map((f, i) => {
                const rec = recsByKey[f.parameter_key];
                const dom = DOMAIN_BY_CAT[f.category] || { label: f.category, color: "#6B7280", bg: "#F3F4F6" };
                const firstStep = rec?.remediation_steps?.[0];
                return (
                  <div key={i} className="bg-white border border-[#E5E7EB] rounded-lg p-3" style={{ borderTop: `3px solid ${color}` }}>
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium mb-2"
                      style={{ backgroundColor: dom.bg || "#F3F4F6", color: dom.color || "#374151" }}
                    >
                      {dom.label}
                    </span>
                    <p className="text-xs font-semibold text-[#111827] leading-snug">
                      {f.parameter_name || fmtKey(f.parameter_key)}
                    </p>
                    {firstStep && (
                      <p className="text-xs text-[#6B7280] mt-1">{String(firstStep).slice(0, 100)}</p>
                    )}
                    {rec?.effort && (
                      <div className="mt-2">
                        <span
                          className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border"
                          style={{
                            color: rec.effort === "Low" ? "#16A34A" : rec.effort === "Medium" ? "#CA8A04" : "#DC2626",
                            borderColor: rec.effort === "Low" ? "#16A34A" : rec.effort === "Medium" ? "#CA8A04" : "#DC2626",
                          }}
                        >
                          {rec.effort} effort
                        </span>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Report Modal ──────────────────────────────────────────────
const GEN_MESSAGES = [
  [0,  "Preparing assessment data…"],
  [30, "Applying report template…"],
  [60, "Generating document…"],
  [85, "Finalizing report…"],
];

function ReportModal({ assessmentId, tenantName, onClose }) {
  const toast   = useToast();
  const pollRef = useRef(null);
  const [phase, setPhase]             = useState("config");
  const [genProgress, setGenProgress] = useState(0);
  const [genMsg, setGenMsg]           = useState("");
  const [reportType, setReportType]   = useState("docx");

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const startPolling = () => {
    let polls = 0;
    pollRef.current = setInterval(async () => {
      polls++;
      if (polls > 30) { clearInterval(pollRef.current); setPhase("error"); return; }
      try {
        const report = await getAssessmentReport(assessmentId);
        if (report?.status === "generated" || report?.pdf_url) {
          clearInterval(pollRef.current);
          setGenProgress(100);
          setGenMsg("Report ready!");
          setTimeout(() => setPhase("done"), 400);
        }
      } catch { /* ignore */ }
    }, 2000);
  };

  const handleGenerate = async () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setPhase("generating");
    setGenProgress(10);
    setGenMsg("Preparing assessment data…");
    let fakeProgress = 10;
    const fakeInterval = setInterval(() => {
      fakeProgress = Math.min(fakeProgress + 4, 80);
      setGenProgress(fakeProgress);
      const msg = GEN_MESSAGES.slice().reverse().find(([p]) => fakeProgress >= p)?.[1] ?? "";
      setGenMsg(msg);
    }, 700);
    try {
      const result = await generateAssessmentReport(assessmentId, reportType);
      clearInterval(fakeInterval);
      setGenProgress(85);
      setGenMsg("Finalizing report…");

      // Check if PDF conversion failed but DOCX succeeded
      if (result.pdf_conversion_error && reportType === "both") {
        toast.warning(
          "DOCX report generated successfully. PDF conversion failed. " +
          "You can download the DOCX report instead."
        );
      }

      startPolling();
    } catch (error) {
      clearInterval(fakeInterval);
      const errorMsg = error?.response?.data?.detail || error?.message || "Failed to generate report.";
      toast.error(errorMsg);
      setPhase("error");
    }
  };

  const handleDownload = async (reportType) => {
    try {
      const { data } = await downloadAssessmentReport(assessmentId, reportType);
      const date = new Date().toISOString().slice(0, 10);
      const safeName = (tenantName || "tenant").replace(/\s+/g, "_").replace(/[^a-zA-Z0-9_-]/g, "");
      const url = URL.createObjectURL(data);
      const a   = document.createElement("a");
      a.href     = url;
      a.download = `CRA_Report_${safeName}_${date}.${reportType}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success(`${reportType.toUpperCase()} downloaded`);
    } catch {
      toast.error(`Failed to download ${reportType.toUpperCase()} report.`);
    }
  };

  return (
    <Modal
      title={phase === "config" ? "Generate Readiness Report" : undefined}
      onClose={phase !== "generating" ? onClose : undefined}
      maxWidth="480px"
      footer={
        phase === "config" ? (
          <>
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button variant="primary" onClick={handleGenerate}>Generate Report</Button>
          </>
        ) : phase === "error" ? (
          <>
            <Button variant="ghost" onClick={onClose}>Close</Button>
            <Button variant="primary" onClick={handleGenerate}>Try Again</Button>
          </>
        ) : undefined
      }
    >
      {phase === "config" && (
        <div className="space-y-3">
          <div className="flex items-start gap-3 p-4 rounded-lg bg-[#EFF6FC]">
            <FileText size={20} className="text-[#0078D4] mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-[#111827]">Report Output</p>
              <p className="text-xs text-[#6B7280]">DOCX preserves the Word template most reliably. PDF requires Word or LibreOffice conversion.</p>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-[#374151]" htmlFor="report-type">Output format</label>
            <select
              id="report-type"
              value={reportType}
              onChange={(event) => setReportType(event.target.value)}
              className="w-full rounded-lg border border-[#D1D5DB] bg-white px-3 py-2 text-sm text-[#111827]"
            >
              <option value="docx">Word DOCX - recommended</option>
              <option value="pdf">PDF only</option>
              <option value="both">Word DOCX and PDF</option>
            </select>
          </div>
        </div>
      )}

      {phase === "generating" && (
        <div className="py-8 text-center space-y-5">
          <Loader2 size={48} className="animate-spin text-[#0078D4] mx-auto" />
          <p className="text-base font-semibold text-[#374151]">{genMsg}</p>
          <div className="w-full bg-[#E5E7EB] rounded-full h-2 overflow-hidden">
            <div className="h-2 rounded-full bg-[#0078D4] transition-all duration-500" style={{ width: `${genProgress}%` }} />
          </div>
          <p className="text-xs text-[#9CA3AF]">{genProgress}% complete</p>
        </div>
      )}

      {phase === "done" && (
        <div className="py-8 text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-[#DFF6DD] flex items-center justify-center mx-auto">
            <Check size={32} className="text-[#107C10]" />
          </div>
          <h3 className="text-xl font-bold text-[#111827]">Report ready!</h3>
          <div className="flex flex-col gap-2">
            {(reportType === "docx" || reportType === "both") && (
              <Button variant="primary" fullWidth onClick={() => handleDownload("docx")}>
                <Download size={16} /> Download DOCX
              </Button>
            )}
            {(reportType === "pdf" || reportType === "both") && (
              <Button variant={reportType === "pdf" ? "primary" : "secondary"} fullWidth onClick={() => handleDownload("pdf")}>
                <Download size={16} /> Download PDF
              </Button>
            )}
          </div>
        </div>
      )}

      {phase === "error" && (
        <div className="py-8 text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-[#FDE7E9] flex items-center justify-center mx-auto">
            <XCircle size={32} className="text-[#D13438]" />
          </div>
          <h3 className="text-lg font-bold text-[#111827]">Report generation failed</h3>
          <p className="text-sm text-[#6B7280]">
            {reportType === "both"
              ? "PDF conversion failed. Try selecting 'Word DOCX - recommended' instead."
              : "An error occurred. Please try again or use a different format."}
          </p>
        </div>
      )}
    </Modal>
  );
}

// ── Main Page ─────────────────────────────────────────────────
const TABS = ["Key Observations", "Detailed Findings", "Recommendations", "Roadmap"];

export default function ResultsPage() {
  const { assessmentId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const [result, setResult]             = useState(null);
  const [activeTab, setActiveTab]       = useState(0);
  const [showReport, setShowReport]     = useState(false);
  const [rerunning, setRerunning]       = useState(false);
  const [skippedBanner, setSkippedBanner] = useState(true);
  const [showCustomizeModal, setShowCustomizeModal] = useState(false);
  const [logoFile, setLogoFile] = useState(null);
  const [logoPreview, setLogoPreview] = useState(null);
  const [companyName, setCompanyName] = useState("");
  const [address, setAddress] = useState("");
  const [customizing, setCustomizing] = useState(false);

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
    return () => { cancelled = true; };
  }, [assessmentId]);

  if (loading) return <CenteredSpinner label="Loading results…" />;
  if (error || !result) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <XCircle size={48} className="text-[#D13438]" />
        <p className="text-base font-semibold text-[#374151]">{error ?? "Results not found."}</p>
        <div className="flex items-center gap-3">
          <Button variant="primary" onClick={() => window.location.reload()}>
            Retry
          </Button>
          <Button variant="secondary" onClick={() => navigate("/assessments")}>
            <ChevronLeft size={16} /> Back to Assessments
          </Button>
        </div>
      </div>
    );
  }

  const assessment = result.assessment ?? {};
  const scores     = result.scores     ?? {};
  const allFindings = result.findings?.items ?? [];
  const categorized = buildCategorized(allFindings);
  const tenantName = assessment.tenant_name ?? "Assessment";
  const runDate    = assessment.completed_at || assessment.started_at;
  const isRunning  = assessment.status && assessment.status !== "completed";

  // Detect skipped domains (skippable + null score)
  const skippedDomains = SCORE_DOMAINS.filter(
    (d) => d.skippable && scores[d.key] == null
  );
  const hasSkipped = skippedDomains.length > 0;

  const handleRerun = async () => {
    const tenantId = assessment.tenant_id;
    if (!tenantId) { toast.error("Tenant ID not available."); return; }
    setRerunning(true);
    try {
      const newAssessment = await startAssessment(tenantId);
      navigate(`/assessments/${newAssessment.id}/progress`);
    } catch {
      toast.error("Failed to start assessment. Please try again.");
      setRerunning(false);
    }
  };

  return (
    <>
      <div className="flex gap-6">
        {/* ── Left sticky sidebar ── */}
        <div className="hidden lg:block flex-shrink-0" style={{ width: 280 }}>
          <div className="sticky top-[calc(var(--topbar-height,56px)+1.5rem)] bg-white border border-[#E5E7EB] rounded-xl shadow-sm overflow-hidden">
            {/* Tenant name */}
            <div className="p-4 border-b border-[#E5E7EB]">
              <Link to="/assessments" className="inline-flex items-center gap-1.5 text-xs text-[#6B7280] hover:text-[#111827] mb-3">
                <ChevronLeft size={14} /> Assessments
              </Link>
              <p className="text-sm font-bold text-[#111827]">{tenantName}</p>
              {runDate && <p className="text-xs text-[#9CA3AF] mt-0.5">{fmtDate(runDate)}</p>}
            </div>

            {/* Score gauge */}
            <div className="p-4">
              <ScoreGauge score={assessment.overall_score} />
            </div>

            {/* Domain score bars — smart coloring */}
            <div className="px-4 pb-4 space-y-3">
              {SCORE_DOMAINS.map(({ key, label }) => {
                const v = scores[key];
                const rule = getDomainRule(key, v, allFindings);

                if (rule === "C") {
                  // Licensing — excluded
                  return (
                    <div key={key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#9CA3AF]">{label}</span>
                        <span className="font-semibold text-[#9CA3AF] ml-2">Excl.</span>
                      </div>
                      <div className="h-[5px] rounded-full bg-[#F3F4F6]" />
                      <p className="text-[10px] text-[#9CA3AF] mt-0.5">Excluded from score</p>
                    </div>
                  );
                }

                if (rule === "B") {
                  // Not assessed — gray dashed
                  return (
                    <div key={key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#9CA3AF]">{label}</span>
                        <span className="font-semibold text-[#9CA3AF] ml-2">N/A</span>
                      </div>
                      <div className="h-[5px] rounded-full bg-[#F3F4F6] border border-dashed border-[#D1D5DB]" />
                      <p className="text-[10px] text-[#9CA3AF] mt-0.5">Not assessed</p>
                    </div>
                  );
                }

                if (rule === "A") {
                  // Determine if this domain's fails are actionable or licensing-only (Change 6)
                  const domDef = SCORE_DOMAINS.find((x) => x.key === key);
                  const domCats = domDef?.cats ?? [];
                  const domFails = allFindings.filter((f) =>
                    domCats.length > 0
                      ? domCats.includes(f.category || "")
                      : (f.status || "").toLowerCase() === "fail"
                  );
                  const domActionable = domFails.filter((f) => categorizeFinding(f) === "actionable");
                  const isLicensingOnly = domActionable.length === 0 && domFails.length > 0;

                  if (isLicensingOnly) {
                    return (
                      <div key={key}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#9CA3AF]">{label}</span>
                          <span className="font-semibold text-[#9CA3AF] ml-2">0%</span>
                        </div>
                        <div className="relative h-[5px] rounded-full bg-[#F3F4F6]">
                          <div className="absolute left-0 top-0 h-full w-[3px] min-w-[3px] rounded-full bg-[#9CA3AF]" />
                        </div>
                        <p className="text-[10px] text-[#9CA3AF] mt-0.5">Service not available</p>
                      </div>
                    );
                  }

                  // Has actionable fails — red
                  return (
                    <div key={key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#DC2626] font-medium">{label}</span>
                        <span className="font-semibold text-[#DC2626] ml-2">0%</span>
                      </div>
                      <div className="relative h-[5px] rounded-full bg-[#FEE2E2]">
                        <div className="absolute left-0 top-0 h-full w-[3px] min-w-[3px] rounded-full bg-[#DC2626]" />
                      </div>
                      <p className="text-[10px] text-[#DC2626] mt-0.5">
                        {domActionable.length} security gap{domActionable.length !== 1 ? "s" : ""}
                      </p>
                    </div>
                  );
                }

                // Rule D — normal colored bar
                const barColor = getScoreBarColor(v ?? 0);
                return (
                  <div key={key}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-[#374151]">{label}</span>
                      <span className="font-semibold text-[#111827] ml-2">{Math.round(v ?? 0)}%</span>
                    </div>
                    <div className="h-[5px] rounded-full bg-[#E5E7EB] overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${v ?? 0}%`, backgroundColor: barColor }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Actions */}
            <div className="p-4 border-t border-[#E5E7EB] space-y-2 flex flex-col">
              <Button variant="primary" fullWidth onClick={() => setShowCustomizeModal(true)} className="justify-center h-10 rounded-lg">
                <FileText size={16} /> Customize & Generate
              </Button>
              <Button variant="secondary" fullWidth size="sm" onClick={() => setShowReport(true)} disabled={isRunning} className="justify-center">
                <Download size={15} /> Quick Generate
              </Button>
              <Button variant="secondary" fullWidth size="sm" loading={rerunning} onClick={handleRerun} disabled={isRunning || rerunning} className="justify-center">
                <RotateCcw size={14} /> Re-run Assessment
              </Button>
            </div>
          </div>
        </div>

        {/* ── Right content ── */}
        <div className="flex-1 min-w-0">
          <Link to="/assessments" className="lg:hidden inline-flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#111827] mb-4">
            <ChevronLeft size={16} /> Assessments
          </Link>

          <div className="mb-5">
            <p className="text-xs text-[#9CA3AF] uppercase tracking-wide">Copilot Readiness Assessment</p>
            <h1 className="text-2xl font-black text-[#111827]">{tenantName}</h1>
            <div className="flex items-center gap-4 mt-1 flex-wrap">
              {runDate && <p className="text-sm text-[#6B7280]">Assessment date: {fmtDate(runDate)}</p>}
              <p className="text-sm text-[#9CA3AF]">Prepared by: CRA Tool</p>
            </div>
          </div>

          <div className="lg:hidden mb-4 flex gap-2">
            <Link to={`/assessments/${assessmentId}/report`} className="flex-1">
              <Button variant="primary" fullWidth>
                <FileText size={15} /> Customize
              </Button>
            </Link>
            <Button variant="secondary" fullWidth loading={rerunning} onClick={handleRerun} disabled={isRunning || rerunning}>
              <RotateCcw size={14} /> Re-run
            </Button>
          </div>

          {isRunning && (
            <div className="flex items-center gap-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800 mb-4">
              <Clock size={16} className="flex-shrink-0" />
              <span className="flex-1">Assessment is still {assessment.status}. Results may be incomplete.</span>
              <Link to={`/assessments/${assessmentId}/progress`} className="font-semibold underline whitespace-nowrap">
                View Progress →
              </Link>
            </div>
          )}

          {hasSkipped && skippedBanner && (
            <div className="flex items-start gap-3 p-3 bg-[#F8F9FA] border border-[#E5E7EB] rounded-lg text-sm text-[#6B7280] mb-4">
              <Info size={15} className="flex-shrink-0 mt-0.5 text-[#9CA3AF]" />
              <span className="flex-1">
                <strong className="text-[#374151]">Partial assessment: </strong>
                {skippedDomains.map((d) => d.label).join(" and ")} {skippedDomains.length === 1 ? "was" : "were"} not assessed — {skippedDomains.length === 1 ? "it requires" : "they require"} delegated authentication (device code flow). Scores shown reflect available services only.
              </span>
              <button
                onClick={() => setSkippedBanner(false)}
                className="text-[#9CA3AF] hover:text-[#6B7280] flex-shrink-0 text-xs font-medium"
                title="Dismiss"
              >
                ✕
              </button>
            </div>
          )}

          <ExecSummaryCard result={result} />

          <div className="results-tab-bar">
            {TABS.map((t, i) => (
              <button
                key={t}
                className={["results-tab", activeTab === i ? "active" : ""].join(" ")}
                onClick={() => setActiveTab(i)}
              >
                {t}
              </button>
            ))}
          </div>

          <div className="mt-4">
            {activeTab === 0 && <KeyObservationsTab result={result} categorized={categorized} />}
            {activeTab === 1 && <DetailedFindingsTab result={result} categorized={categorized} />}
            {activeTab === 2 && <RecommendationsTab result={result} />}
            {activeTab === 3 && <RoadmapTab result={result} />}
          </div>
        </div>
      </div>

      {showReport && (
        <ReportModal
          assessmentId={assessmentId}
          tenantName={tenantName}
          onClose={() => setShowReport(false)}
        />
      )}

      {showCustomizeModal && (
        <Modal onClose={() => setShowCustomizeModal(false)}>
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">📋 Customize Report</h2>

            {/* Logo Upload */}
            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2">🎨 Company Logo</label>
              {logoPreview ? (
                <div className="border rounded-lg p-3 bg-gray-50 flex items-center justify-between">
                  <img src={logoPreview} alt="Logo" className="h-12 w-auto" />
                  <button
                    onClick={() => { setLogoFile(null); setLogoPreview(null); }}
                    className="text-sm text-blue-600 hover:text-blue-800 font-semibold"
                  >
                    Change
                  </button>
                </div>
              ) : (
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/svg+xml"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setLogoFile(file);
                      const reader = new FileReader();
                      reader.onload = (event) => setLogoPreview(event.target?.result);
                      reader.readAsDataURL(file);
                    }
                  }}
                  className="w-full text-sm"
                />
              )}
            </div>

            {/* Company Name */}
            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2">🏢 Company Name</label>
              <input
                type="text"
                placeholder="e.g., Acme Corporation"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600"
              />
            </div>

            {/* Address */}
            <div className="mb-6">
              <label className="block text-sm font-semibold mb-2">📍 Company Address</label>
              <textarea
                placeholder="e.g., 123 Business St, City, State 12345"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                rows="3"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600 resize-none"
              />
            </div>

            {/* Buttons */}
            <div className="flex gap-2">
              <button
                onClick={() => setShowCustomizeModal(false)}
                className="flex-1 px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  try {
                    setCustomizing(true);
                    await customizeAssessmentReport(assessmentId, { logoFile, companyName, address });
                    setShowCustomizeModal(false);
                    setLogoFile(null);
                    setLogoPreview(null);
                    setCompanyName("");
                    setAddress("");
                    setShowReport(true);
                  } catch (err) {
                    toast.error(err?.message || "Failed to customize report");
                  } finally {
                    setCustomizing(false);
                  }
                }}
                disabled={customizing || (!logoFile && !companyName && !address)}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold disabled:opacity-50"
              >
                {customizing ? "Applying..." : "Apply & Generate"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
