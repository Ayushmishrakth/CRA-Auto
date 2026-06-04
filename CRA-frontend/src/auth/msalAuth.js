/**
 * Microsoft login / logout — popup flow with ID token for CRA backend.
 */

import { BrowserAuthError, InteractionRequiredAuthError } from "@azure/msal-browser";
import { loginRequest, logoutRequest, tenantDeploymentRequest, tokenRequest } from "./msalConfig";
import { clearAllAuthCaches } from "./msalCache";

function decodeJwtPayload(token) {
  if (!token || typeof token !== "string" || token.split(".").length !== 3) {
    throw new Error("MSAL did not return a JWT access token for Microsoft Graph.");
  }
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    return JSON.parse(window.atob(padded));
  } catch {
    throw new Error("Microsoft Graph access token payload could not be decoded.");
  }
}

function validateGraphAccessToken(token) {
  const claims = decodeJwtPayload(token);
  const audience = claims.aud;
  const scopes = String(claims.scp || "").split(" ").filter(Boolean);
  const expiresAt = Number(claims.exp || 0) * 1000;
  const diagnostics = {
    issuer: claims.iss,
    audience,
    tenant: claims.tid,
    scopes,
    expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
    token_use: claims.nonce ? "id_token_like" : "access_token",
  };
  console.info("[CRA] Graph deployment token diagnostics", diagnostics);
  if (audience !== "https://graph.microsoft.com" && audience !== "00000003-0000-0000-c000-000000000000") {
    throw new Error(`MSAL returned a token for '${audience}', not Microsoft Graph.`);
  }
  if (!claims.scp) {
    throw new Error("MSAL returned a token without delegated Graph scopes.");
  }
  if (expiresAt && expiresAt <= Date.now()) {
    throw new Error("MSAL returned an expired Microsoft Graph access token.");
  }
  return diagnostics;
}

export function mapMsalError(error) {
  if (!error) return "Unknown authentication error";

  if (error instanceof BrowserAuthError) {
    switch (error.errorCode) {
      case "popup_window_error":
      case "empty_window_error":
        return "Popup blocked. Allow popups for http://localhost:3000 and retry.";
      case "user_cancelled":
        return "Sign-in cancelled.";
      case "monitor_window_timeout":
        return "Microsoft login timed out. Retry.";
      case "no_network_connectivity":
        return "No network. Check your connection.";
      default:
        return error.message || `Microsoft error: ${error.errorCode}`;
    }
  }

  if (error instanceof InteractionRequiredAuthError) {
    return "Additional Microsoft consent required. Contact your admin.";
  }

  return error.message || "Microsoft login failed";
}

/**
 * Popup login → Microsoft ID token (for POST /auth/login).
 */
export async function loginWithMicrosoftPopup(msalInstance) {
  await clearAllAuthCaches(msalInstance);

  let loginResponse;
  try {
    console.info("[CRA] MSAL loginPopup starting…");
    loginResponse = await msalInstance.loginPopup({
      ...loginRequest,
      redirectUri: msalInstance.getConfiguration().auth.redirectUri,
      prompt: "select_account",
    });
    console.info("[CRA] MSAL loginPopup success", loginResponse.account?.username);
  } catch (error) {
    console.error("[CRA] MSAL loginPopup failed", error);
    throw new Error(mapMsalError(error));
  }

  const account = loginResponse.account;
  if (account) {
    msalInstance.setActiveAccount(account);
  }

  let idToken = loginResponse.idToken;
  console.info("[CRA] ID token from loginPopup:", idToken ? "received" : "missing");

  if (!idToken && account) {
    try {
      const silent = await msalInstance.acquireTokenSilent({
        ...tokenRequest,
        account,
      });
      idToken = silent.idToken;
      console.info("[CRA] ID token from acquireTokenSilent:", idToken ? "received" : "missing");
    } catch (silentError) {
      if (silentError instanceof InteractionRequiredAuthError) {
        const popupToken = await msalInstance.acquireTokenPopup({
          ...tokenRequest,
          account,
        });
        idToken = popupToken.idToken;
        console.info("[CRA] ID token from acquireTokenPopup:", idToken ? "received" : "missing");
      } else {
        throw new Error(mapMsalError(silentError));
      }
    }
  }

  if (!idToken) {
    throw new Error(
      "No Microsoft ID token. Verify Azure SPA redirect http://localhost:3000, " +
        "API permissions (openid, profile, email, User.Read), and Client ID in .env."
    );
  }

  return { idToken, account };
}

export async function logoutMicrosoft(msalInstance) {
  const account = msalInstance.getActiveAccount();
  try {
    await msalInstance.logoutPopup({
      ...logoutRequest,
      account: account ?? undefined,
    });
  } finally {
    await clearAllAuthCaches(msalInstance);
  }
}

export async function acquireTenantDeploymentToken(msalInstance) {
  const account = msalInstance.getActiveAccount() || msalInstance.getAllAccounts()[0];
  if (!account) {
    throw new Error("Microsoft session is not active. Sign in again.");
  }
  try {
    const silent = await msalInstance.acquireTokenSilent({
      ...tenantDeploymentRequest,
      account,
    });
    validateGraphAccessToken(silent.accessToken);
    return silent.accessToken;
  } catch (error) {
    if (!(error instanceof InteractionRequiredAuthError)) {
      throw new Error(mapMsalError(error));
    }
    const popup = await msalInstance.acquireTokenPopup({
      ...tenantDeploymentRequest,
      account,
      prompt: "consent",
    });
    validateGraphAccessToken(popup.accessToken);
    return popup.accessToken;
  }
}
