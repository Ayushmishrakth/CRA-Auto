import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, FilePlus2, History, Upload } from "lucide-react";
import {
  getAssessment,
  getAssessmentEvidence,
  getAssessmentFindings,
  getAssessmentRecommendations,
  generateAssessmentReport,
  getAssessmentReport,
  customizeAssessmentReport,
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
    message: "Downloadable report artifacts are available for this assessment.",
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
  const [logoFile, setLogoFile] = useState(null);
  const [logoPreview, setLogoPreview] = useState(null);
  const [companyName, setCompanyName] = useState("");
  const [address, setAddress] = useState("");
  const [outputFormat, setOutputFormat] = useState("docx");
  const [customizing, setCustomizing] = useState(false);
  const [customizeSuccess, setCustomizeSuccess] = useState(false);

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
      await generateAssessmentReport(assessmentId, outputFormat);
      const reportData = await getAssessmentReport(assessmentId);
      setReport(reportData ?? {});
    } catch (err) {
      setError(extractApiError(err));
      setReport((current) => ({ ...(current ?? {}), status: "generation_failed" }));
    } finally {
      setGenerating(false);
    }
  };

  const handleLogoChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setLogoFile(file);
      const reader = new FileReader();
      reader.onload = (event) => {
        setLogoPreview(event.target?.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleCustomize = async () => {
    if (!logoFile && !companyName && !address && !outputFormat) {
      alert("Please fill in at least one field");
      return;
    }
    setCustomizing(true);
    setError(null);
    try {
      await customizeAssessmentReport(assessmentId, { logoFile, companyName, address, outputFormat });
      setCustomizeSuccess(true);
      setTimeout(() => setCustomizeSuccess(false), 3000);
    } catch (err) {
      setError(extractApiError(err));
    } finally {
      setCustomizing(false);
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
              Back to Assessment
            </Link>
          </div>
        </div>

        {error && <div className="error-banner">{error}</div>}
        {customizeSuccess && <div className="success-banner">✓ Report customization saved! Ready to generate.</div>}

        {/* MAIN CUSTOMIZATION SECTION - PROMINENT FOCUS */}
        <section className="customization-hero">
          <div className="customization-content">
            <div className="customization-header">
              <h1>📋 Customize Your Report</h1>
              <p className="subtitle">Add your company branding. Your logo and details will appear on <strong>every page</strong> of the generated PDF.</p>
            </div>

            {/* Logo Upload - Featured */}
            <div className="logo-upload-section">
              <div className="form-group full-width">
                <label htmlFor="logo-input" className="label-with-icon">🎨 Company Logo</label>
                <p className="label-hint">Will appear on cover page and every page header</p>
                <div className="logo-upload-container-large">
                  {logoPreview ? (
                    <div className="logo-preview-large">
                      <img src={logoPreview} alt="Logo preview" className="logo-img-preview" />
                      <button
                        type="button"
                        className="btn-change"
                        onClick={() => {
                          setLogoFile(null);
                          setLogoPreview(null);
                        }}
                      >
                        ✎ Change Logo
                      </button>
                    </div>
                  ) : (
                    <label htmlFor="logo-input" className="logo-upload-label-large">
                      <div className="upload-icon">📤</div>
                      <strong>Click to upload your logo</strong>
                      <span className="upload-hint">PNG, JPG, SVG • Max 5MB</span>
                      <input
                        id="logo-input"
                        type="file"
                        accept="image/png,image/jpeg,image/svg+xml"
                        onChange={handleLogoChange}
                        style={{ display: "none" }}
                      />
                    </label>
                  )}
                </div>
              </div>
            </div>

            {/* Company Details */}
            <div className="company-details-section">
              <div className="form-group">
                <label htmlFor="company-input" className="label-with-icon">🏢 Company Name</label>
                <input
                  id="company-input"
                  type="text"
                  placeholder="e.g., Acme Corporation"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className="form-input-large"
                />
              </div>

              <div className="form-group">
                <label htmlFor="address-input" className="label-with-icon">📍 Company Address</label>
                <textarea
                  id="address-input"
                  placeholder="e.g., 123 Business St, City, State 12345"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="form-input-large"
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label htmlFor="output-format" className="label-with-icon">Report Output</label>
                <select
                  id="output-format"
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  className="form-input-large"
                >
                  <option value="docx">Word DOCX - recommended</option>
                  <option value="pdf">PDF only</option>
                  <option value="both">Word DOCX and PDF</option>
                </select>
                <p className="label-hint">
                  DOCX preserves the sample Word template most reliably. PDF requires Word or LibreOffice conversion.
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="customization-actions">
              <button
                type="button"
                className="btn-apply"
                onClick={handleCustomize}
                disabled={customizing}
              >
                {customizing ? "⏳ Saving..." : "✓ Apply Customization"}
              </button>
              <button
                type="button"
                className="btn-generate-primary"
                onClick={handleGenerate}
                disabled={generating}
              >
                <FilePlus2 size={18} />
                {generating ? "Generating..." : "📄 Generate Report"}
              </button>
              <p className="action-hint">Your logo and details will appear on every page of the PDF</p>
            </div>
          </div>
        </section>

        {/* Only customization form is shown - old dashboards removed */}

        <ReportDownloadPanel assessmentId={assessmentId} report={safeReport} />
        {requestErrors.length > 0 && <div className="warning-banner">Some report data was unavailable. The executive summary is based on available assessment results.</div>}
      </div>
    </ReportPageErrorBoundary>
  );
}

export default function AssessmentReportPage() {
  return <AssessmentReportContent />;
}
