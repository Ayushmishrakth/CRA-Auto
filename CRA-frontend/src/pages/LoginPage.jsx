import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import LoadingSpinner from "../components/LoadingSpinner";

export default function LoginPage() {
  const {
    loginWithMicrosoft,
    loading,
    error,
    isAuthenticated,
    setError,
    clearAuthCaches,
  } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const handleLogin = async () => {
    setError(null);
    try {
      await loginWithMicrosoft();
      navigate(from, { replace: true });
    } catch {
      /* error in context */
    }
  };

  const handleClearCache = async () => {
    setError(null);
    await clearAuthCaches();
    setError("Auth cache cleared. Try Login with Microsoft again.");
  };

  if (loading && isAuthenticated) {
    return <LoadingSpinner label="Redirecting..." />;
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>CRA Platform</h1>
        <p className="subtitle">
          Multi-tenant Microsoft 365 sign-in (Entra ID + CRA JWT).
        </p>

        <button
          type="button"
          className="btn-microsoft"
          onClick={handleLogin}
          disabled={loading}
        >
          {loading ? "Signing in..." : "Login with Microsoft"}
        </button>

        <button
          type="button"
          className="btn-secondary"
          onClick={handleClearCache}
          disabled={loading}
        >
          Clear auth cache
        </button>

        {error && (
          <div className="error-box">
            <strong>Sign-in failed</strong>
            <p>{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
