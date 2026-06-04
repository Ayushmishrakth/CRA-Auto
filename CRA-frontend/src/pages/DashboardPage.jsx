import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, CalendarDays, PlayCircle, ShieldCheck, TrendingUp } from "lucide-react";
import { getAssessmentEvidence, getAssessmentFindings, getAssessmentRecommendations } from "../api/assessmentApi";
import { listTenants } from "../api/tenantApi";
import LoadingSpinner from "../components/LoadingSpinner";
import ReadinessRadialChart from "../components/charts/ReadinessRadialChart";
import ScoreTrendChart from "../components/charts/ScoreTrendChart";
import { useAuth } from "../context/AuthContext";
import { useAssessments } from "../context/AssessmentContext";
import { buildScoreTrend, formatDateTime, numberOrZero } from "../utils/assessmentFormatters";
import { getApiErrorMessage } from "../utils/apiErrors";
import {
  businessDomain,
  businessName,
  coveragePercent,
  executiveStatus,
  findingToExecutiveRow,
  foundText,
  riskRating,
  sortBusinessPriority,
  statusTone,
} from "../utils/executiveFormatters";

function ScoreKpi({ label, value }) {
  const score = value == null ? null : Math.round(numberOrZero(value));
  const width = score == null ? 0 : Math.max(0, Math.min(100, score));
  return (
    <article className="metric-card executive-kpi">
      <span>{label}</span>
      <strong>{score == null ? "-" : `${score}%`}</strong>
      <div className="mini-progress"><i style={{ width: `${width}%` }} /></div>
    </article>
  );
}

function domainPassScore(rows, domain) {
  const domainRows = rows.filter((item) => businessDomain(item) === domain);
  if (!domainRows.length) return null;
  return Math.round((domainRows.filter((item) => item.status === "PASS").length / domainRows.length) * 100);
}

const HEATMAP_SERVICES = ["Entra ID", "Exchange", "Teams", "SharePoint", "OneDrive", "Purview"];
const HEATMAP_SEVERITIES = ["critical", "high", "medium", "low"];

function serviceLabel(row) {
  const domain = businessDomain(row);
  if (domain === "Identity") return "Entra ID";
  if (domain === "Exchange") return "Exchange";
  if (domain === "Teams") return "Teams";
  if (domain === "SharePoint") return "SharePoint";
  if (domain === "OneDrive") return "OneDrive";
  if (domain === "Purview") return "Purview";
  return domain;
}

function countRows(rows, predicate) {
  return rows.filter(predicate).length;
}

function serviceScorecards(rows) {
  return HEATMAP_SERVICES.map((service) => {
    const items = rows.filter((item) => serviceLabel(item) === service);
    const pass = countRows(items, (item) => item.status === "PASS");
    const fail = countRows(items, (item) => item.status === "FAIL");
    const readiness = items.length ? Math.round((pass / items.length) * 100) : 0;
    return { service, total: items.length, pass, fail, readiness, rating: riskRating(readiness) };
  });
}

