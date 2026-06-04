const ACCESS_KEY = "cra_access_token";
const REFRESH_KEY = "cra_refresh_token";

export const tokenStorage = {
  getAccessToken() {
    return localStorage.getItem(ACCESS_KEY);
  },
  getRefreshToken() {
    return localStorage.getItem(REFRESH_KEY);
  },
  setTokens({ access_token, refresh_token }) {
    localStorage.setItem(ACCESS_KEY, access_token);
    if (refresh_token) {
      localStorage.setItem(REFRESH_KEY, refresh_token);
    }
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
  hasAccessToken() {
    return Boolean(localStorage.getItem(ACCESS_KEY));
  },
};
