import api from "./axiosClient";

/**
 * Generate a customized report with logo and company details
 * Supports PDF, DOCX, or both (as ZIP)
 */
export async function generateCustomizedReport(assessmentId, {
  logoFile,
  companyName = "",
  companyAddress = "",
  format = "pdf",
}) {
  const formData = new FormData();

  if (logoFile) {
    formData.append("logo", logoFile);
  }

  formData.append("company_name", companyName);
  formData.append("company_address", companyAddress);
  formData.append("report_format", format);

  try {
    // ✅ FIX: Do NOT manually set Content-Type header
    // When Axios detects FormData, it automatically sets:
    // "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundary..."
    // If you manually set the header, Axios won't add the boundary marker,
    // which breaks multipart parsing on the backend.

    const response = await api.post(
      `/reports/assessments/${assessmentId}/generate`,
      formData,
      {
        // ✅ CORRECT: Let Axios handle Content-Type automatically
        responseType: "blob",
        timeout: 300000, // 5 minutes for report generation
      }
    );

    // Extract filename from Content-Disposition header
    const disposition = response.headers?.["content-disposition"] || "";
    const match = disposition.match(/filename="?([^";\n]+)"?/i);

    let filename;
    const timestamp = new Date().toISOString().slice(0, 10);
    const safeName = (companyName || "assessment").replace(/\s+/g, "_").replace(/[^a-zA-Z0-9_-]/g, "");

    if (format === "both") {
      filename = match?.[1] ?? `CRA_Report_${safeName}_${timestamp}.zip`;
    } else if (format === "pdf") {
      filename = match?.[1] ?? `CRA_Report_${safeName}_${timestamp}.pdf`;
    } else {
      filename = match?.[1] ?? `CRA_Report_${safeName}_${timestamp}.docx`;
    }

    return {
      data: new Blob([response.data], { type: response.headers["content-type"] || "application/octet-stream" }),
      filename,
    };
  } catch (error) {
    console.error("[REPORT API] generateCustomizedReport failed", {
      assessmentId,
      format,
      companyName,
      hasLogo: !!logoFile,
      errorMessage: error.message,
      errorStatus: error.response?.status,
      errorData: error.response?.data,
    });

    // Extract meaningful error message from backend
    const errorDetail = error.response?.data?.detail || error.response?.data?.message || error.message;
    throw new Error(errorDetail || "Failed to generate customized report");
  }
}

/**
 * Download a generated report file
 */
export async function downloadReport(data, filename) {
  if (typeof window === "undefined" || typeof document === "undefined") return;

  const url = URL.createObjectURL(data);
  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}
