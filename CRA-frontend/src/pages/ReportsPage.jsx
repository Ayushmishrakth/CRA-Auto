import { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { Download, FileText } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useAssessments } from "../context/AssessmentContext";
import AssessmentStatusBadge from "../components/assessment/AssessmentStatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import { formatDateTime, numberOrZero } from "../utils/assessmentFormatters";
import { riskRating } from "../utils/executiveFormatters";

export default function ReportsPage() {
  const { user } = useAuth();
  const { assessments, loading, error, fetchTenantAssessments } = useAssessments();

  useEffect(() => {
    if (user?.microsoft_tid) fetchTenantAssessments(user.microsoft_tid, { limit: 100 });
  }, [user?.microsoft_tid, fetchTenantAssessments]);

  const rows = useMemo(
    () =>
      assessments
        .filter((assessment) => assessment.tenant_id === user?.microsoft_tid)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
    [assessments, user?.microsoft_tid]
  );

  if (loading && !rows.length) return <LoadingSpinner label="Loading reports..." />;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Reports</h1>
          <p>Executive Copilot readiness summaries and downloadable board-ready artifacts.</p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="panel">
        <div className="executive-list">
          {rows.map((assessment) => {
            const score = Math.round(numberOrZero(assessment.overall_score));
            return (
              <article className="executive-row" key={assessment.id}>
                <div className="row-icon"><FileText size={18} /></div>
                <div>
                  <h3>Copilot Readiness Report</h3>
                  <p>{formatDateTime(assessment.created_at)} · Risk rating: {riskRating(score)}</p>
                </div>
                <AssessmentStatusBadge status={assessment.status} />
                <strong>{score}%</strong>
                <Link className="btn-secondary inline" to={`/assessments/${assessment.id}/report`}>
                  <Download size={16} />
                  Open
                </Link>
              </article>
            );
          })}
          {!rows.length && <p className="muted-text">No assessment reports are available yet.</p>}
        </div>
      </section>
    </div>
  );
}
