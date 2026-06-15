import { useState } from "react";
import { Download, FileText, FileSpreadsheet, Printer, Settings } from "lucide-react";
import { downloadAssessmentReport } from "../../api/assessmentApi";
import { generateCustomizedReport, downloadReport } from "../../api/reportApi";
import CustomizeReportModal from "./CustomizeReportModal";
import { useToast } from "../../context/ToastContext";


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
  const toast = useToast();
  const [busyType, setBusyType] = useState(null);
  const [showCustomizeModal, setShowCustomizeModal] = useState(false);
  const [customizing, setCustomizing] = useState(false);

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

  const handleGenerateCustomized = async (customization) => {
    setCustomizing(true);
    try {
      toast.info("Generating customized report...");
      const { data, filename } = await generateCustomizedReport(assessmentId, customization);
      await downloadReport(data, filename);
      toast.success("Report generated and downloaded successfully");
      setShowCustomizeModal(false);
    } catch (error) {
      console.error("Report generation error:", error);
      toast.error(error.message || "Failed to generate customized report");
    } finally {
      setCustomizing(false);
    }
  };

  return (
    <>
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
          <button
            type="button"
            className="btn-secondary inline"
            onClick={() => setShowCustomizeModal(true)}
            title="Add logo and company details to your report"
          >
            <Settings size={16} />
            Customize & Download
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

      {showCustomizeModal && (
        <CustomizeReportModal
          assessmentId={assessmentId}
          isLoading={customizing}
          onClose={() => setShowCustomizeModal(false)}
          onGenerate={handleGenerateCustomized}
        />
      )}
    </>
  );
}
