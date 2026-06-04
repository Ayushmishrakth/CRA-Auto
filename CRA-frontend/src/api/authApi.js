import api from "./axiosClient";

/** Exchange Microsoft ID token for CRA internal JWT. */
export async function loginWithMicrosoftIdToken(idToken) {
  const { data } = await api.post("/auth/login", { id_token: idToken });
  return data;
}

export async function refreshCraTokens(refreshToken) {
  const { data } = await api.post("/auth/refresh", {
    refresh_token: refreshToken,
  });
  return data;
}

export async function logoutFromBackend(refreshToken) {
  const { data } = await api.post("/auth/logout", {
    refresh_token: refreshToken ?? undefined,
  });
  return data;
}

export async function fetchCurrentUser() {
  const { data } = await api.get("/auth/me");
  return data;
}
