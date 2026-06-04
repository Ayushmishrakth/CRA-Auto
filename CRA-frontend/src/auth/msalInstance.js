import { PublicClientApplication, EventType } from "@azure/msal-browser";
import { msalConfig } from "./msalConfig";

let instance = null;

/**
 * Singleton MSAL instance — initialized once in main.jsx before React render.
 */
export function createMsalInstance() {
  if (!instance) {
    instance = new PublicClientApplication(msalConfig);
  }
  return instance;
}

export function getMsalInstance() {
  if (!instance) {
    throw new Error("MSAL not initialized. Call createMsalInstance() in main.jsx first.");
  }
  return instance;
}

/**
 * Subscribe to MSAL lifecycle events (dev debugging).
 */
export function registerMsalEventCallbacks(msalInstance) {
  if (!import.meta.env.DEV) return;

  msalInstance.addEventCallback((event) => {
    if (
      event.eventType === EventType.LOGIN_SUCCESS ||
      event.eventType === EventType.ACQUIRE_TOKEN_SUCCESS
    ) {
      console.info("[CRA] MSAL event:", event.eventType, event.payload?.account?.username);
    }
    if (event.eventType === EventType.LOGIN_FAILURE) {
      console.error("[CRA] MSAL login failure:", event.error);
    }
  });
}
