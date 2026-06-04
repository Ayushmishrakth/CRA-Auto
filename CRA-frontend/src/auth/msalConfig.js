/**
 * MSAL configuration — multi-tenant CRA SaaS (SPA).
 * Values align with Azure App Registration (Entra ID).
 */

function browserOrigin() {
  return typeof window === "undefined" ? "http://localhost:3000" : window.location.origin;
}

export const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_MSAL_CLIENT_ID,

    authority:
      import.meta.env.VITE_MSAL_AUTHORITY ||
      "https://login.microsoftonline.com/common",

    redirectUri:
      import.meta.env.VITE_MSAL_REDIRECT_URI ||
      browserOrigin(),

    postLogoutRedirectUri:
      import.meta.env.VITE_MSAL_REDIRECT_URI ||
      browserOrigin(),

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
  postLogoutRedirectUri:
    import.meta.env.VITE_MSAL_REDIRECT_URI ||
    browserOrigin(),
  mainWindowRedirectUri:
    import.meta.env.VITE_MSAL_REDIRECT_URI ||
    browserOrigin(),
};
