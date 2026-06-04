import { Link } from "react-router-dom";
import { useState } from "react";
import { Activity, Database, KeyRound, Trash2 } from "lucide-react";
import { resetTenantAssessmentData } from "../api/adminApi";
import { useAuth } from "../context/AuthContext";
import { useAssessments } from "../context/AssessmentContext";
import { getApiErrorMessage } from "../utils/apiErrors";

const SETTINGS = [
  {
    title: "Tenant Connection",
    description: "Deploy and validate CRA access for the current Microsoft 365 tenant.",
    href: "/tenant",
    icon: KeyRound,
  },
  {
    title: "Parameter Registry",
    description: "Review approved assessment controls, scoring logic, and registry mappings.",
    href: "/parameters",
    icon: Database,
  },
  {
    title: "Operational Diagnostics",
    description: "Open assessment operations for admin-only validation and support review.",
    href: "/assessments",
    icon: Activity,
  },
];

export default function SettingsPage() {
  const { user } = useAuth();
  const { clearTenantAssessments, fetchTenantAssessments } = useAssessments();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [resetBusy, setResetBusy] = useState(false);
  const [resetResult, setResetResult] = useState(null);
  const [resetError, setResetError] = useState("");
  const tenantId = user?.microsoft_tid;

  const runReset = async () => {
    if (!tenantId) return;
    setResetBusy(true);
    setResetError("");
    setResetResult(null);
    try {
      const result = await resetTenantAssessmentData(tenantId);
      clearTenantAssessments(tenantId);
      await fetchTenantAssessments(tenantId, { limit: 100 });
      setResetResult(result);
      setConfirmOpen(false);
    } catch (err) {
      setResetError(getApiErrorMessage(err, "Unable to reset tenant assessment data"));
    } finally {
      setResetBusy(false);
    }
  };

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p>Technical configuration, diagnostics, and governance tools for platform operators.</p>
        </div>
      </div>

      <section className="settings-identity">
        <div>
          <span>Signed in as</span>
          <strong>{user?.display_name || user?.email || "-"}</strong>
        </div>
        <div>
          <span>Tenant</span>
          <strong>{user?.microsoft_tid || "-"}</strong>
        </div>
      </section>

      <section className="settings-grid">
        {SETTINGS.map((item) => {
          const Icon = item.icon;
          return (
            <Link className="settings-card" to={item.href} key={item.title}>
              <Icon size={22} />
              <h2>{item.title}</h2>
              <p>{item.description}</p>
            </Link>
          );
        })}
      </section>

      <section className="tenant-admin-panel">
        <div className="panel-header">
          <div>
            <h2>Tenant Administration</h2>
            <p>Runtime assessment data controls for the currently signed-in tenant.</p>
          </div>
        </div>
        <div className="tenant-admin-row">
          <div>
            <strong>Reset Assessment Data</strong>
            <p>
              Delete CRA assessment results, reports, findings, artifacts, jobs, and runtime
              events for this tenant while preserving registry definitions and configuration.
            </p>
          </div>
          <button
            type="button"
            className="danger-action"
            onClick={() => setConfirmOpen(true)}
            disabled={!tenantId || resetBusy}
          >
            <Trash2 size={16} />
            Reset Assessment Data
          </button>
        </div>
        {resetError && <div className="error-banner">{resetError}</div>}
        {resetResult && (
          <div className="info-banner">
            Reset complete for tenant {resetResult.tenant_id}. Assessments deleted:{" "}
            {resetResult.assessments_deleted}.
          </div>
        )}
      </section>

      {confirmOpen && (
        <div className="modal-backdrop" role="presentation">
          <div className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="tenant-reset-title">
            <h2 id="tenant-reset-title">Reset Assessment Data</h2>
            <p>
              This will permanently delete all CRA assessment results for this tenant. Registry
              definitions and configuration will be preserved.
            </p>
            <div className="confirm-dialog-actions">
              <button type="button" className="secondary-action" onClick={() => setConfirmOpen(false)} disabled={resetBusy}>
                Cancel
              </button>
              <button type="button" className="danger-action" onClick={runReset} disabled={resetBusy}>
                {resetBusy ? "Resetting..." : "Confirm Reset"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
