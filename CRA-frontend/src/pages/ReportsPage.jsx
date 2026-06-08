import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Download, Eye, Plus, AlertCircle } from "lucide-react";
import Button from "../components/ui/Button";
import ScoreBadge from "../components/ui/ScoreBadge";
import EmptyState from "../components/ui/EmptyState";
import { useToast } from "../context/ToastContext";
import { listAssessments, downloadAssessmentReport } from "../api/assessmentApi";

function fmtDate(d) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", { dateStyle: "medium" });
}

function SkeletonRow() {
  return (
    <tr className="border-b border-[#F3F4F6]">
      {[160, 60, 90, 80].map((w, i) => (
        <td key={i} className="px-4 py-3">
          <div className="skeleton h-4 rounded" style={{ width: w }} />
        </td>
      ))}
    </tr>
  );
}

export default function ReportsPage() {
  const navigate   = useNavigate();
  const toast      = useToast();
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const [assessments, setAssessments]   = useState([]);
  const [downloading, setDownloading]   = useState({}); // { [id-type]: true }

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listAssessments({ per_page: 100, status: "completed", sort: "newest" });
      setAssessments(data?.items ?? []);
    } catch {
      setError("Could not load reports. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleDownload = async (assessmentId, tenantName, reportType) => {
    const key = `${assessmentId}-${reportType}`;
    setDownloading((prev) => ({ ...prev, [key]: true }));
    try {
      const { data } = await downloadAssessmentReport(assessmentId, reportType);
      const date  = new Date().toISOString().slice(0, 10);
      const safe  = (tenantName || "tenant").replace(/\s+/g, "_").replace(/[^a-zA-Z0-9_-]/g, "");
      const name  = `CRA_Report_${safe}_${date}.${reportType}`;
      const url   = URL.createObjectURL(data);
      const a     = document.createElement("a");
      a.href = url; a.download = name; a.click();
      URL.revokeObjectURL(url);
      toast.success(`${reportType.toUpperCase()} downloaded`);
    } catch {
      toast.error(`Failed to download ${reportType.toUpperCase()}. Generate the report first from the Results page.`);
    } finally {
      setDownloading((prev) => ({ ...prev, [key]: false }));
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-[#111827] m-0">Reports</h2>
        <Button variant="primary" onClick={() => navigate("/assessments/new")}>
          <Plus size={16} /> New Assessment
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <AlertCircle size={16} className="flex-shrink-0" />
          <span className="flex-1">{error}</span>
          <button onClick={fetchData} className="font-semibold underline text-red-700 hover:text-red-900 whitespace-nowrap">Retry</button>
        </div>
      )}

      <div className="bg-white border border-[#E5E7EB] rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E5E7EB]">
                {["Tenant", "Score", "Completed", "Download"].map((h) => (
                  <th key={h} className="text-left text-xs font-semibold text-[#6B7280] px-4 py-3 uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} />)
                : assessments.length === 0
                ? (
                  <tr>
                    <td colSpan={4}>
                      <EmptyState
                        icon={FileText}
                        title="No reports yet"
                        subtitle="Complete an assessment and generate a report to see it here."
                        action={
                          <Button variant="primary" onClick={() => navigate("/assessments/new")}>
                            <Plus size={16} /> Run First Assessment
                          </Button>
                        }
                      />
                    </td>
                  </tr>
                )
                : assessments.map((a) => (
                  <tr key={a.id} className="border-b border-[#F3F4F6] hover:bg-[#F8F9FA] transition-colors">
                    <td className="px-4 py-3 font-semibold text-[#111827]">{a.tenant_name}</td>
                    <td className="px-4 py-3">
                      {a.overall_score != null
                        ? <ScoreBadge value={a.overall_score} />
                        : <span className="text-[#9CA3AF]">—</span>}
                    </td>
                    <td className="px-4 py-3 text-[#6B7280] whitespace-nowrap">
                      {fmtDate(a.completed_at || a.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => navigate(`/assessments/${a.id}/results`)}
                          className="p-1.5 rounded-md text-[#6B7280] hover:bg-[#EFF6FC] hover:text-[#0078D4] transition-colors"
                          title="View results"
                        >
                          <Eye size={15} />
                        </button>
                        <button
                          onClick={() => handleDownload(a.id, a.tenant_name, "pdf")}
                          disabled={downloading[`${a.id}-pdf`]}
                          className="p-1.5 rounded-md text-[#6B7280] hover:bg-[#EFF6FC] hover:text-[#0078D4] transition-colors disabled:opacity-40"
                          title="Download PDF"
                        >
                          <Download size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
