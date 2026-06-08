import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import {
  createMsalInstance,
  registerMsalEventCallbacks,
} from "./auth/msalInstance";
import { CRA_AUTH_TENANT_ID } from "./auth/msalConfig";
import "./index.css";

function accountTenantId(account) {
  return account?.tenantId || account?.idTokenClaims?.tid || account?.homeAccountId?.split(".")?.[1] || "";
}

const _MULTI_TENANT_MODES = new Set(["common", "organizations", ""]);

function isConfiguredTenantAccount(account) {
  // Multi-tenant / common authority: accept accounts from any tenant.
  if (_MULTI_TENANT_MODES.has(CRA_AUTH_TENANT_ID.toLowerCase())) return true;
  return accountTenantId(account).toLowerCase() === CRA_AUTH_TENANT_ID.toLowerCase();
}

async function bootstrap() {
  const msalInstance = createMsalInstance();
  await msalInstance.initialize();
  registerMsalEventCallbacks(msalInstance);

  const redirectResult = await msalInstance.handleRedirectPromise();
  if (redirectResult?.account && isConfiguredTenantAccount(redirectResult.account)) {
    msalInstance.setActiveAccount(redirectResult.account);
  } else {
    const accounts = msalInstance.getAllAccounts().filter(isConfiguredTenantAccount);
    if (accounts.length > 0) {
      msalInstance.setActiveAccount(accounts[0]);
    } else {
      msalInstance.setActiveAccount(null);
    }
  }

  const root = document.getElementById("root");
  if (!root) throw new Error("CRA root element was not found.");
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

bootstrap().catch((err) => {
  console.error("[CRA] Bootstrap failed:", err);
  if (typeof document === "undefined") return;
  const root = document.getElementById("root");
  if (root) {
    ReactDOM.createRoot(root).render(
      <div className="session-recovery">
        <div className="panel session-panel">
          <h1>CRA startup failed</h1>
          <p>The application could not initialize the Microsoft sign-in session.</p>
          <pre className="error-details">{String(err?.message || err)}</pre>
          <div className="modal-actions">
            <button
              className="primary-action"
              type="button"
              onClick={() => {
                if (typeof window !== "undefined") window.location.href = "/login";
              }}
            >
              Sign in again
            </button>
          </div>
        </div>
      </div>
    );
  }
});
