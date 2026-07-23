import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import Logo from "../components/common/Logo";

const MS_ICON = (
  <svg width="20" height="20" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <rect x="1"  y="1"  width="9" height="9" fill="#F25022" />
    <rect x="11" y="1"  width="9" height="9" fill="#7FBA00" />
    <rect x="1"  y="11" width="9" height="9" fill="#00A4EF" />
    <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
  </svg>
);

const FEATURES = [
  "65 automated Microsoft 365 checks",
  "Instant executive PDF reports",
  "Identifies Copilot deployment blockers",
];

export default function LoginPage() {
  const navigate  = useNavigate();
  const location  = useLocation();
  const { isAuthenticated, loading, error, loginWithMicrosoft, setError } = useAuth();
  const [signingIn, setSigningIn] = useState(false);

  const from = location.state?.from?.pathname || "/dashboard";

  useEffect(() => {
    if (isAuthenticated && !loading) navigate(from, { replace: true });
  }, [isAuthenticated, loading, navigate, from]);

  const handleSignIn = async () => {
    if (signingIn) return;
    setSigningIn(true);
    setError(null);
    try {
      await loginWithMicrosoft();
      navigate(from, { replace: true });
    } catch {
      // error surfaced via AuthContext.error
    } finally {
      setSigningIn(false);
    }
  };

  if (loading && !signingIn) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={32} className="animate-spin text-[#0078D4]" />
          <p className="text-sm text-[#6B7280]">Checking session…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex" style={{ fontFamily: "var(--font)" }}>
      {/* ── Left blue panel ─── */}
      <div
        className="hidden md:flex flex-col justify-between p-10"
        style={{ width: "45%", background: "#0078D4" }}
      >
        <div className="inline-flex bg-white rounded-md px-2.5 py-1.5 self-start">
          <Logo size="corner" />
        </div>

        <div>
          <div className="inline-block bg-white rounded-2xl px-5 py-4 mb-6">
            <Logo size="hero" />
          </div>
          <h1 className="text-[28px] font-bold text-white leading-tight mb-3">
            Copilot Readiness<br />Assessment
          </h1>
          <p className="text-white/85 text-sm leading-relaxed mb-8 max-w-xs">
            Automate your Microsoft 365 readiness audit and generate executive
            reports in minutes.
          </p>
          <ul className="space-y-3">
            {FEATURES.map((f) => (
              <li key={f} className="flex items-center gap-3 text-white text-sm">
                <CheckCircle2 size={18} className="flex-shrink-0" />
                {f}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-white/60 text-xs">Trusted by Microsoft Partners</p>
      </div>

      {/* ── Right white panel ─── */}
      <div className="flex flex-col items-center justify-center flex-1 bg-white p-8">
        <div className="w-full" style={{ maxWidth: "400px" }}>
          {/* Mobile logo */}
          <div className="flex items-center mb-8 md:hidden">
            <Logo size="mobile" />
          </div>

          <p className="text-sm text-[#6B7280] mb-1">Welcome back</p>
          <h2 className="text-2xl font-bold text-[#111827] mb-8 mt-0">
            Sign in to your account
          </h2>

          {error && (
            <div className="flex items-start gap-3 p-3.5 rounded-lg border border-[#D13438] bg-[#FDE7E9] mb-5">
              <AlertCircle size={18} className="text-[#D13438] flex-shrink-0 mt-0.5" />
              <p className="text-sm text-[#D13438] leading-snug">{error}</p>
            </div>
          )}

          <button
            type="button"
            onClick={handleSignIn}
            disabled={signingIn}
            className="w-full flex items-center justify-center gap-3 h-11 px-4 rounded-lg border border-[#D1D5DB] bg-white text-sm font-semibold text-[#374151] hover:bg-[#F8F9FA] transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0078D4] focus-visible:ring-offset-2"
          >
            {signingIn ? (
              <>
                <Loader2 size={18} className="animate-spin text-[#0078D4]" />
                Signing in…
              </>
            ) : (
              <>
                {MS_ICON}
                Sign in with Microsoft
              </>
            )}
          </button>

          <p className="text-center text-xs text-[#9CA3AF] mt-5">
            By signing in, you agree to our{" "}
            <a href="#" className="underline hover:text-[#374151]">
              Terms of Service
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
