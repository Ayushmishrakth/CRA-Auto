import api from "./axiosClient";
import { unwrapApiData } from "../utils/assessmentFormatters";

export async function getRegistryParameters() {
  const response = await api.get("/registry/parameters");
  const data = unwrapApiData(response);
  return Array.isArray(data) ? data : [];
}
