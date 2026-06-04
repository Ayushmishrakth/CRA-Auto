import { FileText, Gauge, Settings, ShieldCheck } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function MainLayout() {
  const { user, logout, loading } = useAuth();

  return (
    <div className="layout">
      <header className="header">
        <div className="brand">
          <Link to="/dashboard">CRA Platform</Link>
          <span className="badge">Copilot Readiness</span>
        </div>
        <nav className="main-nav">
          <NavLink to="/dashboard"><Gauge size={16} />Dashboard</NavLink>
          <NavLink to="/assessments"><ShieldCheck size={16} />Assessments</NavLink>
          <NavLink to="/reports"><FileText size={16} />Reports</NavLink>
          <NavLink to="/settings"><Settings size={16} />Settings</NavLink>
        </nav>
        {user && (
          <div className="header-actions">
            <span className="user-email">{user.display_name || user.email}</span>
            <button type="button" onClick={logout} disabled={loading}>
              Logout
            </button>
          </div>
        )}
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
