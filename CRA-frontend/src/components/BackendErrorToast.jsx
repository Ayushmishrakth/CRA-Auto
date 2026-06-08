import { AlertCircle, ChevronDown, ChevronUp, Clipboard, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { BACKEND_ERROR_EVENT } from "../utils/backendErrors";

const MAX_ERRORS = 8;

function readableParameter(error) {
  const raw = error.parameterName || error.parameterKey || error.raw?.payload?.parameter_key;
  if (!raw) return "Backend error";
  return String(raw).replace(/^powershell\./, "").replace(/^graph\./, "").replaceAll("_", " ");
}

function normalizeError(detail = {}) {
  const rawPayload = detail.raw?.payload ?? {};
  const parameterKey = detail.parameterKey || rawPayload.parameter_key;
  const collector = detail.collector || rawPayload.collector;
  const exceptionType = detail.exceptionType || rawPayload.exception_type;
  const message = detail.message || rawPayload.error || "Backend request failed";
  const source = detail.source || "backend";
  const status = detail.status;
  const method = detail.method;
  const url = detail.url;
  const eventType = detail.eventType || detail.raw?.event || detail.raw?.type;
  const groupKey = [
    source,
    status,
    method,
    url,
    eventType,
    parameterKey,
    collector,
    exceptionType,
    message,
  ].filter(Boolean).join("|");

  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    groupKey,
    source,
    message,
    status,
    method,
    url,
    eventType,
    script: detail.script || rawPayload.script || rawPayload.script_path,
    parameterKey,
    parameterName: detail.parameterName || rawPayload.parameter_name,
    collector,
    exceptionType,
    raw: detail.raw,
    timestamp: detail.timestamp || new Date().toISOString(),
    count: 1,
  };
}

export default function BackendErrorToast() {
  const [errors, setErrors] = useState([]);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    const handleBackendError = (event) => {
      const nextError = normalizeError(event.detail);
      setErrors((current) => {
        const existing = current.find((item) => item.groupKey === nextError.groupKey);
        if (!existing) return [nextError, ...current].slice(0, MAX_ERRORS);
        return [
          { ...existing, ...nextError, id: existing.id, count: existing.count + 1 },
          ...current.filter((item) => item.groupKey !== nextError.groupKey),
        ].slice(0, MAX_ERRORS);
      });
      setExpandedId(nextError.id);
    };

    window.addEventListener(BACKEND_ERROR_EVENT, handleBackendError);
    return () => window.removeEventListener(BACKEND_ERROR_EVENT, handleBackendError);
  }, []);

  if (!errors.length) return null;

  const latest = errors[0];
  const totalCount = errors.reduce((sum, item) => sum + item.count, 0);
  const title = errors.length === 1 ? "Backend error" : `Backend errors (${totalCount})`;
  const copyError = (error) => {
    const text = JSON.stringify(
      {
        parameter: readableParameter(error),
        collector: error.collector,
        exception: error.exceptionType,
        message: error.message,
        eventType: error.eventType,
        status: error.status,
        method: error.method,
        url: error.url,
        timestamp: error.timestamp,
        raw: error.raw,
      },
      null,
      2
    );
    navigator.clipboard?.writeText(text);
  };

  return (
    <aside className="backend-error-panel" role="alert" aria-live="assertive">
      <div className="backend-error-panel-header">
        <div className="backend-error-icon" aria-hidden="true">
          <AlertCircle size={20} />
        </div>
        <div>
          <strong>{title}</strong>
          <span>{latest.source}</span>
        </div>
        <button
          className="backend-error-close"
          type="button"
          aria-label="Clear all backend errors"
          onClick={() => setErrors([])}
        >
          <Trash2 size={16} />
        </button>
      </div>
      <div className="backend-error-list">
        {errors.map((error) => {
          const requestLabel = [error.method, error.url].filter(Boolean).join(" ");
          const isExpanded = expandedId === error.id;
          return (
            <article className="backend-error-item" key={error.id}>
              <div className="backend-error-title">
                <strong>{readableParameter(error)}</strong>
                <div className="backend-error-actions">
                  {error.count > 1 ? <span>x{error.count}</span> : null}
                  {error.status ? <span>{error.status}</span> : null}
                  <button
                    type="button"
                    className="backend-error-icon-button"
                    aria-label="Copy backend error"
                    onClick={() => copyError(error)}
                  >
                    <Clipboard size={14} />
                  </button>
                  <button
                    type="button"
                    className="backend-error-icon-button"
                    aria-label={isExpanded ? "Hide backend error details" : "Show backend error details"}
                    onClick={() => setExpandedId(isExpanded ? null : error.id)}
                  >
                    {isExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                  </button>
                  <button
                    type="button"
                    className="backend-error-icon-button"
                    aria-label="Dismiss backend error"
                    onClick={() => {
                      setErrors((current) => current.filter((item) => item.id !== error.id));
                    }}
                  >
                    <X size={15} />
                  </button>
                </div>
              </div>
              <p className="backend-error-message">{error.message}</p>
              <div className="backend-error-meta">
                <span>{new Date(error.timestamp).toLocaleTimeString()}</span>
                <span>{error.source}</span>
                {error.eventType ? <span>{error.eventType}</span> : null}
              </div>
              {error.collector ? <code>Collector: {error.collector}</code> : null}
              {error.exceptionType ? <code>Exception: {error.exceptionType}</code> : null}
              {requestLabel ? <code>{requestLabel}</code> : null}
              {error.script ? <code>{error.script}</code> : null}
              {isExpanded && error.raw ? (
                <pre>{JSON.stringify(error.raw, null, 2)}</pre>
              ) : null}
            </article>
          );
        })}
      </div>
    </aside>
  );
}
