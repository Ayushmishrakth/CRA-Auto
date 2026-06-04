import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useMsal } from "@azure/msal-react";
import {
  acquireTenantDeploymentToken,
  loginWithMicrosoftPopup,
  logoutMicrosoft,
} from "../auth/msalAuth";
import { clearAllAuthCaches } from "../auth/msalCache";
import {
  exchangeMicrosoftTokenForCraJwt,
  loadCurrentUser,
  logoutCraSession,
} from "../services/authService";
import { tokenStorage } from "../utils/tokenStorage";
import { formatApiError } from "../utils/authErrors";

const AuthContext = createContext(null);
const SESSION_RESTORE_TIMEOUT_MS = 8000;

function withTimeout(promise, message) {
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = window.setTimeout(() => reject(new Error(message)), SESSION_RESTORE_TIMEOUT_MS);
  });

  return Promise.race([promise, timeout]).finally(() => window.clearTimeout(timeoutId));
}

export function AuthProvider({ children }) {
  const { instance } = useMsal();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const bootstrapPromiseRef = useRef(null);

  const isAuthenticated = Boolean(tokenStorage.hasAccessToken() && user);

  const bootstrap = useCallback(async () => {
    if (bootstrapPromiseRef.current) {
      return bootstrapPromiseRef.current;
    }

    const promise = (async () => {
      setLoading(true);
      setError(null);
      try {
        if (tokenStorage.hasAccessToken()) {
          console.info("[CRA] Restoring session from stored CRA JWT");
          const profile = await withTimeout(
            loadCurrentUser(),
            "Session restore timed out. Please sign in again."
          );
          setUser(profile);
          console.info("[CRA] Session restored:", profile.email);
        } else {
          setUser(null);
        }
        return null;
      } catch (err) {
        console.warn("[CRA] Session restore failed", err);
        tokenStorage.clear();
        setUser(null);
        setError(err.message || "Session restore failed. Please sign in again.");
        return null;
      } finally {
        bootstrapPromiseRef.current = null;
        setLoading(false);
      }
    })();

    bootstrapPromiseRef.current = promise;
    return promise;
  }, []);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const loginWithMicrosoft = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      tokenStorage.clear();
      setUser(null);

      const { idToken } = await loginWithMicrosoftPopup(instance);
      console.info("[CRA] Sending ID token to backend POST /auth/login");

      const { user: profile, tokens } = await exchangeMicrosoftTokenForCraJwt(idToken);
      console.info("[CRA] CRA JWT stored, expires_in:", tokens.expires_in);

      setUser(profile);
      return profile;
    } catch (err) {
      const message = err.response
        ? formatApiError(err)
        : err.message || "Microsoft login failed";
      console.error("[CRA] Login failed:", message);
      setError(message);
      tokenStorage.clear();
      setUser(null);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [instance]);

  const logout = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await logoutCraSession(() => logoutMicrosoft(instance));
      setUser(null);
      console.info("[CRA] Logout complete");
    } catch (err) {
      const message = err.response
        ? formatApiError(err)
        : err.message || "Logout failed";
      setError(message);
      await clearAllAuthCaches(instance);
      tokenStorage.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [instance]);

  const clearAuthCaches = useCallback(() => clearAllAuthCaches(instance), [instance]);

  const getTenantDeploymentToken = useCallback(
    () => acquireTenantDeploymentToken(instance),
    [instance]
  );

  const value = useMemo(
    () => ({
      user,
      loading,
      error,
      isAuthenticated,
      loginWithMicrosoft,
      logout,
      clearAuthCaches,
      getTenantDeploymentToken,
      setError,
      refreshUser: bootstrap,
    }),
    [
      user,
      loading,
      error,
      isAuthenticated,
      loginWithMicrosoft,
      logout,
      clearAuthCaches,
      getTenantDeploymentToken,
      bootstrap,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
