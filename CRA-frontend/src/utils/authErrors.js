/**
 * Normalize API and network errors for display in the UI.
 */
export function formatApiError(error) {
  if (!error) {
    return "Request failed";
  }

  if (!error.response) {
    if (error.code === "ERR_NETWORK") {
      return (
        "Cannot reach CRA backend at " +
        (import.meta.env.VITE_API_BASE_URL || "API") +
        ". Start FastAPI: uvicorn app.main:app --reload"
      );
    }
    return error.message || "Network error";
  }

  const detail = error.response.data?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  return error.response.statusText || `Error ${error.response.status}`;
}
