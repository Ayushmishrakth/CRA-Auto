import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, CheckCircle2, RefreshCw, ShieldCheck, Check } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import api from "../api/axiosClient";
import {
  deployTenantAccess,
  listTenants,
  validateTenantConsent,
} from "../api/tenantApi";
import LoadingSpinner from "../components/LoadingSpinner";
import Button from "../components/ui/Button";
import { getApiErrorMessage } from "../utils/apiErrors";

const PERMISSIONS = [
  "Read user accounts and licenses",
  "Read Teams usage and activity reports",
  "Read SharePoint site metrics",
  "Read security and compliance configuration",
  "Read sign-in logs and audit events",
];

export default function TenantConnectionPage() {
  const { user, getTenantDeploymentToken } = useAuth();
  const navigate = useNavigate();
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(true);
  const [phase, setPhase] = useState("idle"); // idle | deploying | consent | validating | success | error
  const [error, setError] = useState(null);

  // Load existing tenant on mount
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listTenants()
      .then((items) => {
        if (!cancelled) {
          const activeTenant = items?.[0];
          if (activeTenant?.status === "ACTIVE") {
            setTenant(activeTenant);
            setPhase("success");
          } else {
            setPhase("idle");
          }
        }
      })
      .catch((err) => {
        if (!cancelled) setPhase("idle");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Step 1: Deploy app registration
  const handleCreateAppRegistration = async () => {
    setPhase("deploying");
    setError(null);
    try {
      const graphAccessToken = await getTenantDeploymentToken();
      const result = await deployTenantAccess({
        tenantId: user.microsoft_tid,
        graphAccessToken,
        redirectUri: window.location.origin,
      });
      setTenant(result);
      setPhase("consent"); // Show permission list for user to accept
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to create app registration"));
      setPhase("error");
    }
  };

  // Step 2: User accepts permissions and validates
  const handleAcceptPermissions = async () => {
    setPhase("validating");
    setError(null);
    try {
      const result = await validateTenantConsent({
        tenantId: user.microsoft_tid,
        graphAccessToken,
      });

      if (result?.status === "ACTIVE") {
        setTenant(result);
        setPhase("success");
      } else {
        setError("Admin consent validation failed. Please try again.");
        setPhase("consent");
      }
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to validate permissions"));
      setPhase("consent");
    }
  };

  if (loading) return <LoadingSpinner label="Loading tenant connection..." />;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Tenant Connection</h1>
          <p className="welcome">
            Tenant <span className="mono">{user.microsoft_tid}</span>
          </p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* Phase: Idle - Not Connected */}
      {phase === "idle" && (
        <section className="panel">
          <div className="panel-header">
            <h2>Connect Microsoft 365 Tenant</h2>
            <p>Securely connect to your Microsoft 365 environment.</p>
          </div>
          <div className="space-y-4">
            <div className="flex gap-3 p-4 rounded-lg bg-[#EFF6FC] border border-[#DEECF9]">
              <div className="w-3 h-3 rounded-full bg-[#0078D4] flex-shrink-0 mt-1" />
              <p className="text-sm text-[#005A9E]">
                A <strong>Global Administrator</strong> of the customer tenant must complete this step.
              </p>
            </div>

            <Button
              variant="primary"
              fullWidth
              loading={phase === "deploying"}
              onClick={handleCreateAppRegistration}
              disabled={phase === "deploying"}
            >
              <ShieldCheck size={16} />
              Create App Registration
            </Button>
          </div>
        </section>
      )}

      {/* Phase: Deploying */}
      {phase === "deploying" && (
        <section className="panel">
          <LoadingSpinner label="Creating app registration..." />
        </section>
      )}

      {/* Phase: Consent - Show Permissions List */}
      {phase === "consent" && (
        <section className="panel">
          <div className="panel-header">
            <h2>Review Permissions</h2>
            <p>Accept these read-only permissions to complete the connection.</p>
          </div>

          <div className="space-y-4">
            <div className="border border-[#E5E7EB] rounded-lg p-4 bg-[#F8F9FA]">
              <p className="text-sm font-semibold text-[#374151] mb-3">Permissions requested (read-only)</p>
              <ul className="space-y-2">
                {PERMISSIONS.map((perm) => (
                  <li key={perm} className="flex items-center gap-2.5 text-sm text-[#374151]">
                    <Check size={16} className="text-[#107C10] flex-shrink-0" />
                    {perm}
                  </li>
                ))}
              </ul>
              <p className="text-xs text-[#6B7280] mt-4 pt-4 border-t border-[#E5E7EB]">
                ✓ We never access email content, file content, or passwords.
              </p>
            </div>

            <Button
              variant="primary"
              fullWidth
              loading={phase === "validating"}
              onClick={handleAcceptPermissions}
              disabled={phase === "validating"}
            >
              {phase === "validating" ? "Processing..." : "Accept & Connect"}
            </Button>
          </div>
        </section>
      )}

      {/* Phase: Validating */}
      {phase === "validating" && (
        <section className="panel">
          <LoadingSpinner label="Validating permissions..." />
        </section>
      )}

      {/* Phase: Success */}
      {phase === "success" && tenant && (
        <section className="panel">
          <div className="space-y-4">
            <div className="flex gap-3 p-4 rounded-lg bg-[#DFF6DD] border border-[#107C10]/20">
              <CheckCircle2 size={18} className="text-[#107C10] flex-shrink-0 mt-0.5" />
              <p className="text-sm text-[#107C10] font-semibold">✓ Tenant connected successfully</p>
            </div>

            <div className="bg-[#F8F9FA] border border-[#E5E7EB] rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-3 text-sm">
                <span className="w-32 text-[#6B7280] flex-shrink-0">Tenant Name</span>
                <span className="text-[#111827] font-medium">{tenant.tenant_name || user.microsoft_tid}</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <span className="w-32 text-[#6B7280] flex-shrink-0">Tenant ID</span>
                <code className="text-xs font-mono text-[#111827]">{tenant.tenant_id}</code>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <span className="w-32 text-[#6B7280] flex-shrink-0">Status</span>
                <span className="text-[#107C10] font-medium">✓ Active</span>
              </div>
            </div>

            <Button variant="primary" fullWidth onClick={() => navigate("/dashboard")}>
              Go to Dashboard
            </Button>
          </div>
        </section>
      )}

      {/* Phase: Error */}
      {phase === "error" && (
        <section className="panel">
          <div className="flex gap-3 p-4 rounded-lg bg-[#FDE7E9] border border-[#D13438]/20">
            <AlertTriangle size={18} className="text-[#D13438] flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-[#D13438] font-semibold">Connection failed</p>
              <p className="text-xs text-[#D13438] mt-1">{error}</p>
            </div>
          </div>
          <Button variant="secondary" fullWidth onClick={() => setPhase("idle")} className="mt-4">
            Try Again
          </Button>
        </section>
      )}
    </div>
  );
}
