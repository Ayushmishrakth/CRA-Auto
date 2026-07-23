import { useState, useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, ClipboardList, FileText, Settings,
  Bell, Menu, X, LogOut,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { listTenants } from "../../api/tenantApi";
import Logo from "../common/Logo";

const ROLE_LABELS = { admin: "Administrator", user: "User" };

function formatStatus(raw) {
  if (!raw) return null;
  if (/active|connected/i.test(raw)) return { label: "Connected", ok: true };
  if (/pending/i.test(raw))          return { label: "Pending", ok: false };
  if (/failed/i.test(raw))           return { label: "Not connected", ok: false };
  return { label: raw.replace(/_/g, " ").toLowerCase(), ok: false };
}

const NAV_LINKS = [
  { to: "/dashboard",   icon: LayoutDashboard, label: "Dashboard" },
  { to: "/assessments", icon: ClipboardList,    label: "Assessments" },
  { to: "/reports",     icon: FileText,         label: "Reports" },
  { to: "/settings",    icon: Settings,         label: "Settings" },
];

const PAGE_TITLES = {
  "/dashboard":   "Dashboard",
  "/assessments": "Assessments",
  "/customers":   "Customers",
  "/reports":     "Reports",
  "/settings":    "Settings",
  "/parameters":  "Parameters",
};

function deriveTitle(pathname) {
  if (PAGE_TITLES[pathname]) return PAGE_TITLES[pathname];
  if (pathname === "/assessments/new") return "New Assessment";
  if (pathname.endsWith("/progress")) return "Assessment Progress";
  if (pathname.endsWith("/results"))  return "Assessment Results";
  if (pathname.endsWith("/evidence")) return "Evidence";
  if (pathname.endsWith("/report"))   return "Report";
  if (pathname.startsWith("/assessments/")) return "Assessment Details";
  return "Dashboard";
}

function initials(name) {
  if (!name) return "U";
  return name.split(" ").filter(Boolean).map((w) => w[0].toUpperCase()).join("").slice(0, 2);
}

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, loading } = useAuth();

  const [tenantInfo, setTenantInfo] = useState(null);

  const pageTitle = deriveTitle(location.pathname);
  const displayName = user?.display_name || user?.name || user?.email || "User";
  const email = user?.email || "";
  const tenantId = user?.microsoft_tid || user?.tenant_id || "—";

  // Real tenant name/status has a proper display name only if it isn't just the GUID fallback.
  const hasRealName = tenantInfo?.tenant_name && tenantInfo.tenant_name !== tenantId;
  const orgName = hasRealName ? tenantInfo.tenant_name : (email.split("@")[1] || "—");
  const roleLabel = ROLE_LABELS[(user?.role || "").toLowerCase()] || user?.role || "—";
  const status = formatStatus(tenantInfo?.status || tenantInfo?.consent_status);

  // Close sidebar on route change on mobile
  useEffect(() => setSidebarOpen(false), [location.pathname]);

  // Load the signed-in user's tenant details for the account card (existing /tenants endpoint).
  useEffect(() => {
    if (!user?.microsoft_tid) return;
    let cancelled = false;
    listTenants()
      .then((tenants) => {
        if (cancelled) return;
        const list = Array.isArray(tenants) ? tenants : [];
        setTenantInfo(list.find((t) => t.tenant_id === user.microsoft_tid) || null);
      })
      .catch(() => { if (!cancelled) setTenantInfo(null); });
    return () => { cancelled = true; };
  }, [user?.microsoft_tid]);

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA] font-[var(--font)]">
      {/* ── Mobile backdrop ─────────────────── */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar ─────────────────────────── */}
      <aside
        className={[
          "shell-sidebar",
          sidebarOpen ? "open" : "",
        ].join(" ")}
      >
        {/* Logo row */}
        <div className="flex items-center gap-3 px-5 border-b border-[#E5E7EB] flex-shrink-0"
          style={{ height: "var(--topbar-height)" }}>
          <Logo size="sidebar" className="flex-shrink-0" />
          <button
            className="ml-auto lg:hidden p-1 text-[#9CA3AF] hover:text-[#374151]"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-3 px-3 overflow-y-auto">
          <p className="px-3 mb-1 text-[10px] font-semibold text-[#9CA3AF] uppercase tracking-widest">
            Menu
          </p>
          {NAV_LINKS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium mb-0.5 transition-colors",
                  isActive ? "nav-link-active" : "nav-link-inactive",
                ].join(" ")
              }
            >
              <Icon size={18} className="flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-[#E5E7EB] p-4 flex-shrink-0">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 rounded-full bg-[#0078D4] flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-bold text-white">{initials(displayName)}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-[#111827] truncate leading-tight">{displayName}</p>
              <p className="text-xs text-[#6B7280] truncate leading-tight">{email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            disabled={loading}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[#6B7280] hover:text-[#111827] hover:bg-[#F3F4F6] rounded-md transition-colors disabled:opacity-50"
          >
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Top bar ─────────────────────────── */}
      <header className="shell-topbar">
        {/* Hamburger (mobile) */}
        <button
          className="lg:hidden p-1.5 text-[#6B7280] hover:text-[#111827] hover:bg-[#F3F4F6] rounded-md"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open sidebar"
        >
          <Menu size={20} />
        </button>

        {/* Desktop sidebar offset spacer */}
        <div className="hidden lg:block flex-shrink-0" style={{ width: "var(--sidebar-width)" }} />

        <h1 className="text-base font-semibold text-[#111827] flex-1">{pageTitle}</h1>

        <div className="ml-auto flex items-center gap-2">
          <button
            className="p-2 text-[#9CA3AF] hover:text-[#374151] hover:bg-[#F3F4F6] rounded-md transition-colors relative"
            aria-label="Notifications"
          >
            <Bell size={20} />
          </button>
          <div
            className="relative"
            onMouseEnter={() => setProfileOpen(true)}
            onMouseLeave={() => setProfileOpen(false)}
          >
            <div
              className="w-8 h-8 rounded-full bg-[#0078D4] flex items-center justify-center cursor-default focus:outline-none focus:ring-2 focus:ring-[#0078D4]/40"
              tabIndex={0}
              role="img"
              aria-label={`Signed in as ${displayName}`}
              onFocus={() => setProfileOpen(true)}
              onBlur={() => setProfileOpen(false)}
            >
              <span className="text-xs font-bold text-white">{initials(displayName)}</span>
            </div>

            {profileOpen && (
              <div
                role="tooltip"
                className="absolute right-0 top-full mt-2 w-64 bg-white border border-[#E5E7EB] rounded-lg shadow-lg z-50 overflow-hidden"
              >
                <div className="flex items-center gap-3 px-4 py-3 border-b border-[#E5E7EB]">
                  <div className="w-9 h-9 rounded-full bg-[#0078D4] flex items-center justify-center flex-shrink-0">
                    <span className="text-xs font-bold text-white">{initials(displayName)}</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[#111827] truncate leading-tight">{displayName}</p>
                    <p className="text-xs text-[#6B7280] truncate leading-tight">{email}</p>
                  </div>
                </div>
                <dl className="px-4 py-3 space-y-2.5 m-0">
                  <div className="flex items-start justify-between gap-3">
                    <dt className="text-xs text-[#6B7280] flex-shrink-0">Organization</dt>
                    <dd className="text-xs font-medium text-[#111827] text-right m-0 break-words">{orgName}</dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="text-xs text-[#6B7280] flex-shrink-0">Role</dt>
                    <dd className="text-xs font-medium text-[#111827] text-right m-0">{roleLabel}</dd>
                  </div>
                  {status && (
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-xs text-[#6B7280] flex-shrink-0">Status</dt>
                      <dd className="text-xs font-medium text-right m-0 inline-flex items-center gap-1.5">
                        <span className={`w-1.5 h-1.5 rounded-full ${status.ok ? "bg-[#16A34A]" : "bg-[#9CA3AF]"}`} />
                        <span className={status.ok ? "text-[#111827]" : "text-[#6B7280]"}>{status.label}</span>
                      </dd>
                    </div>
                  )}
                  <div className="pt-0.5">
                    <dt className="text-xs text-[#6B7280] mb-1">Tenant ID</dt>
                    <dd className="text-[11px] font-mono text-[#374151] m-0 break-all leading-snug">{tenantId}</dd>
                  </div>
                </dl>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── Main content ─────────────────────── */}
      <main className="shell-main">
        <div className="shell-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
