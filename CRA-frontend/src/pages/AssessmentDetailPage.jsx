import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, FileText, X } from "lucide-react";
import { getAssessmentEvidence } from "../api/assessmentApi";
import AssessmentProgress from "../components/assessment/AssessmentProgress";
import AssessmentStatusBadge from "../components/assessment/AssessmentStatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import { useAuth } from "../context/AuthContext";
import { useAssessments } from "../context/AssessmentContext";
import { extractApiError } from "../utils/apiErrors";
import { formatDateTime, formatDuration, numberOrZero } from "../utils/assessmentFormatters";
import { safeStringify } from "../utils/safeStringify";
import {
  businessDomain,
  businessName,
  coveragePercent,
  executiveStatus,
  expectedText,
  findingToExecutiveRow,
  foundText,
  riskRating,
  sortBusinessPriority,
  statusTone,
} from "../utils/executiveFormatters";

const SCORECARD_DOMAINS = ["Identity", "Exchange", "Teams", "SharePoint", "Purview", "OneDrive"];
const CONTROL_FILTERS = [
  { label: "All", value: "ALL" },
  { label: "Pass", value: "PASS" },
  { label: "Fail", value: "FAIL" },
  { label: "Collection Error", value: "COLLECTION_ERROR" },
  { label: "Needs License", value: "LICENSING_REQUIRED" },
  { label: "Manual", value: "MANUAL_VALIDATION" },
  { label: "Not Collected", value: "NOT_COLLECTED" },
];

function countStatus(rows, status) {
  return rows.filter((item) => item.status === status).length;
}

function domainScorecard(rows) {
  return SCORECARD_DOMAINS.map((domain) => {
    const items = rows.filter((item) => businessDomain(item) === domain);
    const pass = countStatus(items, "PASS");
    const fail = countStatus(items, "FAIL");
    const total = Math.max(1, items.length);
    const passPct = Math.round((pass / total) * 100);
    const failPct = Math.round((fail / total) * 100);
    return { domain, total: items.length, passPct, failPct, rating: riskRating(passPct) };
  });
}

function DetailDrawer({ item, onClose }) {
  if (!item) return null;
  const rawData = item.evidence ?? item.artifact_json ?? {};
  return (
    <aside className="evidence-drawer executive-drawer">
      <div className="panel-header">
        <div>
          <h2>{businessName(item)}</h2>
          <p>{businessDomain(item)} readiness control</p>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close details">
          <X size={16} />
        </button>
      </div>

      <section className="assessment-outcome-card">
        <div><span>Status</span><strong><span className={`status-pill tone-${statusTone(item.status)}`}>{executiveStatus(item.status)}</span></strong></div>
        <div><span>Severity</span><strong>{item.severity || "info"}</strong></div>
        <div><span>Found</span><strong>{foundText(item)}</strong></div>
        <div><span>Expected</span><strong>{expectedText(item)}</strong></div>
      </section>

      <dl className="profile-grid report-summary-list">
        <dt>Business Impact</dt>
        <dd>{item.recommendation?.impact || "This control helps reduce exposure before Microsoft 365 Copilot can reason over organizational data."}</dd>
        <dt>Actual Result</dt>
        <dd>{item.finding || foundText(item)}</dd>
        <dt>Microsoft Guidance</dt>
        <dd>{item.recommendation?.remediation_steps?.[0] || "Align the setting with Microsoft 365 Copilot readiness and security baseline expectations."}</dd>
        <dt>Recommendation</dt>
        <dd>{item.recommendation?.recommendation_text || "Review the control owner guidance and remediate the failed condition."}</dd>
      </dl>

      <details className="drawer-section" open>
        <summary>Evidence</summary>
        <p>{item.finding || foundText(item)}</p>
      </details>
      <details className="drawer-section">
        <summary>Raw Data</summary>
        <pre className="evidence-json">{safeStringify(rawData)}</pre>
      </details>
    </aside>
  );
}

