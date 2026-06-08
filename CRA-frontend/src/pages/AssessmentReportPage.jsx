import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, FilePlus2, History } from "lucide-react";
import {
  getAssessment,
  getAssessmentEvidence,
  getAssessmentFindings,
  getAssessmentRecommendations,
  generateAssessmentReport,
  getAssessmentReport,
} from "../api/assessmentApi";
import LoadingSpinner from "../components/LoadingSpinner";
import ReportDownloadPanel from "../components/report/ReportDownloadPanel";
import ReportPageErrorBoundary from "../components/report/ReportPageErrorBoundary";
import ReportSummaryCards from "../components/report/ReportSummaryCards";
import { useAuth } from "../context/AuthContext";
import { extractApiError } from "../utils/apiErrors";
import { businessDomain, businessName, executiveStatus, foundText, riskRating, sortBusinessPriority, statusTone } from "../utils/executiveFormatters";

const REPORT_STATUS_COPY = {
  generated: {
    title: "Report generated",
    message: "PDF download is available for this assessment.",
  },
  not_generated: {
    title: "Report not generated",
    message: "Live report data is available. Generate artifacts when you need downloadable files.",
  },
  generation_failed: {
    title: "Report generation failed",
    message: "Report data can still be reviewed below. Generate again after the assessment is available.",
  },
};

async function recoverRequest(label, request, fallback, onError) {
  try {
    return await request();
  } catch (err) {
    const message = extractApiError(err);
    onError({ label, message });
    return fallback;
  }
}

function serviceReadiness(rows = []) {
  const services = ["Identity", "Exchange", "Teams", "SharePoint", "OneDrive", "Purview"];
  return services.map((service) => {
    const items = rows.filter((item) => businessDomain(item) === service);
    const pass = items.filter((item) => item.status === "PASS").length;
    const readiness = items.length ? Math.round((pass / items.length) * 100) : 0;
    return { service, readiness, total: items.length, rating: riskRating(readiness) };
  });
}

