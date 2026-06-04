import { Download, FileText } from "lucide-react";
import { downloadAssessmentReport } from "../../api/assessmentApi";

const MIME_TYPES = {
  pdf: "application/pdf",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};

async function saveReport(assessmentId, reportType) {
  const data = await downloadAssessmentReport(assessmentId, reportType);
  const blob = new Blob([data], { type: MIME_TYPES[reportType] });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `copilot-readiness-assessment.${reportType}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function ReportDownloadPanel({ assessmentId, report = {} }) {
  const safeReport = report ?? {};
  const artifacts = Array.isArray(safeReport.artifacts) ? safeReport.artifacts : [];
  const hasPdf = artifacts.some((item) => item.report_type === "pdf");
  const hasDocx = artifacts.some((item) => item.report_type === "docx");

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Report Downloads</h2>
          <p>Enterprise CRA report artifacts generated for this assessment.</p>
        </div>
      </div>
      <div className="download-actions">
        <button
          type="button"
          className={`primary-action ${hasPdf ? "" : "disabled-link"}`}
          disabled={!hasPdf}
          onClick={() => saveReport(assessmentId, "pdf")}
        >
          <Download size={16} />
          Download PDF
        </button>
        <button
          type="button"
          className={`btn-secondary inline ${hasDocx ? "" : "disabled-link"}`}
          disabled={!hasDocx}
          onClick={() => saveReport(assessmentId, "docx")}
        >
          <FileText size={16} />
          Download DOCX
        </button>
      </div>
    </section>
  );
}
