import { useState } from "react";
import { Download, FileText, FileSpreadsheet, Printer } from "lucide-react";
import { downloadAssessmentReport } from "../../api/assessmentApi";


async function saveReport(assessmentId, reportType) {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  const { data, filename } = await downloadAssessmentReport(assessmentId, reportType);
  // data is already a correctly-typed Blob from downloadAssessmentReport
  const url = URL.createObjectURL(data);
  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

function csvEscape(value) {
  const text = value === null || value === undefined || value === "" ? "No data available" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function saveCsv(report = {}) {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  const rows = report?.summary
    ? Object.entries(report.summary).map(([key, value]) => [key, value])
    : [["message", "Assessment data not collected"]];
  const csv = ["Field,Value", ...rows.map((row) => row.map(csvEscape).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = "copilot-readiness-assessment.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

export default function ReportDownloadPanel({ assessmentId, report = {} }) {
  const [busyType, setBusyType] = useState(null);
  const safeReport = report ?? {};
  const artifacts = Array.isArray(safeReport.artifacts) ? safeReport.artifacts : [];
  const hasDocx = artifacts.some((item) => item.report_type === "docx");
  const hasPdf = artifacts.some((item) => item.report_type === "pdf");
  const runDownload = async (reportType) => {
    setBusyType(reportType);
    try {
      await saveReport(assessmentId, reportType);
    } finally {
      setBusyType(null);
    }
  };

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
          className={`primary-action ${hasDocx ? "" : "disabled-link"}`}
          disabled={!hasDocx}
          onClick={() => runDownload("docx")}
        >
          <FileText size={16} />
          {busyType === "docx" ? "Preparing DOCX..." : "Export DOCX"}
        </button>
        <button
          type="button"
          className={`btn-secondary inline ${hasPdf ? "" : "disabled-link"}`}
          disabled={!hasPdf}
          onClick={() => runDownload("pdf")}
        >
          <Download size={16} />
          {busyType === "pdf" ? "Preparing PDF..." : "Export PDF"}
        </button>
        <button type="button" className="btn-secondary inline" onClick={() => saveCsv(safeReport)}>
          <FileSpreadsheet size={16} />
          Export Excel
        </button>
        <button type="button" className="btn-secondary inline" onClick={() => window.print()}>
          <Printer size={16} />
          Print Report
        </button>
      </div>
    </section>
  );
}
