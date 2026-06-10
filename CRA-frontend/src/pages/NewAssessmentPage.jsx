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

const PERMISSIONS = [
  "Read user accounts and licenses",
  "Read Teams usage and activity reports",
  "Read SharePoint site metrics",
  "Read security and compliance configuration",
  "Read sign-in logs and audit events",
];

// ── Step 1: Connect Tenant (All inline, no redirects) ──────────────────────────────────
function Step1({ onNext }) {
  const { user, getTenantDeploymentToken } = useAuth();
  const { tenantInfo, setTenantInfo } = useWizard();
  // idle | deploying | consent | validating | success | error
  const [phase, setPhase] = useState(() => (tenantInfo.connected ? "success" : "idle"));
  const [error, setError] = useState(null);

  const [adminConsentUrl, setAdminConsentUrl] = useState(null);

  // Load existing tenant AND validate it exists in Azure
  useEffect(() => {
    let isMounted = true;
    if (tenantInfo.connected) return;

    const loadAndValidate = async () => {
      try {
        // Step 1: Load from database
        const tenants = await listTenants();
        if (!isMounted) return;

        const active = (Array.isArray(tenants) ? tenants : tenants?.items ?? [])
          .find((t) => t.status === "ACTIVE");

        if (!active) {
          setPhase("idle");
          return;
        }

        // Step 2: Validate it still exists in Azure
        try {
          const graphAccessToken = await getTenantDeploymentToken();
          if (!isMounted) return;

          const validationResult = await validateTenantConsent({
            tenantId: active.tenant_id,
            graphAccessToken,
          });

          if (!isMounted) return;

          // Validation succeeded - app registration exists
          if (validationResult?.status === "ACTIVE") {
            setTenantInfo({
              connected: true,
              tenantId: active.tenant_id,
              tenantName: active.tenant_name || active.tenant_id,
            });
            setPhase("success");
          } else {
            // Validation failed - app was deleted or needs consent
            setTenantInfo({
              connected: true,
              tenantId: active.tenant_id,
              tenantName: active.tenant_name || active.tenant_id,
            });
            // If consent not granted, show consent URL
            if (validationResult?.admin_consent_url) {
              setAdminConsentUrl(validationResult.admin_consent_url);
              setPhase("consent");
            } else {
              setPhase("error");
              setError("App registration was deleted from Azure. Click 'Try Again' to recreate it.");
            }
          }
        } catch (validationErr) {
          if (!isMounted) return;
          // Validation error - app likely deleted
          setTenantInfo({
            connected: true,
            tenantId: active.tenant_id,
            tenantName: active.tenant_name || active.tenant_id,
          });
          setPhase("error");
          setError("App registration was deleted from Azure. Click 'Try Again' to recreate it.");
        }
      } catch (err) {
        if (!isMounted) return;
        setPhase("idle");
      }
    };

    loadAndValidate();
    return () => {
      isMounted = false;
    };
  }, [getTenantDeploymentToken]); // Re-run if auth context changes

  // Step 1: Create app registration
  const handleCreateAppRegistration = async () => {
    setPhase("deploying");
    setError(null);
    try {
      const graphAccessToken = await getTenantDeploymentToken();
      // Use the correct redirect URI that backend expects
      const redirectUri = `${window.location.origin}/tenant/deployment-success`;
      const result = await deployTenantAccess({
        tenantId: user.microsoft_tid,
        graphAccessToken,
        redirectUri,
      });
      // Store the admin consent URL from the response
      if (result?.admin_consent_url) {
        setAdminConsentUrl(result.admin_consent_url);
      }
      setPhase("consent");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to create app registration"));
      setPhase("error");
    }
  };

  // Step 2: Validate after user grants consent
  const handleValidateConsent = async () => {
    setPhase("validating");
    setError(null);
    try {
      const graphAccessToken = await getTenantDeploymentToken();
      const result = await validateTenantConsent({
        tenantId: user.microsoft_tid,
        graphAccessToken,
      });

      if (result?.status === "ACTIVE") {
        setTenantInfo({
          connected: true,
          tenantId: result.tenant_id || user.microsoft_tid,
          tenantName: result.tenant_name || user.microsoft_tid,
        });
        setPhase("success");
      } else {
        setError("Validation failed. Please ensure you've granted admin consent in Azure.");
        setPhase("consent");
      }
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to validate permissions"));
      setPhase("consent");
    }
  };

  const isConnected = phase === "success" || tenantInfo.connected;

  return (
    <div className="space-y-5">
      {/* Info banner */}
      <div className="flex gap-3 p-4 rounded-lg bg-[#EFF6FC] border border-[#DEECF9]">
        <AlertCircle size={18} className="text-[#0078D4] flex-shrink-0 mt-0.5" />
        <p className="text-sm text-[#005A9E]">
          A <strong>Global Administrator</strong> of the customer tenant must complete this step.
        </p>
      </div>

      {/* Phase: Idle */}
      {phase === "idle" && (
        <Button
          variant="primary"
          fullWidth
          onClick={handleCreateAppRegistration}
        >
          <Shield size={16} />
          Create App Registration
        </Button>
      )}

      {/* Phase: Deploying */}
      {phase === "deploying" && (
        <div className="flex gap-3 p-4 rounded-lg bg-[#FFF4CE] border border-[#FF8C00]/30">
          <div className="w-2.5 h-2.5 rounded-full bg-[#FF8C00] animate-pulse flex-shrink-0 mt-1" />
          <p className="text-sm text-[#B45309] font-medium">Creating app registration...</p>
        </div>
      )}

      {/* Phase: Consent - Show Permissions & Admin Consent Link */}
      {phase === "consent" && (
        <div className="space-y-4">
          <div className="border border-[#E5E7EB] rounded-lg p-4 bg-[#F8F9FA]">
            <p className="text-sm font-semibold text-[#374151] mb-3">Permissions requested (read-only)</p>
            <ul className="space-y-2">
              {PERMISSIONS.map((p) => (
                <li key={p} className="flex items-center gap-2.5 text-sm text-[#374151]">
                  <Check size={16} className="text-[#107C10] flex-shrink-0" />
                  {p}
                </li>
              ))}
            </ul>
            <p className="text-xs text-[#6B7280] mt-4 pt-4 border-t border-[#E5E7EB]">
              ✓ We never access email content, file content, or passwords.
            </p>
          </div>

          {/* Admin Consent Step */}
          {adminConsentUrl && (
            <div className="border border-[#0078D4]/20 rounded-lg p-4 bg-[#EFF6FC]">
              <p className="text-sm font-semibold text-[#374151] mb-3">Step 1: Grant Admin Consent</p>
              <p className="text-xs text-[#6B7280] mb-3">
                A Global Administrator must grant permissions in Azure. Click the button below to open the consent form in a new window.
              </p>
              <Button
                variant="primary"
                fullWidth
                onClick={() => window.open(adminConsentUrl, "_blank", "noopener,noreferrer")}
              >
                Open Consent Form
              </Button>
            </div>
          )}

          {/* Validate Step */}
          <div className="border border-[#107C10]/20 rounded-lg p-4 bg-[#F0FDF4]">
            <p className="text-sm font-semibold text-[#374151] mb-3">Step 2: Validate Connection</p>
            <p className="text-xs text-[#6B7280] mb-3">
              After granting consent, click below to verify the connection.
            </p>
            <Button
              variant="primary"
              fullWidth
              loading={phase === "validating"}
              onClick={handleValidateConsent}
              disabled={phase === "validating"}
            >
              {phase === "validating" ? "Validating..." : "Validate Connection"}
            </Button>
          </div>

          {error && (
            <div className="flex gap-3 p-4 rounded-lg bg-[#FDE7E9] border border-[#D13438]/20">
              <AlertCircle size={18} className="text-[#D13438] flex-shrink-0 mt-0.5" />
              <p className="text-xs text-[#D13438]">{error}</p>
            </div>
          )}
        </div>
      )}

      {/* Phase: Validating */}
      {phase === "validating" && (
        <div className="flex gap-3 p-4 rounded-lg bg-[#FFF4CE] border border-[#FF8C00]/30">
          <div className="w-2.5 h-2.5 rounded-full bg-[#FF8C00] animate-pulse flex-shrink-0 mt-1" />
          <p className="text-sm text-[#B45309] font-medium">Validating permissions...</p>
        </div>
      )}

      {/* Phase: Success */}
      {phase === "success" && isConnected && (
        <div className="space-y-4">
          <div className="flex gap-3 p-4 rounded-lg bg-[#DFF6DD] border border-[#107C10]/20">
            <Check size={18} className="text-[#107C10] flex-shrink-0 mt-0.5" />
            <p className="text-sm text-[#107C10] font-semibold">✓ Tenant connected and verified</p>
          </div>
          <div className="bg-[#F8F9FA] border border-[#E5E7EB] rounded-lg p-4 space-y-2">
            <div className="flex items-center gap-3 text-sm">
              <span className="w-28 text-[#6B7280] flex-shrink-0">Tenant Name</span>
              <span className="text-[#111827] font-medium">{tenantInfo.tenantName || tenantInfo.tenantId}</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span className="w-28 text-[#6B7280] flex-shrink-0">Tenant ID</span>
              <code className="text-xs font-mono text-[#111827]">{tenantInfo.tenantId}</code>
            </div>
          </div>
        </div>
      )}

      {/* Phase: Error */}
      {phase === "error" && (
        <div className="space-y-3">
          <div className="flex gap-3 p-4 rounded-lg bg-[#FDE7E9] border border-[#D13438]/20">
            <AlertCircle size={18} className="text-[#D13438] flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-[#D13438] font-medium">Connection Invalid</p>
              {error && <p className="text-xs text-[#D13438] mt-0.5">{error}</p>}
            </div>
          </div>
          <Button
            variant="primary"
            fullWidth
            onClick={() => {
              setTenantInfo({ connected: false, tenantId: null, tenantName: null });
              setPhase("idle");
              setError(null);
            }}
          >
            Recreate App Registration
          </Button>
        </div>
      )}

      {/* Review & Launch button */}
      <div className="flex justify-end pt-2">
        <Button variant="primary" disabled={!isConnected} onClick={onNext}>
          Review & Launch <ChevronRight size={16} />
        </Button>
      </div>
    </div>
  );
}

// ── Step 2: Review & Launch ─────────────────────────────────
function Step2({ onBack }) {
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
    <Step2 key={1} onBack={() => setStep(0)} />,
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
