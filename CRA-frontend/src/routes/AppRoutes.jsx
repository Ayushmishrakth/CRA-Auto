import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import AppShell from "../components/layout/AppShell";

// Pages
import LoginPage           from "../pages/LoginPage";
import DashboardPage       from "../pages/DashboardPage";
import AssessmentsPage     from "../pages/AssessmentsPage";
import NewAssessmentPage   from "../pages/NewAssessmentPage";
import ProgressPage        from "../pages/ProgressPage";
import ResultsPage         from "../pages/ResultsPage";
import ReportsPage         from "../pages/ReportsPage";
import SettingsPage        from "../pages/SettingsPage";

// Legacy pages (still functional, now wrapped in AppShell)
import AssessmentDetailPage  from "../pages/AssessmentDetailPage";
import AssessmentEvidencePage from "../pages/AssessmentEvidencePage";
import AssessmentReportPage  from "../pages/AssessmentReportPage";
import TenantConnectionPage  from "../pages/TenantConnectionPage";
import ParametersPage        from "../pages/ParametersPage";

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected — all use AppShell */}
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard"    element={<DashboardPage />} />
          <Route path="/assessments"  element={<AssessmentsPage />} />
          {/* /new must come before /:assessmentId so it is not captured as an id */}
          <Route path="/assessments/new"                          element={<NewAssessmentPage />} />
          <Route path="/assessments/:assessmentId/progress"       element={<ProgressPage />} />
          <Route path="/assessments/:assessmentId/results"        element={<ResultsPage />} />
          {/* Legacy detail routes kept as-is */}
          <Route path="/assessments/:assessmentId"                element={<AssessmentDetailPage />} />
          <Route path="/assessments/:assessmentId/evidence"       element={<AssessmentEvidencePage />} />
          <Route path="/assessments/:assessmentId/report"         element={<AssessmentReportPage />} />
          <Route path="/reports"      element={<ReportsPage />} />
          <Route path="/settings"     element={<SettingsPage />} />
          <Route path="/tenant"       element={<TenantConnectionPage />} />
          <Route path="/tenant/deployment-success" element={<TenantConnectionPage />} />
          <Route path="/parameters"   element={<ParametersPage />} />
          {/* Customers placeholder (future page) */}
          <Route path="/customers"    element={<Navigate to="/dashboard" replace />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
