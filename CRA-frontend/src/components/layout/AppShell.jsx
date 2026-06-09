import { useState, useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, ClipboardList, FileText, Settings,
  Bell, Menu, X, LogOut, ShieldCheck,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

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
  "/tenant":      "Tenant Setup",
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
  return "CRA Tool";
}

function initials(name) {
  if (!name) return "U";
  return name.split(" ").filter(Boolean).map((w) => w[0].toUpperCase()).join("").slice(0, 2);
}

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, loading } = useAuth();

  const pageTitle = deriveTitle(location.pathname);
  const displayName = user?.display_name || user?.name || user?.email || "User";
  const email = user?.email || "";

  // Close sidebar on route change on mobile
  useEffect(() => setSidebarOpen(false), [location.pathname]);

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
          <div className="w-8 h-8 rounded-lg bg-[#0078D4] flex items-center justify-center flex-shrink-0">
            <ShieldCheck size={18} className="text-white" />
          </div>
          <span className="text-base font-bold text-[#111827]">CRA Tool</span>
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
            className="w-8 h-8 rounded-full bg-[#0078D4] flex items-center justify-center cursor-default"
            title={displayName}
          >
            <span className="text-xs font-bold text-white">{initials(displayName)}</span>
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
