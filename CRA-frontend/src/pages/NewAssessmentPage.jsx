import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Shield, Lock, Mail, Users, FolderOpen, CreditCard,
  Check, ChevronRight, ChevronLeft, Clock, AlertCircle,
} from "lucide-react";
import { WizardProvider, useWizard } from "../context/WizardContext";
import StepIndicator from "../components/ui/StepIndicator";
import Button from "../components/ui/Button";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";
import { startAssessment } from "../api/assessmentApi";
import { deployTenantAccess, listTenants, validateTenantConsent } from "../api/tenantApi";
import { getApiErrorMessage } from "../utils/apiErrors";

const STEPS = ["Connect Tenant", "Review & Launch"];

const MODULES = [
  { key: "identity",   icon: Shield,     color: "#0078D4", bg: "#EFF6FC", label: "Identity & Access",    desc: "MFA, Conditional Access, guest users, SSPR" },
  { key: "security",   icon: Lock,       color: "#D13438", bg: "#FDE7E9", label: "Security Posture",      desc: "Defender, DLP policies, Secure Score, compliance" },
  { key: "exchange",   icon: Mail,       color: "#FF8C00", bg: "#FFF4CE", label: "Exchange Online",       desc: "Mailbox policies, anti-phishing, encryption" },
  { key: "teams",      icon: Users,      color: "#5C2D91", bg: "#F4EEF9", label: "Microsoft Teams",       desc: "Governance, external sharing, meeting policies" },
  { key: "sharepoint", icon: FolderOpen, color: "#107C10", bg: "#DFF6DD", label: "SharePoint & OneDrive", desc: "Sharing settings, sensitivity labels, sync" },
  { key: "licensing",  icon: CreditCard, color: "#0097A7", bg: "#E0F7FA", label: "Licensing & Cost",      desc: "Copilot eligibility, license count, ROI estimate" },
];

const POLL_INTERVAL_MS = 3000;
const POLL_MAX = 100; // ~5 minutes

