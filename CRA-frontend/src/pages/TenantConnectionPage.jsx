import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { CheckCircle2, ExternalLink, RefreshCw, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import {
  deployTenantAccess,
  listTenants,
  validateTenantConsent,
} from "../api/tenantApi";
import LoadingSpinner from "../components/LoadingSpinner";
import { getApiErrorMessage } from "../utils/apiErrors";

export default function TenantConnectionPage() {
  const { user, getTenantDeploymentToken } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [tenant, setTenant] = useState(null);
  const [deployment, setDeployment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listTenants()
      .then((items) => {
        if (!cancelled) setTenant(items?.[0] ?? null);
      })
      .catch((err) => {
        if (!cancelled) setError(getApiErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const runDeploy = async () => {
    setBusy(true);
    setError(null);
    try {
      const graphAccessToken = await getTenantDeploymentToken();
      const result = await deployTenantAccess({
        tenantId: user.microsoft_tid,
        graphAccessToken,
        redirectUri: `${window.location.origin}/tenant/deployment-success`,
      });
      setDeployment(result);
      setTenant((current) => ({ ...(current || {}), ...result }));
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to deploy CRA access"));
    } finally {
      setBusy(false);
    }
  };

  const validateConsent = async ({ auto = false } = {}) => {
    setBusy(true);
    setError(null);
    try {
      const graphAccessToken = await getTenantDeploymentToken();
      const result = await validateTenantConsent({
        tenantId: user.microsoft_tid,
        graphAccessToken,
      });
      setDeployment(result);
      setTenant((current) => ({ ...(current || {}), ...result }));
      if (auto && result.status === "ACTIVE") {
        navigate("/tenant", { replace: true });
      }
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to validate admin consent"));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (location.pathname !== "/tenant/deployment-success" || !user?.microsoft_tid) return;
    validateConsent({ auto: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname, user?.microsoft_tid]);

  if (loading) return <LoadingSpinner label="Loading tenant connection..." />;

  const current = deployment || tenant || {};
  const status = current.status || "NOT_DEPLOYED";
  const deploymentStatus = current.deployment_status || status;
  const isActive = status === "ACTIVE";
  const canGrantConsent = Boolean(current.admin_consent_url) && status === "CONSENT_REQUIRED";
  const deployLabel = isActive ? "Repair CRA Access" : "Deploy CRA Access";

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Tenant Connection</h1>
          <p className="welcome">
            Tenant <span className="mono">{user.microsoft_tid}</span>
          </p>
        </div>
        <button type="button" className="primary-action" onClick={runDeploy} disabled={busy}>
          <ShieldCheck size={16} />
          {deployLabel}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {busy && <LoadingSpinner label="Waiting for Microsoft Graph..." />}

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Deployment Status</h2>
            <p>{isActive ? "CRA access is active." : "Deploy the tenant application and grant admin consent before assessments."}</p>
          </div>
        </div>
        <dl className="profile-grid">
          <dt>Tenant Name</dt>
          <dd>{current.tenant_name || user.microsoft_tid}</dd>
          <dt>Tenant ID</dt>
          <dd className="mono">{user.microsoft_tid}</dd>
          <dt>Status</dt>
          <dd>{status}</dd>
          <dt>Deployment</dt>
          <dd>{deploymentStatus}</dd>
          <dt>Consent</dt>
          <dd>{current.consent_status || "pending"}</dd>
          <dt>Application client ID</dt>
          <dd className="mono">{current.app_client_id || "-"}</dd>
          <dt>Secret expiry</dt>
          <dd>{current.secret_expires_at ? new Date(current.secret_expires_at).toLocaleString() : "-"}</dd>
        </dl>
      </section>

      {isActive && (
        <section className="panel">
          <div className="success">
            <CheckCircle2 size={18} />
            CRA Access Successfully Deployed
          </div>
          <button type="button" className="btn-secondary inline" onClick={runDeploy} disabled={busy}>
            <RefreshCw size={16} />
            Repair Permissions
          </button>
          <button type="button" className="primary-action" onClick={() => navigate("/dashboard")}>
            Start Assessment
          </button>
        </section>
      )}

      {current.admin_consent_url && !isActive && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Admin Consent</h2>
              <p>Grant tenant-wide permissions, then validate deployment.</p>
            </div>
          </div>
          <div className="report-actions">
            <a className="primary-action" href={current.admin_consent_url} aria-disabled={!canGrantConsent}>
              <ExternalLink size={16} />
              Grant Admin Consent
            </a>
            <button type="button" className="btn-secondary inline" onClick={validateConsent} disabled={busy}>
              <RefreshCw size={16} />
              Validate Deployment
            </button>
          </div>
        </section>
      )}

      {current.deployment_error && (
        <section className="panel">
          <h2>Last Failure</h2>
          <p className="error-text">{current.deployment_error}</p>
        </section>
      )}
    </div>
  );
}
