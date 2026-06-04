import api from "./axiosClient";

export async function resetTenantAssessmentData(tenantId) {
  const response = await api.post(`/admin/reset-tenant/${tenantId}`);
  return response.data?.data ?? response.data;
}