// ── Step 1: Connect Tenant ──────────────────────────────────
function Step1({ onNext }) {
  const { user, getTenantDeploymentToken } = useAuth();
  const { tenantInfo, setTenantInfo } = useWizard();
  // idle | deploying | waiting | success | error | timeout | validating
  const [phase, setPhase] = useState(() => (tenantInfo.connected ? "validating" : "idle"));
  const [error, setError] = useState(null);
  const [validationError, setValidationError] = useState(null);
  const [isStale, setIsStale] = useState(false);
  const pollRef = useRef(null);
  const credRef = useRef(null); // { tenantId, graphAccessToken }

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current);
  }, []);

  // Auto-detect and validate already-connected tenant (once only)
  useEffect(() => {
    let isMounted = true;

    const validateConnection = async () => {
      try {
        // Load tenant list from database
        const tenants = await listTenants();
        if (!isMounted) return;

        const active = (Array.isArray(tenants) ? tenants : tenants?.items ?? [])
          .find((t) => t.status === "ACTIVE");

        if (!active) {
          setPhase("idle");
          return;
        }

        // Found ACTIVE tenant in DB - now validate it still exists in Azure
        try {
          const graphAccessToken = await getTenantDeploymentToken();
          if (!isMounted) return;

          // Call validation endpoint to check if app registration exists
          const validationResult = await validateTenantConsent({
            tenantId: active.tenant_id,
            graphAccessToken,
          });

          if (!isMounted) return;

          // Validation succeeded - connection is real
          if (validationResult?.status === "ACTIVE") {
            setTenantInfo({
              connected: true,
              tenantId: active.tenant_id,
              tenantName: active.tenant_name || active.tenant_id,
            });
            setPhase("success");
            setIsStale(false);
            setValidationError(null);
          } else {
            // Validation returned non-ACTIVE status
            setTenantInfo({
              connected: true,
              tenantId: active.tenant_id,
              tenantName: active.tenant_name || active.tenant_id,
            });
            setPhase("success");
            setIsStale(true);
            setValidationError("App registration deleted or permissions revoked. Click 'Reconnect' to fix.");
          }
        } catch (validationErr) {
          if (!isMounted) return;
          // Validation failed - app registration likely deleted
          setTenantInfo({
            connected: true,
            tenantId: active.tenant_id,
            tenantName: active.tenant_name || active.tenant_id,
          });
          setPhase("success");
          setIsStale(true);
          setValidationError("App registration was deleted from Azure. Click 'Reconnect' to recreate it.");
        }
      } catch (err) {
        if (!isMounted) return;
        setPhase("idle");
      }
    };

    validateConnection();

    return () => {
      isMounted = false;
    };
  }, []); // Run only once on mount

  const startPolling = (tenantId, graphAccessToken) => {
    let polls = 0;
    pollRef.current = setInterval(async () => {
      polls++;
      if (polls > POLL_MAX) {
        clearInterval(pollRef.current);
        setPhase("timeout");
        return;
      }
      try {
        const result = await validateTenantConsent({ tenantId, graphAccessToken });
        if (result?.status === "ACTIVE") {
          clearInterval(pollRef.current);
          setTenantInfo({
            connected: true,
            tenantId,
            tenantName: result.tenant_name || result.tenantName || tenantId,
          });
          setPhase("success");
        }
      } catch {
        // Ignore individual poll errors — keep trying
      }
    }, POLL_INTERVAL_MS);
  };

  const handleConnect = async () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setPhase("deploying");
    setError(null);
    try {
      const graphAccessToken = await getTenantDeploymentToken();
      const tenantId = user.microsoft_tid;
      credRef.current = { tenantId, graphAccessToken };

      const result = await deployTenantAccess({
        tenantId,
        graphAccessToken,
        redirectUri: `${window.location.origin}/tenant/deployment-success`,
      });

      if (result?.admin_consent_url) {
        window.open(result.admin_consent_url, "_blank", "noopener,noreferrer");
      }

      setPhase("waiting");
      startPolling(tenantId, graphAccessToken);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to start tenant deployment"));
      setPhase("error");
    }
  };

  const handleRetry = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setPhase("idle");
    setError(null);
  };

  const isConnected = phase === "success" || tenantInfo.connected;
  const isBusy = phase === "deploying" || phase === "waiting";

  return (
    <div className="space-y-5">
      {/* Info banner */}
      <div className="flex gap-3 p-4 rounded-lg bg-[#EFF6FC] border border-[#DEECF9]">
        <AlertCircle size={18} className="text-[#0078D4] flex-shrink-0 mt-0.5" />
        <p className="text-sm text-[#005A9E]">
          A <strong>Global Administrator</strong> of the customer tenant must complete this step.
        </p>
      </div>

      {/* Phase-driven status cards */}
      {isConnected && (
        <div className="space-y-4">
          {isStale ? (
            <div className="flex gap-3 p-4 rounded-lg bg-[#FDE7E9] border border-[#D13438]/20">
              <AlertCircle size={18} className="text-[#D13438] flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-[#D13438] font-semibold">Connection is invalid</p>
                {validationError && <p className="text-xs text-[#D13438] mt-0.5">{validationError}</p>}
              </div>
            </div>
          ) : (
            <div className="flex gap-3 p-4 rounded-lg bg-[#DFF6DD] border border-[#107C10]/20">
              <Check size={18} className="text-[#107C10] flex-shrink-0 mt-0.5" />
              <p className="text-sm text-[#107C10] font-semibold">✓ Tenant connected and verified</p>
            </div>
          )}
          <div className="bg-[#F8F9FA] border border-[#E5E7EB] rounded-lg p-4 space-y-2">
            <Row label="Tenant Name" value={tenantInfo.tenantName || tenantInfo.tenantId} />
            <Row label="Tenant ID"   value={<code className="text-xs font-mono">{tenantInfo.tenantId}</code>} />
            {isStale && <Row label="Status" value="⚠️ Invalid (needs reconnect)" />}
          </div>
        </div>
      )}

      {phase === "waiting" && (
        <div className="flex gap-3 p-4 rounded-lg bg-[#FFF4CE] border border-[#FF8C00]/30">
          <div className="w-2.5 h-2.5 rounded-full bg-[#FF8C00] animate-pulse flex-shrink-0 mt-1" />
          <p className="text-sm text-[#B45309] font-medium">
            Waiting for admin consent… Keep this page open.
          </p>
        </div>
      )}

      {phase === "error" && (
        <div className="flex gap-3 p-4 rounded-lg bg-[#FDE7E9] border border-[#D13438]/20">
          <AlertCircle size={18} className="text-[#D13438] flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-[#D13438] font-medium">Connection failed</p>
            {error && <p className="text-xs text-[#D13438] mt-0.5">{error}</p>}
          </div>
        </div>
      )}

      {phase === "timeout" && (
        <div className="flex gap-3 p-4 rounded-lg bg-[#FDE7E9] border border-[#D13438]/20">
          <AlertCircle size={18} className="text-[#D13438] flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-[#D13438] font-medium">Consent timed out after 5 minutes</p>
            <p className="text-xs text-[#6B7280] mt-0.5">Ask your admin to complete consent, then try again.</p>
          </div>
        </div>
      )}

      {/* Action button — shown when not connected or when stale */}
      {(!isConnected || isStale) && (
        <div className="border border-[#E5E7EB] rounded-lg p-4 space-y-3">
          <p className="text-sm font-semibold text-[#374151]">
            {isStale ? "Reconnect your tenant" : "Connect directly (if you are the admin)"}
          </p>
          <Button
            variant="primary"
            fullWidth
            loading={isBusy}
            onClick={isBusy ? undefined : phase === "error" || phase === "timeout" ? handleRetry : handleConnect}
            disabled={isBusy}
          >
            {phase === "deploying"
              ? "Creating app registration…"
              : phase === "waiting"
              ? "Waiting for admin consent…"
              : phase === "error" || phase === "timeout"
              ? "Try Again"
              : isStale
              ? "Reconnect Microsoft 365 Tenant"
              : "Connect Microsoft 365 Tenant"}
          </Button>
        </div>
      )}

      {/* Read-only permissions list */}
      <div className="border border-[#E5E7EB] rounded-lg p-4">
        <p className="text-sm font-semibold text-[#374151] mb-3">Permissions requested (read-only)</p>
        <ul className="space-y-2">
          {[
            "Read user accounts and licenses",
            "Read Teams usage and activity reports",
            "Read SharePoint site metrics",
            "Read security and compliance configuration",
            "Read sign-in logs and audit events",
          ].map((p) => (
            <li key={p} className="flex items-center gap-2.5 text-sm text-[#374151]">
              <Check size={14} className="text-[#107C10] flex-shrink-0" />
              {p}
            </li>
          ))}
        </ul>
        <p className="text-xs text-[#6B7280] mt-3 pt-3 border-t border-[#E5E7EB]">
          We never access email content, file content, or passwords.
        </p>
      </div>

      <div className="flex justify-end pt-2">
        <Button variant="primary" disabled={!isConnected || isStale} onClick={onNext}>
          Review & Launch <ChevronRight size={16} />
        </Button>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-28 text-[#6B7280] flex-shrink-0">{label}</span>
      <span className="text-[#111827] font-medium">{value}</span>
    </div>
  );
}

