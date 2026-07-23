import axios from "axios";
import { tokenStorage } from "../utils/tokenStorage";
import { extractApiError } from "../utils/apiErrors";
import { publishBackendError } from "../utils/backendErrors";

const baseURL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") ||
  "http://127.0.0.1:8000/api/v1";

const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
  // Progress polling (/job) can be slow while the backend is mid-assessment
  // (PowerShell collectors + Graph calls), so allow more than the default 30s.
  timeout: 120000,
});

const isPublicAuthPath = (url = "") =>
  url.includes("/auth/login") || url.includes("/auth/refresh");
const AUTH_EXPIRED_EVENT = "cra:auth-expired";
const LOGIN_IN_PROGRESS_FLAG = "__CRA_LOGIN_IN_PROGRESS__";

function isLoginInProgress() {
  return Boolean(typeof window !== "undefined" && window[LOGIN_IN_PROGRESS_FLAG]);
}

// The access token is short-lived (ACCESS_TOKEN_EXPIRE_MINUTES). When it expires we
// silently exchange the long-lived refresh token for a new access token and retry the
// request, instead of dumping the user back to the login screen mid-session.
let refreshPromise = null;

async function refreshAccessToken() {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) return null;
  // Bare axios (not the `api` instance) so this never recurses through these interceptors.
  const resp = await axios.post(
    `${baseURL}/auth/refresh`,
    { refresh_token: refreshToken },
    { headers: { "Content-Type": "application/json" }, timeout: 30000 }
  );
  const data = resp?.data?.data || resp?.data || {};
  if (data.access_token) {
    tokenStorage.setTokens({
      access_token: data.access_token,
      refresh_token: data.refresh_token,
    });
    return data.access_token;
  }
  return null;
}

function forceLogout() {
  tokenStorage.clear();
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent(AUTH_EXPIRED_EVENT, {
        detail: { message: "Your sign-in session has expired. Please sign in again." },
      })
    );
  }
}

api.interceptors.request.use((config) => {
  const url = config.url || "";

  if (!isPublicAuthPath(url)) {
    const token = tokenStorage.getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } else {
    delete config.headers.Authorization;
  }

  if (import.meta.env.DEV) {
    console.info(`[CRA] API ${config.method?.toUpperCase()} ${baseURL}${url}`);
  }

  return config;
});

api.interceptors.response.use(
  (response) => {
    if (import.meta.env.DEV && response.config.url?.includes("/auth/login")) {
      console.info("[CRA] Backend auth/login success — CRA JWT received");
    }
    return response;
  },
  async (error) => {
    const original = error.config || {};
    const status = error.response?.status;

    if (status === 401 && !isPublicAuthPath(original.url) && !isLoginInProgress()) {
      // First 401 for this request: try to refresh the access token once, then retry.
      if (!original.__craRetried) {
        try {
          if (!refreshPromise) {
            refreshPromise = refreshAccessToken().finally(() => {
              refreshPromise = null;
            });
          }
          const newToken = await refreshPromise;
          if (newToken) {
            original.__craRetried = true;
            original.headers = {
              ...(original.headers || {}),
              Authorization: `Bearer ${newToken}`,
            };
            return api(original);
          }
        } catch (refreshError) {
          // fall through to logout
        }
      }
      // No refresh token, refresh failed, or the retry still 401'd → the session is truly over.
      console.warn("[CRA] Session expired and refresh failed — signing out");
      forceLogout();
    }

    if (import.meta.env.DEV) {
      console.error(
        "[CRA] API error",
        error.response?.status,
        error.response?.data || error.message
      );
    }
    publishBackendError({
      source: "api",
      message: extractApiError(error),
      status: error.response?.status,
      method: error.config?.method?.toUpperCase(),
      url: error.config?.url,
      raw: error.response?.data || error.message,
    });
    return Promise.reject(error);
  }
);

export default api;
