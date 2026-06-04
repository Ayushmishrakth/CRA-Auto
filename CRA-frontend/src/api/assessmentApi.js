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

export async function generateAssessmentReport(assessmentId) {
  const response = await api.post(`/assessments/${assessmentId}/generate-report`);
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

export function getAssessmentReportDownloadUrl(assessmentId, reportType = "pdf") {
  const baseURL = api.defaults.baseURL?.replace(/\/+$/, "") || "";
  return `${baseURL}/assessments/${assessmentId}/report/download?report_type=${reportType}`;
}

export async function downloadAssessmentReport(assessmentId, reportType = "pdf") {
  const response = await api.get(`/assessments/${assessmentId}/report/download`, {
    params: { report_type: reportType },
    responseType: "blob",
  });
  return response.data;
}
