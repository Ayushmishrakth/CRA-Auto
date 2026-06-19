import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { Eye, EyeOff, Copy, RefreshCw, ExternalLink, Check } from "lucide-react";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Modal from "../components/ui/Modal";
import { useToast } from "../context/ToastContext";

const TABS = ["Profile", "Branding", "Notifications", "API & Integrations"];

// ── Profile tab ─────────────────────────────────────────────
function ProfileTab({ user }) {
  const fields = [
    { label: "Full Name",     value: user?.display_name || user?.name || "—" },
    { label: "Email",         value: user?.email || "—" },
    { label: "Organization",  value: user?.organization || "—" },
    { label: "Role",          value: user?.role || "Admin" },
  ];

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 p-4 rounded-lg bg-[#EFF6FC] border border-[#DEECF9]">
        <Badge variant="info">Managed by Microsoft account</Badge>
        <p className="text-sm text-[#374151]">Profile details are managed through your Microsoft 365 account.</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {fields.map(({ label, value }) => (
          <div key={label} className="space-y-1">
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide">{label}</p>
            <div className="h-10 px-3 flex items-center bg-[#F8F9FA] border border-[#E5E7EB] rounded-lg text-sm text-[#374151]">
              {value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Branding tab ────────────────────────────────────────────
function BrandingTab() {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [partnerName, setPartnerName] = useState("Your Company Ltd");
  const [brandColor, setBrandColor] = useState("#0078D4");

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 800));
    setSaving(false);
    toast.success("Branding saved successfully.");
  };

  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <label className="text-sm font-medium text-[#374151]">Partner company name</label>
        <input
          type="text"
          value={partnerName}
          onChange={(e) => setPartnerName(e.target.value)}
          className="w-full h-10 px-3 text-sm border border-[#D1D5DB] rounded-lg focus:outline-none focus:border-[#0078D4] focus:ring-1 focus:ring-[#0078D4]"
        />
      </div>

      <div className="space-y-1">
        <label className="text-sm font-medium text-[#374151]">Company logo</label>
        <div className="border-2 border-dashed border-[#D1D5DB] rounded-lg p-6 text-center text-sm text-[#9CA3AF] cursor-pointer hover:border-[#0078D4] hover:text-[#0078D4] transition-colors">
          Drag & drop logo (PNG/SVG) or{" "}
          <span className="underline font-semibold">browse</span>
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-sm font-medium text-[#374151]">Primary brand color</label>
        <div className="flex items-center gap-3">
          <input
            type="color"
            value={brandColor}
            onChange={(e) => setBrandColor(e.target.value)}
            className="w-10 h-10 rounded-lg border border-[#D1D5DB] cursor-pointer p-1"
          />
          <input
            type="text"
            value={brandColor}
            onChange={(e) => setBrandColor(e.target.value)}
            className="w-32 h-10 px-3 font-mono text-sm border border-[#D1D5DB] rounded-lg focus:outline-none focus:border-[#0078D4]"
          />
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-sm font-medium text-[#374151]">Report footer text</label>
        <textarea
          rows={2}
          placeholder="Prepared by Your Company Ltd · Confidential"
          className="w-full px-3 py-2.5 text-sm border border-[#D1D5DB] rounded-lg focus:outline-none focus:border-[#0078D4] resize-none"
        />
      </div>

      <Button variant="primary" loading={saving} onClick={handleSave}>
        Save Branding
      </Button>
    </div>
  );
}

// ── Notifications tab ───────────────────────────────────────
function NotificationsTab() {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [prefs, setPrefs] = useState({
    assessment_complete: true,
    report_generated:    true,
    weekly_summary:      false,
    assessment_failed:   true,
  });

  const NOTIFS = [
    { key: "assessment_complete", label: "Assessment complete",     sub: "Email notification"        },
    { key: "report_generated",    label: "Report generated",        sub: "Email notification"        },
    { key: "weekly_summary",      label: "Weekly summary",          sub: "Every Monday 9am"          },
    { key: "assessment_failed",   label: "Assessment failed",       sub: "Immediate alert"           },
  ];

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 600));
    setSaving(false);
    toast.success("Notification preferences saved.");
  };

  return (
    <div className="space-y-5">
      <div className="space-y-3">
        {NOTIFS.map(({ key, label, sub }) => (
          <div key={key} className="flex items-center justify-between py-3 border-b border-[#F3F4F6]">
            <div>
              <p className="text-sm font-semibold text-[#374151]">{label}</p>
              <p className="text-xs text-[#9CA3AF]">{sub}</p>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={prefs[key]}
                onChange={(e) => setPrefs((p) => ({ ...p, [key]: e.target.checked }))}
              />
              <span className="toggle-track" />
            </label>
          </div>
        ))}
      </div>
      <Button variant="primary" loading={saving} onClick={handleSave}>
        Save Preferences
      </Button>
    </div>
  );
}

// ── API & Integrations tab ───────────────────────────────────
function ApiTab({ user }) {
  return (
    <div className="space-y-5">
      <Card header={{ title: "App Registration" }}>
        <div className="space-y-3">
          {[
            { label: "Application ID",   value: user?.app_client_id || "702eb094-c0a3-4950-bdab-ca97d2c256be", mono: true },
            { label: "Directory Tenant", value: user?.tenant_id || "common",                                   mono: true },
            { label: "Created",          value: "2025-01-15",                                                  mono: false },
          ].map(({ label, value, mono }) => (
            <div key={label} className="flex items-start gap-3">
              <span className="w-36 text-sm text-[#6B7280] flex-shrink-0 pt-0.5">{label}</span>
              <span className={["text-sm text-[#374151] break-all", mono ? "font-mono" : ""].join(" ")}>
                {value}
              </span>
            </div>
          ))}
        </div>
        <a
          href="https://portal.azure.com"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 mt-4 text-sm text-[#0078D4] hover:underline"
        >
          View in Azure Portal <ExternalLink size={13} />
        </a>
      </Card>
    </div>
  );
}

// ── Main ─────────────────────────────────────────────────────
export default function SettingsPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(0);

  const CONTENT = [
    <ProfileTab key="profile" user={user} />,
    <BrandingTab key="branding" />,
    <NotificationsTab key="notif" />,
    <ApiTab key="api" user={user} />,
  ];

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-xl font-bold text-[#111827] mb-5">Settings</h2>

      <div className="grid grid-cols-1 sm:grid-cols-[200px_1fr] gap-6">
        {/* Sub-nav */}
        <div className="bg-white border border-[#E5E7EB] rounded-xl p-3 shadow-sm h-fit">
          <nav className="settings-subnav">
            {TABS.map((t, i) => (
              <button
                key={t}
                className={["settings-subnav-item", activeTab === i ? "active" : ""].join(" ")}
                onClick={() => setActiveTab(i)}
              >
                {t}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-sm">
          <h3 className="text-base font-bold text-[#111827] mb-4 pb-3 border-b border-[#F3F4F6]">
            {TABS[activeTab]}
          </h3>
          {CONTENT[activeTab]}
        </div>
      </div>
    </div>
  );
}