// ── Step 3: Review & Launch ─────────────────────────────────
function Step3({ onBack }) {
  const navigate = useNavigate();
  const toast = useToast();
  const { tenantInfo, selectedModules } = useWizard();
  const [launching, setLaunching] = useState(false);

  const count = Object.values(selectedModules).filter(Boolean).length;
  const estMins = Math.max(1, Math.ceil(count * 0.67));

  const handleLaunch = async () => {
    setLaunching(true);
    try {
      const result = await startAssessment(tenantInfo.tenantId);
      navigate(`/assessments/${result.id}/progress`);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Failed to start assessment. Please try again."));
      setLaunching(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Tenant */}
      <div className="border-l-4 border-[#107C10] border border-[#E5E7EB] rounded-lg p-4">
        <div className="flex items-center gap-2 mb-1">
          <Check size={16} className="text-[#107C10]" />
          <p className="text-sm font-semibold text-[#107C10]">Microsoft 365 tenant connected</p>
        </div>
        <p className="text-sm text-[#6B7280] ml-6">{tenantInfo.tenantName || tenantInfo.tenantId}</p>
        <p className="text-xs font-mono text-[#9CA3AF] ml-6 mt-0.5">{tenantInfo.tenantId}</p>
      </div>

      {/* Time estimate */}
      <div className="flex items-center gap-2 p-3 rounded-lg bg-[#F8F9FA] border border-[#E5E7EB]">
        <Clock size={16} className="text-[#6B7280]" />
        <p className="text-sm text-[#6B7280]">
          Estimated time: <strong className="text-[#111827]">~{estMins} minute{estMins !== 1 ? "s" : ""}</strong>
        </p>
      </div>

      <div className="border-t border-[#E5E7EB] pt-4">
        <Button
          variant="primary"
          fullWidth
          size="lg"
          loading={launching}
          onClick={handleLaunch}
          className="font-bold text-base"
        >
          {launching ? "Launching assessment…" : "Start Assessment"}
        </Button>
        <p className="text-center text-xs text-[#9CA3AF] mt-3">
          The assessment runs in the background. You can close this window and return to view results.
        </p>
      </div>

      <div className="flex justify-start pt-0">
        <Button variant="ghost" onClick={onBack} disabled={launching}>
          <ChevronLeft size={16} /> Back
        </Button>
      </div>
    </div>
  );
}

// ── Wizard wrapper ──────────────────────────────────────────
function WizardInner() {
  const { currentStep, setStep } = useWizard();

  const stepComponents = [
    <Step1 key={0} onNext={() => setStep(1)} />,
    <Step3 key={1} onBack={() => setStep(0)} />,
  ];

  const titles = [
    { title: "Connect Microsoft 365 Tenant", subtitle: "Securely connect to your customer's Microsoft 365 environment." },
    { title: "Review & Launch Assessment",   subtitle: "Confirm all details before starting." },
  ];

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <StepIndicator steps={STEPS} currentStep={currentStep} />

      <div className="bg-white border border-[#E5E7EB] rounded-xl shadow-sm">
        <div className="px-6 pt-6 pb-2 border-b border-[#F3F4F6]">
          <h2 className="text-lg font-bold text-[#111827] m-0">{titles[currentStep].title}</h2>
          <p className="text-sm text-[#6B7280] mt-1">{titles[currentStep].subtitle}</p>
        </div>
        <div className="p-6">{stepComponents[currentStep]}</div>
      </div>
    </div>
  );
}

export default function NewAssessmentPage() {
  return (
    <WizardProvider>
      <WizardInner />
    </WizardProvider>
  );
}
