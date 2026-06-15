import api from "./axiosClient";
import {
  normalizeAssessment,
  normalizeRuntimeEvent,
  normalizeFinding,
  normalizeRecommendation,
  unwrapApiData,
} from "../utils/assessmentFormatters";

export async function startAssessment(tenantId) {
  const response = await api.post("/assessments/start", { tenant_id: tenantId });
  return normalizeAssessment(unwrapApiData(response));
}

export async function getAssessment(assessmentId) {
  const response = await api.get(`/assessments/${assessmentId}`);
  return normalizeAssessment(unwrapApiData(response));
}

export async function getAssessmentFindings(assessmentId, params = {}) {
  const response = await api.get(`/assessments/${assessmentId}/findings`, { params });
  const data = unwrapApiData(response);
  return Array.isArray(data) ? data.map(normalizeFinding) : [];
}

export async function getAssessmentRecommendations(assessmentId) {
  const response = await api.get(`/assessments/${assessmentId}/recommendations`);
  const data = unwrapApiData(response);
  const recommendations = data?.recommendations ?? data ?? [];
  return Array.isArray(recommendations)
    ? recommendations.map(normalizeRecommendation)
    : [];
}

export async function getAssessmentScore(assessmentId) {
  const response = await api.get(`/assessments/${assessmentId}/score`);
  return unwrapApiData(response);
}

export async function getAssessmentReadiness(assessmentId) {
  const response = await api.get(`/assessments/${assessmentId}/readiness`);
  return unwrapApiData(response);
}

export async function getAssessmentEvents(assessmentId, params = {}) {
  const response = await api.get(`/assessments/${assessmentId}/events`, { params });
  const data = unwrapApiData(response);
  return Array.isArray(data) ? data.map(normalizeRuntimeEvent) : [];
}

export async function getAssessmentJob(assessmentId) {
  const response = await api.get(`/assessments/${assessmentId}/job`);
  return unwrapApiData(response);
}

export async function getAssessmentEvidence(assessmentId) {
  const response = await api.get(`/assessments/${assessmentId}/evidence`);
  return unwrapApiData(response);
}

export async function getAssessmentFailures(assessmentId) {
  const response = await api.get(`/assessment-failures/${assessmentId}`);
  return unwrapApiData(response);
}

export async function getTenantAssessments(tenantId, params = {}) {
  const response = await api.get(`/tenants/${tenantId}/assessments`, { params });
  const data = unwrapApiData(response);
  return Array.isArray(data) ? data.map(normalizeAssessment) : [];
}

export async function generateAssessmentReport(assessmentId, reportType = "docx") {
  const response = await api.post(`/assessments/${assessmentId}/generate-report`, undefined, {
    params: { report_type: reportType },
    timeout: 180000,
  });
  return unwrapApiData(response);
}

export async function getAssessmentReport(assessmentId) {
  const response = await api.get(`/assessments/${assessmentId}/report`);
  return unwrapApiData(response);
}

export async function getAssessmentReportDebug(assessmentId) {
  const response = await api.get(`/report-debug/${assessmentId}`);
  return unwrapApiData(response);
}

export async function getAssessmentResults(assessmentId) {
  const response = await api.get(`/assessments/${assessmentId}/results`);
  return unwrapApiData(response);
}

export async function getDashboardStats() {
  const response = await api.get("/dashboard/stats");
  return unwrapApiData(response);
}

export async function listAssessments(params = {}) {
  const response = await api.get("/assessments", { params });
  return unwrapApiData(response);
}

export async function deleteAssessment(assessmentId) {
  const response = await api.delete(`/assessments/${assessmentId}`);
  return unwrapApiData(response);
}

export function getAssessmentReportDownloadUrl(assessmentId, reportType = "pdf") {
  const baseURL = api.defaults.baseURL?.replace(/\/+$/, "") || "";
  return `${baseURL}/assessments/${assessmentId}/report/download?report_type=${reportType}`;
}

export async function downloadAssessmentReport(assessmentId, reportType = "docx") {
  const response = await api.get(`/assessments/${assessmentId}/report/download`, {
    params: { report_type: reportType },
    responseType: "arraybuffer",
  });
  const disposition = response.headers?.["content-disposition"] || "";
  const match = disposition.match(/filename="?([^";\n]+)"?/i);
  const filename = match?.[1] ?? `copilot-readiness-assessment.${reportType}`;
  const type =
    reportType === "pdf"
      ? "application/pdf"
      : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  const data = new Blob([response.data], { type });
  return { data, filename };
}

export async function customizeAssessmentReport(assessmentId, { logoFile, address, companyName, outputFormat = "docx" }) {
  const formData = new FormData();
  if (logoFile) {
    formData.append("logo", logoFile);
  }
  if (address) {
    formData.append("address", address);
  }
  if (companyName) {
    formData.append("company_name", companyName);
  }
  formData.append("output_format", outputFormat);

  try {
    // ✅ FIX: Do NOT manually set Content-Type header
    // When Axios detects FormData, it automatically sets:
    // "Content-Type": "multipart/form-data; boundary=..."
    // If you manually set the header, Axios won't add the boundary marker,
    // which breaks multipart parsing on the backend.

    const response = await api.post(
      `/reports/assessments/${assessmentId}/customize`,
      formData
      // ✅ CORRECT: No headers object - let Axios handle it
    );
    return unwrapApiData(response);
  } catch (error) {
    console.error("[CUSTOMIZE API] customizeAssessmentReport failed", {
      assessmentId,
      hasLogo: !!logoFile,
      errorMessage: error.message,
      errorStatus: error.response?.status,
      errorData: error.response?.data,
    });
    throw error;
  }
}
