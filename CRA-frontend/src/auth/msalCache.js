/**
 * Clear stale MSAL / CRA auth state (fixes redirect mismatch & old client ID cache).
 */

import { tokenStorage } from "../utils/tokenStorage";

const MSAL_KEY_PREFIXES = ["msal.", "msal", "login.", "server-telemetry"];

function clearStorageByPrefix(storage) {
  const keysToRemove = [];
  for (let i = 0; i < storage.length; i++) {
    const key = storage.key(i);
    if (!key) continue;
    if (MSAL_KEY_PREFIXES.some((p) => key.toLowerCase().startsWith(p.toLowerCase()))) {
      keysToRemove.push(key);
    }
  }
  keysToRemove.forEach((k) => storage.removeItem(k));
}

/**
 * Remove MSAL keys from session/local storage and CRA JWT tokens.
 */
export async function clearAllAuthCaches(msalInstance) {
  console.info("[CRA] Clearing MSAL + CRA auth caches");
  clearStorageByPrefix(sessionStorage);
  clearStorageByPrefix(localStorage);
  tokenStorage.clear();

  if (msalInstance?.clearCache) {
    try {
      await msalInstance.clearCache();
    } catch (e) {
      console.warn("[CRA] msal clearCache:", e);
    }
  }

  if (msalInstance?.setActiveAccount) {
    msalInstance.setActiveAccount(null);
  }
}
