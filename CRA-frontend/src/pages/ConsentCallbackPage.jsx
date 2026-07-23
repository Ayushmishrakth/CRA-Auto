import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, AlertCircle } from "lucide-react";
import Button from "../components/ui/Button";
import { useAuth } from "../context/AuthContext";
import { validateTenantConsent } from "../api/tenantApi";

// Web-platform redirect target for the /adminconsent server-side redirect.
// Azure lands here after a Global Administrator approves (or denies) consent.
export default function ConsentCallbackPage() {
  const navigate = useNavigate();
  const { user, getTenantDeploymentToken } = useAuth();
  // loading | success | granted | error
  const [state, setState] = useState("loading");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const error = params.get("error");
    const errorDescription = params.get("error_description");
    const adminConsent = params.get("admin_consent");

    if (error || adminConsent === "False") {
      setState("error");
      setDetail(
        errorDescription ||
          "Admin consent was denied. Return to CRA, click Open Consent Form again, and sign in as a Global Administrator to approve the permissions."
      );
      return;
    }

    // Consent granted. Best-effort: trigger validate-consent (which assigns the Teams /
    // Exchange roles) if this tab still has an active CRA session. If it does not, the
    // consent itself still succeeded — the original CRA tab finishes it.
    let cancelled = false;
    (async () => {
      try {
        const tenantId = params.get("tenant") || user?.microsoft_tid;
        if (!tenantId) throw new Error("missing tenant id");
        const graphAccessToken = await getTenantDeploymentToken();
        if (cancelled) return;
        await validateTenantConsent({ tenantId, graphAccessToken });
        if (cancelled) return;
        setState("success");
      } catch {
        if (cancelled) return;
        setState("granted");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getTenantDeploymentToken, user]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#F8F9FA] p-6">
      <div className="w-full max-w-md bg-white border border-[#E5E7EB] rounded-lg p-8 text-center space-y-4">
        {state === "loading" && (
          <>
            <div className="mx-auto w-6 h-6 rounded-full border-2 border-[#0078D4] border-t-transparent animate-spin" />
            <p className="text-sm text-[#374151]">Finalizing permissions…</p>
          </>
        )}

        {(state === "success" || state === "granted") && (
          <>
            <div className="mx-auto w-12 h-12 rounded-full bg-[#DFF6DD] flex items-center justify-center">
              <Check size={24} className="text-[#107C10]" />
            </div>
            <p className="text-base font-semibold text-[#107C10]">
              {state === "success" ? "Tenant setup complete" : "Permissions granted successfully"}
            </p>
            <p className="text-sm text-[#6B7280]">
              {state === "success"
                ? "Permissions were granted and the connection was validated. You can close this tab and return to CRA."
                : "Return to the CRA tab and click “I’ve approved — validate permissions” to finish setup."}
            </p>
          </>
        )}

        {state === "error" && (
          <>
            <div className="mx-auto w-12 h-12 rounded-full bg-[#FDE7E9] flex items-center justify-center">
              <AlertCircle size={24} className="text-[#D13438]" />
            </div>
            <p className="text-base font-semibold text-[#D13438]">Consent was not completed</p>
            <p className="text-sm text-[#6B7280]">{detail}</p>
            <Button variant="primary" fullWidth onClick={() => navigate("/assessments/new")}>
              Back to CRA
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