function heatmap(rows) {
  return HEATMAP_SERVICES.map((service) => {
    const items = rows.filter((item) => serviceLabel(item) === service && item.status !== "PASS");
    const counts = Object.fromEntries(
      HEATMAP_SEVERITIES.map((severity) => [
        severity,
        countRows(items, (item) => String(item.severity || "info").toLowerCase() === severity),
      ])
    );
    return { service, counts };
  });
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { assessments, loading, error, fetchTenantAssessments, startAssessment } = useAssessments();
  const [tenant, setTenant] = useState(null);
  const [evidencePayload, setEvidencePayload] = useState(null);
  const [findings, setFindings] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [startBusy, setStartBusy] = useState(false);
  const [startError, setStartError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!user?.microsoft_tid) return;
    listTenants()
      .then((items) => setTenant(items?.[0] ?? null))
      .catch(() => setTenant(null));
    fetchTenantAssessments(user.microsoft_tid, { limit: 100 });
  }, [user?.microsoft_tid, fetchTenantAssessments]);

  const tenantAssessments = useMemo(
    () => assessments.filter((assessment) => assessment.tenant_id === user?.microsoft_tid),
    [assessments, user?.microsoft_tid]
  );

  const latest = useMemo(
    () =>
      [...tenantAssessments]
        .filter((assessment) => assessment.status === "completed" || assessment.overall_score != null)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0] ||
      [...tenantAssessments].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0],
    [tenantAssessments]
  );

  useEffect(() => {
    if (!latest?.id) return;
    let active = true;
    Promise.all([
      getAssessmentEvidence(latest.id).catch(() => null),
      getAssessmentFindings(latest.id, { limit: 100 }).catch(() => []),
      getAssessmentRecommendations(latest.id).catch(() => []),
    ]).then(([evidence, findingData, recommendationData]) => {
      if (!active) return;
      setEvidencePayload(evidence);
      setFindings(Array.isArray(findingData) ? findingData : []);
      setRecommendations(Array.isArray(recommendationData) ? recommendationData : []);
    });
    return () => {
      active = false;
    };
  }, [latest?.id]);

  const evidenceRows = evidencePayload?.parameters ?? [];
  const safeRecommendations = Array.isArray(recommendations) ? recommendations : [];
  const recommendationByKey = Object.fromEntries(safeRecommendations.map((item) => [item.parameter_key, item]));
  const findingRows = findings.map((item) => findingToExecutiveRow(item, recommendationByKey[item.parameter_key]));
  const visibleRows = evidenceRows.length ? evidenceRows : findingRows;
  const coverage = evidencePayload?.coverage ?? {};
  const riskSummary = useMemo(() => {
    const base = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const row of visibleRows) {
      if (row.status !== "FAIL") continue;
      const severity = String(row.severity || "medium").toLowerCase();
      if (base[severity] !== undefined) base[severity] += 1;
    }
    return base;
  }, [visibleRows]);

  const blockers = useMemo(() => sortBusinessPriority(visibleRows).filter((item) => item.status !== "PASS").slice(0, 5), [visibleRows]);
  const passedCount = visibleRows.filter((item) => item.status === "PASS").length;
  const failedCount = visibleRows.filter((item) => item.status === "FAIL").length;
  const score = latest?.overall_score == null
    ? coveragePercent(coverage)
    : Math.round(numberOrZero(latest?.overall_score));
  const fallbackCoverage = visibleRows.length
    ? Math.round((visibleRows.filter((item) => ["PASS", "FAIL"].includes(item.status)).length / visibleRows.length) * 100)
    : 0;
  const visibleCoverage = coverage.coverage_percent ?? (coveragePercent(coverage) || fallbackCoverage);
  const previous = tenantAssessments.find((item) => item.id !== latest?.id && item.overall_score != null);
  const trend = previous ? score - Math.round(numberOrZero(previous.overall_score)) : 0;
  const canStart = (tenant?.status || "ACTIVE") === "ACTIVE";
  const serviceCards = serviceScorecards(visibleRows);
  const heatmapRows = heatmap(visibleRows);

  const handleStart = async () => {
    if (!user?.microsoft_tid) return;
    if (!canStart) {
      navigate("/settings");
      return;
    }
    setStartBusy(true);
    setStartError(null);
    try {
      const assessment = await startAssessment(user.microsoft_tid);
      navigate(`/assessments/${assessment.id}`);
    } catch (err) {
      setStartError(getApiErrorMessage(err, "Unable to start assessment"));
    } finally {
      setStartBusy(false);
    }
  };

  if (!user || (loading && !tenantAssessments.length)) return <LoadingSpinner label="Loading executive dashboard..." />;

  return (
    <div className="dashboard page-stack">
      <section className="executive-hero">
        <div>
          <span className="eyebrow">Copilot readiness</span>
          <h1>{tenant?.tenant_name || "Microsoft 365 Environment"}</h1>
          <div className="hero-meta">
            <span><CalendarDays size={15} /> {formatDateTime(latest?.created_at)}</span>
            <span><TrendingUp size={15} /> Trend {trend >= 0 ? "+" : ""}{trend}%</span>
            <span>Risk rating {riskRating(score)}</span>
          </div>
        </div>
        <div className="hero-score">
          <span>Copilot Readiness Score</span>
          <strong>{score}%</strong>
        </div>
        <button type="button" className="primary-action" onClick={handleStart} disabled={startBusy}>
          {canStart ? <PlayCircle size={16} /> : <ShieldCheck size={16} />}
          {startBusy ? "Starting..." : canStart ? "Start Assessment" : "Open Settings"}
        </button>
      </section>

      {(error || startError) && <div className="error-banner">{startError || error}</div>}

      {!latest && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>No assessment data yet</h2>
              <p>Start an assessment to populate readiness scores, risks, recommendations, and coverage.</p>
            </div>
            <button type="button" className="primary-action" onClick={handleStart} disabled={startBusy}>
              <PlayCircle size={16} />
              Start Assessment
            </button>
          </div>
        </section>
      )}

      <section className="detail-grid executive-overview">
        <ReadinessRadialChart score={score} />
        <div className="metric-grid">
          <ScoreKpi label="Overall Readiness" value={score} />
          <ScoreKpi label="Identity Readiness" value={latest?.identity_score ?? domainPassScore(visibleRows, "Identity")} />
          <ScoreKpi label="Security Readiness" value={latest?.security_score ?? score} />
          <ScoreKpi label="Compliance Readiness" value={latest?.compliance_score ?? domainPassScore(visibleRows, "Purview")} />
          <ScoreKpi label="Collaboration Readiness" value={latest?.collaboration_score ?? domainPassScore(visibleRows, "SharePoint") ?? domainPassScore(visibleRows, "Teams")} />
        </div>
      </section>

      <section className="metric-grid dashboard-metrics">
        <article className="metric-card"><span>Total Parameters</span><strong>{coverage.total_parameters ?? visibleRows.length ?? 0}</strong></article>
        <article className="metric-card"><span>Passed Controls</span><strong>{passedCount}</strong></article>
        <article className="metric-card"><span>Failed Controls</span><strong>{failedCount}</strong></article>
        <article className="metric-card"><span>Licensing Required</span><strong>{coverage.licensing_required ?? 0}</strong></article>
        <article className="metric-card"><span>Manual Validation</span><strong>{coverage.manual_validation ?? 0}</strong></article>
        <article className="metric-card risk-card critical"><span>Critical Findings</span><strong>{riskSummary.critical}</strong></article>
        <article className="metric-card risk-card high"><span>High Findings</span><strong>{riskSummary.high}</strong></article>
        <article className="metric-card"><span>Coverage</span><strong>{visibleCoverage}%</strong></article>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Risk Heatmap</h2>
            <p>Open readiness risks by Microsoft 365 workload and severity.</p>
          </div>
        </div>
        <div className="heatmap-table">
          <div className="heatmap-row heatmap-head">
            <span>Workload</span>
            {HEATMAP_SEVERITIES.map((severity) => <span key={severity}>{severity}</span>)}
          </div>
          {heatmapRows.map((row) => (
            <div className="heatmap-row" key={row.service}>
              <strong>{row.service}</strong>
              {HEATMAP_SEVERITIES.map((severity) => (
                <span className={`heatmap-cell heat-${severity}`} key={severity}>
                  {row.counts[severity]}
                </span>
              ))}
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Service Scorecards</h2>
            <p>Pass/fail posture and readiness by workload.</p>
          </div>
        </div>
        <div className="service-scorecard-grid">
          {serviceCards.map((item) => (
            <article className="service-scorecard" key={item.service}>
              <div>
                <h3>{item.service}</h3>
                <span>{item.rating} risk</span>
              </div>
              <strong>{item.readiness}%</strong>
              <dl>
                <div><dt>Pass</dt><dd>{item.pass}</dd></div>
                <div><dt>Fail</dt><dd>{item.fail}</dd></div>
                <div><dt>Total</dt><dd>{item.total}</dd></div>
              </dl>
              <div className="mini-progress"><i style={{ width: `${item.readiness}%` }} /></div>
            </article>
          ))}
        </div>
      </section>

      <section className="two-column">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Top Blockers</h2>
              <p>Highest priority items preventing Copilot readiness.</p>
            </div>
            {latest?.id && (
              <button type="button" className="btn-secondary inline" onClick={() => navigate(`/assessments/${latest.id}`)}>
                <ArrowUpRight size={16} />
                View results
              </button>
            )}
          </div>
          <div className="blocker-list">
            {blockers.map((item) => (
              <article className="blocker-row" key={item.parameter_key}>
                <span className={`status-dot tone-${statusTone(item.status)}`} />
                <div>
                  <h3>{businessName(item)}</h3>
                  <p>{foundText(item)}</p>
                </div>
                <span className={`status-pill tone-${statusTone(item.status)}`}>{executiveStatus(item.status)}</span>
              </article>
            ))}
            {!blockers.length && <p className="muted-text">No blockers found in the latest assessment.</p>}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Top Recommendations</h2>
              <p>Actions with the highest impact on readiness.</p>
            </div>
          </div>
          <div className="recommendation-list compact">
            {safeRecommendations.slice(0, 5).map((item) => (
              <article key={item.id || item.title}>
                <strong>{item.title || "Recommendation"}</strong>
                <p>{item.impact || item.recommendation_text || "Review this control and apply the recommended remediation."}</p>
              </article>
            ))}
            {!safeRecommendations.length && <p className="muted-text">Recommendations will appear after assessment completion.</p>}
          </div>
        </section>
      </section>

      <ScoreTrendChart data={buildScoreTrend(tenantAssessments)} />
    </div>
  );
}
