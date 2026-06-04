import {
  fetchCurrentUser,
  loginWithMicrosoftIdToken,
  logoutFromBackend,
} from "../api/authApi";
import { tokenStorage } from "../utils/tokenStorage";

export async function exchangeMicrosoftTokenForCraJwt(idToken) {
  const tokens = await loginWithMicrosoftIdToken(idToken);
  tokenStorage.setTokens(tokens);
  const user = await fetchCurrentUser();
  return { tokens, user };
}

export async function loadCurrentUser() {
  if (!tokenStorage.hasAccessToken()) {
    return null;
  }
  return fetchCurrentUser();
}

export async function logoutCraSession(msalLogout) {
  const refreshToken = tokenStorage.getRefreshToken();
  try {
    if (tokenStorage.getAccessToken()) {
      await logoutFromBackend(refreshToken);
    }
  } finally {
    tokenStorage.clear();
    if (msalLogout) {
      await msalLogout();
    }
  }
}