function AssessmentReportContent() {
  const { assessmentId } = useParams();
  const { user } = useAuth();
  const [assessmentData, setAssessmentData] = useState(null);
  const [findings, setFindings] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [evidenceCoverage, setEvidenceCoverage] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [report, setReport] = useState(null);
  const [requestErrors, setRequestErrors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    setRequestErrors([]);
    try {
      const errors = [];
      const captureError = (item) => errors.push(item);
      const assessment = await recoverRequest(
        "ASSESSMENT",
        () => getAssessment(assessmentId),
        null,
        captureError
      );
      if (assessment?.tenant_id && user?.microsoft_tid && assessment.tenant_id !== user.microsoft_tid) {
        captureError({
          label: "TENANT",
          message: "This assessment belongs to a different tenant than the signed-in user.",
        });
      }
      const [findingData, evidenceData, recommendationData, reportData] = await Promise.all([
        recoverRequest("FINDINGS", () => getAssessmentFindings(assessmentId, { limit: 100 }), [], captureError),
        recoverRequest("EVIDENCE", () => getAssessmentEvidence(assessmentId), { parameters: [] }, captureError),
        recoverRequest("RECOMMENDATIONS", () => getAssessmentRecommendations(assessmentId), [], captureError),
        recoverRequest("REPORT", () => getAssessmentReport(assessmentId), {}, captureError),
      ]);
      setAssessmentData(assessment);
      setFindings(findingData ?? []);
      setEvidence(evidenceData?.parameters ?? []);
      setEvidenceCoverage(evidenceData?.coverage ?? null);
      setRecommendations(recommendationData ?? []);
      setReport(reportData ?? {});
      setRequestErrors(errors);
      const blockingError = errors.find((item) => ["ASSESSMENT", "REPORT"].includes(item.label));
      setError(blockingError?.message ?? null);
    } catch (err) {
      setError(extractApiError(err));
      setReport({});
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, [assessmentId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const reportData = await generateAssessmentReport(assessmentId);
      setReport(reportData ?? {});
    } catch (err) {
      setError(extractApiError(err));
      setReport((current) => ({ ...(current ?? {}), status: "generation_failed" }));
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <LoadingSpinner label="Loading report..." />;
  }

  const safeReport = report ?? {};
  const summary = safeReport.summary ?? {};
  const safeFindings = findings ?? [];
  const safeRecommendations = recommendations ?? [];
  const safeEvidence = evidence ?? [];
  const safeCoverage = evidenceCoverage ?? {};
  const reportStatus = safeReport.status ?? "not_generated";
  const statusCopy = REPORT_STATUS_COPY[reportStatus] ?? REPORT_STATUS_COPY.not_generated;
  const serviceRows = serviceReadiness(safeEvidence);
  const severityDistribution = ["critical", "high", "medium", "low"].map((severity) => ({
    severity,
    count: safeEvidence.filter((item) => item.status !== "PASS" && String(item.severity || "info").toLowerCase() === severity).length,
  }));

  return (
    <ReportPageErrorBoundary
      failedProps={{
        assessmentId,
        assessmentData,
        report: safeReport,
        findings: safeFindings,
        evidence: safeEvidence,
        recommendations: safeRecommendations,
      }}
    >
      <div className="page-stack report-page">
        <div className="page-header">
          <div>
            <Link className="back-link" to={`/assessments/${assessmentId}`}>
              <ArrowLeft size={16} />
              Assessment
            </Link>
            <h1>Enterprise Report</h1>
            <p>Executive summary, analytics, and downloadable CRA deliverables.</p>
          </div>
          <div className="report-actions">
            <Link className="btn-secondary inline" to="/reports">
              <History size={16} />
              Report History
            </Link>
            <button type="button" className="primary-action" onClick={handleGenerate} disabled={generating}>
              <FilePlus2 size={16} />
              {generating ? "Generating..." : "Generate Report"}
            </button>
          </div>
        </div>

        {error && <div className="error-banner">{error}</div>}
        {generating && <LoadingSpinner label="Generating enterprise report..." />}

        <div className={reportStatus === "generation_failed" ? "error-banner" : "info-banner"}>
          <strong>{statusCopy.title}</strong>
          <p>{statusCopy.message}</p>
        </div>

        {!safeReport.summary && (
          <div className="warning-banner">
            Report data is empty. Generate the report after assessment completion.
          </div>
        )}

        <ReportSummaryCards summary={summary} />

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Executive Summary</h2>
              <p>{summary.deployment_recommendation ?? "Generate a report to preview deployment guidance."}</p>
            </div>
          </div>
          <div className="report-executive-grid">
            <article>
              <span>Readiness Score</span>
              <strong>{summary.overall_readiness ?? assessmentData?.overall_score ?? 0}%</strong>
            </article>
            <article>
              <span>Top Risks</span>
              <strong>{safeEvidence.filter((item) => item.status === "FAIL").length}</strong>
            </article>
            <article>
              <span>Recommendations</span>
              <strong>{summary.recommendation_count ?? safeRecommendations.length}</strong>
            </article>
            <article>
              <span>Assessment Coverage</span>
              <strong>{safeCoverage.coverage_percent ?? 0}%</strong>
            </article>
          </div>
        </section>

        <section className="two-column">
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Risk Distribution</h2>
                <p>Open risks by severity.</p>
              </div>
            </div>
            <div className="risk-distribution">
              {severityDistribution.map((item) => (
                <article key={item.severity}>
                  <span className={`severity severity-${item.severity}`}>{item.severity}</span>
                  <strong>{item.count}</strong>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Service Readiness</h2>
                <p>Readiness score by workload.</p>
              </div>
            </div>
            <div className="service-readiness-list">
              {serviceRows.map((item) => (
                <article key={item.service}>
                  <div>
                    <strong>{item.service}</strong>
                    <span>{item.total} controls · {item.rating} risk</span>
                  </div>
                  <b>{item.readiness}%</b>
                </article>
              ))}
            </div>
          </section>
        </section>

        <section className="two-column">
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Top Risks</h2>
                <p>Controls requiring executive attention.</p>
              </div>
            </div>
            <div className="blocker-list">
              {sortBusinessPriority(safeEvidence).filter((item) => item.status !== "PASS").slice(0, 5).map((item) => (
                <article className="blocker-row" key={item.parameter_key}>
                  <span className={`status-dot tone-${statusTone(item.status)}`} />
                  <div>
                    <h3>{businessName(item)}</h3>
                    <p>{foundText(item)}</p>
                  </div>
                  <span className={`status-pill tone-${statusTone(item.status)}`}>{executiveStatus(item.status)}</span>
                </article>
              ))}
              {!safeEvidence.length && <p className="muted-text">No evidence rows are available.</p>}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Top Recommendations</h2>
                <p>Priority remediation actions.</p>
              </div>
            </div>
            <div className="recommendation-list compact">
              {safeRecommendations.slice(0, 5).map((item) => (
                <article key={item.id || item.title}>
                  <strong>{item.title || "Recommendation"}</strong>
                  <p>{item.impact || item.recommendation_text || "Apply the recommended remediation for this control."}</p>
                  <span>{item.effort || "medium"} effort</span>
                </article>
              ))}
              {!safeRecommendations.length && <p className="muted-text">No recommendations are available.</p>}
            </div>
          </section>
        </section>

        <ReportDownloadPanel assessmentId={assessmentId} report={safeReport} />
        {requestErrors.length > 0 && <div className="warning-banner">Some report data was unavailable. The executive summary is based on available assessment results.</div>}
      </div>
    </ReportPageErrorBoundary>
  );
}

export default function AssessmentReportPage() {
  return <AssessmentReportContent />;
}
