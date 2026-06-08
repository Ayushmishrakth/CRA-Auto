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
  timeout: 30000,
});

const isPublicAuthPath = (url = "") =>
  url.includes("/auth/login") || url.includes("/auth/refresh");
const AUTH_EXPIRED_EVENT = "cra:auth-expired";
const LOGIN_IN_PROGRESS_FLAG = "__CRA_LOGIN_IN_PROGRESS__";

function isLoginInProgress() {
  return Boolean(typeof window !== "undefined" && window[LOGIN_IN_PROGRESS_FLAG]);
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
  (error) => {
    if (error.response?.status === 401 && !isPublicAuthPath(error.config?.url) && !isLoginInProgress()) {
      console.warn("[CRA] 401 — clearing CRA tokens");
      tokenStorage.clear();
      window.dispatchEvent(
        new CustomEvent(AUTH_EXPIRED_EVENT, {
          detail: { message: "Your sign-in session has expired. Please sign in again." },
        })
      );
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
