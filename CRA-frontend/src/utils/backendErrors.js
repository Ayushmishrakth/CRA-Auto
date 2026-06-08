export const BACKEND_ERROR_EVENT = "cra:backend-error";

function safeJson(value) {
  if (!value) return null;
  try {
    return JSON.parse(JSON.stringify(value));
  } catch {
    return String(value);
  }
}

export function publishBackendError(detail = {}) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(BACKEND_ERROR_EVENT, {
      detail: {
        source: detail.source || "backend",
        message: detail.message || "Backend error",
        status: detail.status,
        method: detail.method,
        url: detail.url,
        eventType: detail.eventType,
        script: detail.script,
        parameterKey: detail.parameterKey,
        parameterName: detail.parameterName,
        collector: detail.collector,
        exceptionType: detail.exceptionType,
        raw: safeJson(detail.raw),
        timestamp: new Date().toISOString(),
      },
    })
  );
}
