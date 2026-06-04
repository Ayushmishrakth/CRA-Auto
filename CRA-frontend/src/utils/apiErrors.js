export function extractApiError(error, fallback = "Request failed") {
  const data = error?.response?.data;
  const message =
    data?.error?.message ||
    data?.detail ||
    data?.message ||
    error?.message ||
    fallback;

  return typeof message === "string" && message.trim() ? message : fallback;
}

export const getApiErrorMessage = extractApiError;
