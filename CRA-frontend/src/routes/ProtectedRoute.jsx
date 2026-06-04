import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { tokenStorage } from "../utils/tokenStorage";
import LoadingSpinner from "../components/LoadingSpinner";

/**
 * Protects CRA routes — requires CRA JWT (from backend), not only MSAL session.
 */
export default function ProtectedRoute({ children }) {
  const { error, isAuthenticated, loading, refreshUser, setError, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [hydrating, setHydrating] = useState(false);
  const [sessionTimedOut, setSessionTimedOut] = useState(false);

  const hasCraToken = tokenStorage.hasAccessToken();

  useEffect(() => {
    if (hasCraToken && !user && !loading) {
      setHydrating(true);
      setSessionTimedOut(false);
      refreshUser().finally(() => setHydrating(false));
    }
  }, [hasCraToken, user, loading, refreshUser]);

  useEffect(() => {
    if (!loading && !hydrating) {
      setSessionTimedOut(false);
      return undefined;
    }

    const timeout = window.setTimeout(() => {
      setSessionTimedOut(true);
      setError(
        "Session check is taking longer than expected. Your CRA token may be stale."
      );
    }, 10000);

    return () => window.clearTimeout(timeout);
  }, [hydrating, loading, setError]);

  const clearSessionAndLogin = () => {
    tokenStorage.clear();
    setError(null);
    navigate("/login", { replace: true, state: { from: location } });
  };

  if ((error && !isAuthenticated && !loading) || sessionTimedOut) {
    return (
      <div className="session-recovery">
        <div className="panel session-panel">
          <h1>Session check failed</h1>
          <p>{error || "CRA could not restore your session."}</p>
          <div className="modal-actions">
            <button
              type="button"
              className="btn-secondary inline"
              onClick={() => {
                setSessionTimedOut(false);
                refreshUser();
              }}
            >
              Retry
            </button>
            <button type="button" className="primary-action" onClick={clearSessionAndLogin}>
              Sign in again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (loading || hydrating) {
    return <LoadingSpinner label="Checking session..." />;
  }

  if (!hasCraToken || !isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}
