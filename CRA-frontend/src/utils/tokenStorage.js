const ACCESS_KEY = "cra_access_token";
const REFRESH_KEY = "cra_refresh_token";

function storage() {
  if (typeof window === "undefined" || !window.localStorage) return null;
  return window.localStorage;
}

export const tokenStorage = {
  getAccessToken() {
    return storage()?.getItem(ACCESS_KEY) ?? null;
  },
  getRefreshToken() {
    return storage()?.getItem(REFRESH_KEY) ?? null;
  },
  setTokens({ access_token, refresh_token }) {
    const store = storage();
    if (!store) return;
    store.setItem(ACCESS_KEY, access_token);
    if (refresh_token) {
      store.setItem(REFRESH_KEY, refresh_token);
    }
  },
  clear() {
    const store = storage();
    if (!store) return;
    store.removeItem(ACCESS_KEY);
    store.removeItem(REFRESH_KEY);
  },
  hasAccessToken() {
    return Boolean(storage()?.getItem(ACCESS_KEY));
  },
};
