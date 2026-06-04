import axios from "axios";
import { tokenStorage } from "../utils/tokenStorage";

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
    if (error.response?.status === 401 && !isPublicAuthPath(error.config?.url)) {
      console.warn("[CRA] 401 — clearing CRA tokens");
      tokenStorage.clear();
    }
    if (import.meta.env.DEV) {
      console.error(
        "[CRA] API error",
        error.response?.status,
        error.response?.data || error.message
      );
    }
    return Promise.reject(error);
  }
);

export default api;
