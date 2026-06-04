import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, X } from "lucide-react";
import { getAssessment, getAssessmentEvidence } from "../api/assessmentApi";
import LoadingSpinner from "../components/LoadingSpinner";
import { useAuth } from "../context/AuthContext";
import { extractApiError } from "../utils/apiErrors";
import {
  businessDomain,
  businessName,
  coveragePercent,
  executiveStatus,
  expectedText,
  foundText,
  sortBusinessPriority,
  statusTone,
} from "../utils/executiveFormatters";

const STATUSES = ["All", "PASS", "FAIL", "COLLECTION_ERROR", "LICENSING_REQUIRED", "MANUAL_VALIDATION", "NOT_COLLECTED"];

function DetailDrawer({ item, onClose }) {
  if (!item) return null;
  return (
    <aside className="evidence-drawer executive-drawer">
      <div className="panel-header">
        <div>
          <h2>{businessName(item)}</h2>
          <p>{businessDomain(item)} evidence summary</p>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close evidence">
          <X size={16} />
        </button>
      </div>
      <section className="assessment-outcome-card">
        <div><span>Status</span><strong><span className={`status-pill tone-${statusTone(item.status)}`}>{executiveStatus(item.status)}</span></strong></div>
        <div><span>Actual Result</span><strong>{foundText(item)}</strong></div>
        <div><span>Expected</span><strong>{expectedText(item)}</strong></div>
        <div><span>Severity</span><strong>{item.severity || "info"}</strong></div>
        <div><span>Recommendation</span><strong>{item.recommendation?.recommendation_text || "No recommendation generated."}</strong></div>
      </section>
    </aside>
  );
}

export default function AssessmentEvidencePage() {
  const { assessmentId } = useParams();
  const { user } = useAuth();
  const [assessment, setAssessment] = useState(null);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState("All");
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let active = true;
    async function loadEvidence() {
      setLoading(true);
      setError(null);
      try {
        const assessmentData = await getAssessment(assessmentId);
        if (active) setAssessment(assessmentData);
        if (user?.microsoft_tid && assessmentData.tenant_id !== user.microsoft_tid) {
          throw new Error(`This assessment belongs to tenant ${assessmentData.tenant_id}, but you are signed in to tenant ${user.microsoft_tid}.`);
        }
        const data = await getAssessmentEvidence(assessmentId);
        if (active) setPayload(data);
      } catch (err) {
        if (active) setError(extractApiError(err));
      } finally {
        if (active) setLoading(false);
      }
    }
    loadEvidence();
    return () => {
      active = false;
    };
  }, [assessmentId, user?.microsoft_tid]);

  const rows = useMemo(() => {
    const parameters = sortBusinessPriority(payload?.parameters ?? []);
    return parameters.filter((item) => status === "All" || item.status === status);
  }, [payload, status]);

  if (loading) return <LoadingSpinner label="Loading assessment evidence..." />;

  const coverage = payload?.coverage ?? {};

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <Link className="back-link" to={`/assessments/${assessmentId}`}>
            <ArrowLeft size={16} />
            Assessment
          </Link>
          <h1>Evidence</h1>
          <p>Business evidence summaries for the selected assessment.</p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="metric-grid dashboard-metrics">
        <article className="metric-card"><span>Collected</span><strong>{coverage.collected ?? 0}</strong></article>
        <article className="metric-card"><span>Failed Collectors</span><strong>{coverage.failed ?? 0}</strong></article>
        <article className="metric-card"><span>Licensing Required</span><strong>{coverage.licensing_required ?? 0}</strong></article>
        <article className="metric-card"><span>Manual Validation</span><strong>{coverage.manual_validation ?? 0}</strong></article>
        <article className="metric-card"><span>Coverage</span><strong>{coverage.coverage_percent ?? coveragePercent(coverage)}%</strong></article>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Control Evidence</h2>
            <p>{assessment?.status === "completed" ? "Assessment completed." : "Assessment evidence is still being collected."}</p>
          </div>
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            {STATUSES.map((item) => <option key={item} value={item}>{item === "All" ? "All statuses" : executiveStatus(item)}</option>)}
          </select>
        </div>

        <div className="control-grid">
          {rows.map((item) => (
            <article className="control-card" key={item.parameter_key}>
              <div className="control-card-top">
                <div>
                  <h3>{businessName(item)}</h3>
                  <p>{businessDomain(item)}</p>
                </div>
                <span className={`status-pill tone-${statusTone(item.status)}`}>{executiveStatus(item.status)}</span>
              </div>
              <dl>
                <dt>Found</dt>
                <dd>{foundText(item)}</dd>
                <dt>Expected</dt>
                <dd>{expectedText(item)}</dd>
              </dl>
              <button type="button" className="btn-secondary inline" onClick={() => setSelected(item)}>View Details</button>
            </article>
          ))}
          {!rows.length && <p className="muted-text">No controls match the selected filter.</p>}
        </div>
      </section>

      <DetailDrawer item={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
