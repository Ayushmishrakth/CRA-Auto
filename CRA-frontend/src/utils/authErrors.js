import { safeStringify } from "./safeStringify";

const FATAL_AZURE_ERROR_MESSAGES = {
  AADSTS500014:
    "Exchange Online is disabled in this tenant. The Microsoft 365 subscription may have lapsed, or Exchange was disabled by the administrator. The assessment can still run without Exchange data — contact the tenant admin to re-enable Exchange if needed.",
  AADSTS700016:
    "This application is not authorized in the tenant. Ask the tenant admin to approve the app registration.",
  AADSTS50020:
    "The user account does not exist in this tenant. Sign in with the correct tenant account.",
  AADSTS65004:
    "Admin consent was declined. The tenant admin must accept the permissions to continue.",
  AADSTS70011:
    "An invalid scope was requested. Contact your CRA administrator.",
};

export function getFriendlyOAuthError(error, description) {
  const desc = String(description || "");
  for (const [code, message] of Object.entries(FATAL_AZURE_ERROR_MESSAGES)) {
    if (desc.includes(code)) return message;
  }
  if (error === "invalid_resource")
    return "A required Microsoft service is not available in this tenant. The assessment may still run with the available modules.";
  if (error === "access_denied")
    return "Access was denied. The tenant admin must grant consent before CRA can continue.";
  return `Authentication failed (${error || "unknown error"}). Please try again or contact support.`;
}

export function isFatalOAuthError(description) {
  const desc = String(description || "");
  return Object.keys(FATAL_AZURE_ERROR_MESSAGES).some((code) => desc.includes(code));
}

function friendlyAuthMessage(message = "") {
  const text = String(message || "");
  const lower = text.toLowerCase();

  if (
    lower.includes("selected user account does not exist in tenant") ||
    lower.includes("does not exist in tenant") ||
    lower.includes("belongs to a different tenant")
  ) {
    return "Your Microsoft account belongs to a different tenant than the configured application. Please contact your administrator.";
  }
  if (lower.includes("consent") || lower.includes("admin approval") || lower.includes("aadsts65001")) {
    return "Microsoft consent is required before CRA can continue. Please ask your administrator to grant consent for this application.";
  }
  if (lower.includes("invalid microsoft id token")) {
    return text;
  }
  if (lower.includes("expired") || lower.includes("session restore timed out")) {
    return "Your sign-in session has expired. Please sign in again.";
  }
  if (lower.includes("network") || lower.includes("failed to fetch") || lower.includes("no_network_connectivity")) {
    return "Microsoft sign-in is temporarily unavailable. Check your network connection and try again.";
  }

  return text;
}

/**
 * Normalize API and network errors for display in the UI.
 */
export function formatApiError(error) {
  if (!error) {
    return "Request failed";
  }

  if (!error.response) {
    if (error.code === "ERR_NETWORK") {
      return (
        "Cannot reach CRA backend at " +
        (import.meta.env.VITE_API_BASE_URL || "API") +
        ". Start FastAPI: uvicorn app.main:app --reload"
      );
    }
    return friendlyAuthMessage(error.message || "Network error");
  }

  const detail = error.response.data?.detail;
  if (typeof detail === "string") {
    return friendlyAuthMessage(detail);
  }
  if (Array.isArray(detail)) {
    return friendlyAuthMessage(detail.map((d) => d.msg || safeStringify(d, 0)).join("; "));
  }
  return friendlyAuthMessage(error.response.statusText || `Error ${error.response.status}`);
}

export { friendlyAuthMessage };
