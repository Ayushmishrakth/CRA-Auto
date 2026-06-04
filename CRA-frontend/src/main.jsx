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

  ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

bootstrap().catch((err) => {
  console.error("[CRA] Bootstrap failed:", err);
  const root = document.getElementById("root");
  if (root) {
    root.innerHTML = `
      <div class="session-recovery">
        <div class="panel session-panel">
          <h1>CRA startup failed</h1>
          <p>The application could not initialize the Microsoft sign-in session.</p>
          <pre class="error-details">${String(err?.message || err)}</pre>
          <div class="modal-actions">
            <button class="primary-action" onclick="window.location.href='/login'">Sign in again</button>
          </div>
        </div>
      </div>
    `;
  }
});
