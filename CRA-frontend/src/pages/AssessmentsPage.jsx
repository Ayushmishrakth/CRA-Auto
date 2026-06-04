import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FileText, PlayCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useAssessments } from "../context/AssessmentContext";
import AssessmentProgress from "../components/assessment/AssessmentProgress";
import AssessmentStatusBadge from "../components/assessment/AssessmentStatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import { formatDateTime, numberOrZero } from "../utils/assessmentFormatters";
import { riskRating } from "../utils/executiveFormatters";

export default function AssessmentsPage() {
  const { user } = useAuth();
  const { assessments, loading, error, fetchTenantAssessments, startAssessment } = useAssessments();
  const [startBusy, setStartBusy] = useState(false);
  const navigate = useNavigate();
  const tenantId = user?.microsoft_tid;

  useEffect(() => {
    if (tenantId) fetchTenantAssessments(tenantId, { limit: 100 });
  }, [tenantId, fetchTenantAssessments]);

  const rows = useMemo(
    () =>
      assessments
        .filter((assessment) => !tenantId || assessment.tenant_id === tenantId)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
    [assessments, tenantId]
  );

  const handleStart = async () => {
    if (!tenantId) return;
    setStartBusy(true);
    try {
      const assessment = await startAssessment(tenantId);
      navigate(`/assessments/${assessment.id}`);
    } finally {
      setStartBusy(false);
    }
  };

  if (loading && !assessments.length) return <LoadingSpinner label="Loading assessments..." />;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Assessments</h1>
          <p>Copilot readiness history and current business risk posture.</p>
        </div>
        <button type="button" className="primary-action" onClick={handleStart} disabled={!tenantId || startBusy}>
          <PlayCircle size={16} />
          {startBusy ? "Starting..." : "Start Assessment"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="panel">
        <div className="executive-list">
          {rows.map((assessment) => {
            const score = Math.round(numberOrZero(assessment.overall_score));
            return (
              <article className="executive-row assessment-summary-row" key={assessment.id}>
                <div>
                  <h3>Copilot Readiness Assessment</h3>
                  <p>{formatDateTime(assessment.created_at)} · {riskRating(score)} risk</p>
                </div>
                <AssessmentStatusBadge status={assessment.status} />
                <strong>{score}%</strong>
                <span>{assessment.critical_findings ?? 0} critical · {assessment.high_findings ?? 0} high</span>
                <AssessmentProgress value={assessment.progress_pct} compact />
                <div className="row-actions">
                  <Link className="btn-secondary inline" to={`/assessments/${assessment.id}`}>Results</Link>
                  <Link className="icon-button" to={`/assessments/${assessment.id}/report`} aria-label="Open report">
                    <FileText size={16} />
                  </Link>
                </div>
              </article>
            );
          })}
          {!rows.length && <p className="muted-text">No assessments have been run yet.</p>}
        </div>
      </section>
    </div>
  );
}
