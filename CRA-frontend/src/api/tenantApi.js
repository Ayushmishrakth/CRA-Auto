import api from "./axiosClient";
import { unwrapApiData } from "../utils/assessmentFormatters";

export async function listTenants() {
  const response = await api.get("/tenants");
  return unwrapApiData(response);
}

export async function deployTenantAccess({ tenantId, graphAccessToken, redirectUri }) {
  const response = await api.post("/tenants/deployment/start", {
    tenant_id: tenantId,
    graph_access_token: graphAccessToken,
    redirect_uri: redirectUri,
  });
  return unwrapApiData(response);
}

export async function validateTenantConsent({ tenantId, graphAccessToken }) {
  const response = await api.post("/tenants/deployment/validate-consent", {
    tenant_id: tenantId,
    graph_access_token: graphAccessToken,
  });
  return unwrapApiData(response);
}
