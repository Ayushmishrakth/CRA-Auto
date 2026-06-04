import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import {
  createMsalInstance,
  registerMsalEventCallbacks,
} from "./auth/msalInstance";
import "./index.css";

async function bootstrap() {
  const msalInstance = createMsalInstance();
  await msalInstance.initialize();
  registerMsalEventCallbacks(msalInstance);

  const redirectResult = await msalInstance.handleRedirectPromise();
  if (redirectResult?.account) {
    msalInstance.setActiveAccount(redirectResult.account);
  } else {
    const accounts = msalInstance.getAllAccounts();
    if (accounts.length > 0) {
      msalInstance.setActiveAccount(accounts[0]);
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
