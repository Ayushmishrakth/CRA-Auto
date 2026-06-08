/**
 * MSAL configuration for the CRA application.
 * All Azure AD values are read from VITE_MSAL_* environment variables.
 * Set these in CRA-frontend/.env — never hardcode credentials in source.
 */

function browserOrigin() {
  return typeof window === "undefined" ? "http://localhost:3000" : window.location.origin;
}

/** Extract the tenant segment from an authority URL (e.g. "common" or a GUID). */
function _extractTenantFromAuthority(authority) {
  const m = (authority || "").match(/login\.microsoftonline\.com\/([^/?#\s]+)/);
  return m ? m[1] : "";
}

export const CRA_AUTH_CLIENT_ID =
  import.meta.env.VITE_MSAL_CLIENT_ID ||
  "702eb094-c0a3-4950-bdab-ca97d2c256be";

export const CRA_AUTH_AUTHORITY =
  import.meta.env.VITE_MSAL_AUTHORITY ||
  "https://login.microsoftonline.com/common";

/**
 * Tenant ID derived from the authority URL.
 * Will be "common" when multi-tenant authority is used — tenant
 * assertion is skipped in that case (see msalAuth.js).
 */
export const CRA_AUTH_TENANT_ID = _extractTenantFromAuthority(CRA_AUTH_AUTHORITY);

/**
 * Login popup redirect URI — must be the plain origin registered as an SPA
 * redirect URI in Azure Portal (e.g. http://localhost:3000).
 * Do NOT use a sub-path here; the popup flow only needs the origin.
 */
const _loginRedirectUri =
  import.meta.env.VITE_MSAL_REDIRECT_URI || browserOrigin();

export const msalConfig = {
  auth: {
    clientId: CRA_AUTH_CLIENT_ID,
    authority: CRA_AUTH_AUTHORITY,
    redirectUri: _loginRedirectUri,
    postLogoutRedirectUri: _loginRedirectUri,
    navigateToLoginRequestUrl: false,
  },

  cache: {
    cacheLocation: "sessionStorage",
    storeAuthStateInCookie: false,
  },
};

export const loginRequest = {
  scopes: ["openid", "profile", "email"],
};

/** Used by silent / popup token acquisition after login. */
export const tokenRequest = {
  scopes: loginRequest.scopes,
};

export const tenantDeploymentRequest = {
  scopes: [
    "https://graph.microsoft.com/User.Read",
    "https://graph.microsoft.com/Directory.Read.All",
    "https://graph.microsoft.com/Application.ReadWrite.All",
    "https://graph.microsoft.com/AppRoleAssignment.ReadWrite.All",
  ],
};

/** Used by logout popup. */
export const logoutRequest = {
  postLogoutRedirectUri: _loginRedirectUri,
  mainWindowRedirectUri: _loginRedirectUri,
};