export default function AssessmentDetailPage() {
  const { assessmentId } = useParams();
  const { user } = useAuth();
  const [evidencePayload, setEvidencePayload] = useState(null);
  const [evidenceError, setEvidenceError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [controlFilter, setControlFilter] = useState("ALL");
  const {
    activeAssessment,
    findings,
    recommendations,
    scores,
    progress,
    loading,
    error,
    fetchAssessment,
    subscribeAssessment,
  } = useAssessments();

  useEffect(() => {
    if (!assessmentId) return undefined;
    fetchAssessment(assessmentId);
    getAssessmentEvidence(assessmentId)
      .then((data) => {
        setEvidencePayload(data);
        setEvidenceError(null);
      })
      .catch((err) => {
        setEvidencePayload(null);
        setEvidenceError(extractApiError(err));
      });
    return subscribeAssessment(assessmentId);
  }, [assessmentId, fetchAssessment, subscribeAssessment]);

  if (loading && !activeAssessment) return <LoadingSpinner label="Loading assessment..." />;
  if (error && !activeAssessment) return <div className="error-banner">{error}</div>;

  const assessment = activeAssessment;
  if (!assessment) {
    return (
      <div className="page-stack">
        <div className="panel">
          <div className="panel-header">
            <div>
              <Link className="back-link" to="/assessments"><ArrowLeft size={16} />Assessments</Link>
              <h1>Assessment not available</h1>
              <p>CRA could not load this assessment. It may belong to another backend session or may have been removed.</p>
            </div>
          </div>
          {error && <div className="error-banner">{error}</div>}
        </div>
      </div>
    );
  }
  if (user?.microsoft_tid && assessment.tenant_id !== user.microsoft_tid) {
    return <div className="error-banner">This assessment belongs to tenant {assessment.tenant_id}, but you are signed in to tenant {user.microsoft_tid}.</div>;
  }

  const completedAt = assessment.status === "completed" ? assessment.updated_at : null;
  const overall = assessment.overall_score ?? scores?.overall_score ?? 0;
  const evidenceRows = evidencePayload?.parameters ?? [];
  const safeRecommendations = Array.isArray(recommendations) ? recommendations : [];
  const recommendationByKey = Object.fromEntries(
    safeRecommendations.map((item) => [item.parameter_key, item])
  );
  const safeFindings = Array.isArray(findings) ? findings : [];
  const findingRows = safeFindings.map((item) => findingToExecutiveRow(item, recommendationByKey[item.parameter_key]));
  const rows = evidenceRows.length ? evidenceRows : findingRows;
  const coverage = evidencePayload?.coverage ?? {};
  const sortedRows = sortBusinessPriority(rows);
  const visibleRows =
    controlFilter === "ALL"
      ? sortedRows
      : sortedRows.filter((item) => item.status === controlFilter);
  const scorecard = domainScorecard(rows);
  const passed = countStatus(rows, "PASS");
  const failed = countStatus(rows, "FAIL");
  const failedCollectors = countStatus(rows, "COLLECTION_ERROR") + countStatus(rows, "FAILED_COLLECTOR") + countStatus(rows, "FAILED");
  const fallbackCoverage = rows.length ? Math.round(((passed + failed) / rows.length) * 100) : 0;
  const visibleCoverage = coverage.coverage_percent ?? (coveragePercent(coverage) || fallbackCoverage);

  return (
    <div className="page-stack assessment-detail">
      <div className="assessment-hero executive-hero compact-hero">
        <div>
          <Link className="back-link" to="/assessments"><ArrowLeft size={16} />Assessments</Link>
          <h1>Assessment Results</h1>
          <div className="hero-meta">
            <AssessmentStatusBadge status={assessment.status} />
            <span>Started {formatDateTime(assessment.created_at)}</span>
            <span>Duration {formatDuration(assessment.created_at, completedAt)}</span>
            <span>Risk rating {riskRating(overall)}</span>
          </div>
        </div>
        <div className="hero-score"><span>Readiness Score</span><strong>{Math.round(numberOrZero(overall))}%</strong></div>
        <AssessmentProgress value={progress} />
      </div>

      {(error || evidenceError) && <div className="error-banner">{error || evidenceError}</div>}

      <section className="metric-grid dashboard-metrics">
        <article className="metric-card"><span>Passed Controls</span><strong>{passed}</strong></article>
        <article className="metric-card"><span>Failed Controls</span><strong>{failed}</strong></article>
        <article className="metric-card"><span>Collection Issues</span><strong>{failedCollectors}</strong></article>
        <article className="metric-card"><span>Licensing Required</span><strong>{coverage.licensing_required ?? 0}</strong></article>
        <article className="metric-card"><span>Manual Validation</span><strong>{coverage.manual_validation ?? 0}</strong></article>
        <article className="metric-card"><span>Coverage</span><strong>{visibleCoverage}%</strong></article>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Executive Scorecard</h2>
            <p>Readiness by Microsoft 365 workload.</p>
          </div>
          <Link className="btn-secondary inline" to={`/assessments/${assessmentId}/report`}>
            <FileText size={16} />
            Report
          </Link>
        </div>
        <div className="scorecard-grid">
          {scorecard.map((item) => (
            <article className="scorecard-tile" key={item.domain}>
              <h3>{item.domain}</h3>
              <strong>{item.passPct}% pass</strong>
              <span>{item.failPct}% fail · {item.rating} risk</span>
              <div className="mini-progress"><i style={{ width: `${item.passPct}%` }} /></div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Assessment Results</h2>
            <p>{coverage.total_parameters ?? rows.length} business-readable control outcomes.</p>
          </div>
          <div className="segmented-control" aria-label="Assessment result status filter">
            {CONTROL_FILTERS.map((item) => (
              <button
                type="button"
                key={item.value}
                className={controlFilter === item.value ? "active" : ""}
                onClick={() => setControlFilter(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <div className="table-wrap executive-results-wrap">
          <table className="data-table executive-results-table">
            <thead>
              <tr>
                <th>Parameter</th>
                <th>Service</th>
                <th>Status</th>
                <th>Actual Result</th>
                <th>Expected Result</th>
                <th>Severity</th>
                <th>Business Impact</th>
                <th>Recommendation</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((item) => (
                <tr key={item.parameter_key}>
                  <td><strong>{businessName(item)}</strong></td>
                  <td>{businessDomain(item)}</td>
                  <td><span className={`status-pill tone-${statusTone(item.status)}`}>{executiveStatus(item.status)}</span></td>
                  <td>{foundText(item)}</td>
                  <td>{expectedText(item)}</td>
                  <td>{item.severity || "info"}</td>
                  <td>{item.recommendation?.impact || "This control affects Copilot readiness, data exposure, or governance posture."}</td>
                  <td>{item.recommendation?.recommendation_text || "Review and remediate this control according to Microsoft 365 readiness guidance."}</td>
                  <td>
                    <button type="button" className="btn-secondary inline" onClick={() => setSelected(item)}>
                      View
                    </button>
                  </td>
                </tr>
              ))}
              {!rows.length && (
                <tr><td colSpan="9" className="muted-text">No assessment results are available yet.</td></tr>
              )}
              {rows.length > 0 && visibleRows.length === 0 && (
                <tr><td colSpan="9" className="muted-text">No controls match this filter.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Recommendations</h2>
            <p>Priority actions grouped by business risk.</p>
          </div>
        </div>
        <div className="recommendation-groups">
          {["critical", "high", "medium", "low"].map((severity) => {
            const items = safeRecommendations.filter((item) => String(item.severity || "medium").toLowerCase() === severity);
            return (
              <article className="recommendation-group" key={severity}>
                <h3>{severity}</h3>
                {items.map((item) => (
                  <div className="recommendation-action" key={item.id || item.title}>
                    <strong>{item.title || "Recommendation"}</strong>
                    <p>{item.impact || item.recommendation_text || "Apply the recommended remediation for this control."}</p>
                    <span>{item.effort || "medium"} effort</span>
                  </div>
                ))}
                {!items.length && <p className="muted-text">No {severity} recommendations.</p>}
              </article>
            );
          })}
          {!safeRecommendations.length && <p className="muted-text">No recommendations were generated from assessment results.</p>}
        </div>
      </section>

      <DetailDrawer item={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
