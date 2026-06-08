import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, Plus, Eye, FileDown, Trash2, RotateCcw,
  ClipboardList, ChevronLeft, ChevronRight, X, AlertCircle,
} from "lucide-react";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import ScoreBadge from "../components/ui/ScoreBadge";
import EmptyState from "../components/ui/EmptyState";
import Modal from "../components/ui/Modal";
import { useToast } from "../context/ToastContext";
import { listAssessments, deleteAssessment, startAssessment } from "../api/assessmentApi";

const PAGE_SIZE = 10;

const STATUS_VARIANT = {
  completed: "success",
  running:   "info",
  failed:    "danger",
  queued:    "gray",
};

function fmtDate(d) {
  return new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function relTime(d) {
  const diff = Date.now() - new Date(d).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  return `${days} days ago`;
}

function SkeletonRow() {
  return (
    <tr className="border-b border-[#F3F4F6]">
      {[140, 60, 80, 70, 90, 80].map((w, i) => (
        <td key={i} className="px-4 py-3">
          <div className="skeleton h-4 rounded" style={{ width: w }} />
        </td>
      ))}
    </tr>
  );
}

export default function AssessmentsPage() {
  const navigate = useNavigate();
  const toast    = useToast();

  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [items, setItems]         = useState([]);
  const [total, setTotal]         = useState(0);
  const [search, setSearch]       = useState("");
  const [statusFilter, setStatus] = useState("all");
  const [sortBy, setSort]         = useState("newest");
  const [page, setPage]           = useState(1);
  const [deleteTarget, setDelete]   = useState(null);
  const [deleting, setDeleting]     = useState(false);
  const [rerunningId, setRerunning] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        per_page: PAGE_SIZE,
        sort: sortBy,
        ...(statusFilter !== "all" && { status: statusFilter }),
      };
      const data = await listAssessments(params);
      setItems(data?.items ?? []);
      setTotal(data?.total ?? 0);
    } catch {
      setError("Could not load assessments. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, sortBy]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Client-side search on the current page only
  const filtered = useMemo(() => {
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter((a) => (a.tenant_name ?? "").toLowerCase().includes(q));
  }, [items, search]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasFilters = search || statusFilter !== "all" || sortBy !== "newest";
  const startItem  = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const endItem    = Math.min(page * PAGE_SIZE, total);

  const clearFilters = () => {
    setSearch(""); setStatus("all"); setSort("newest"); setPage(1);
  };

  const handleRerun = async (a, e) => {
    e.stopPropagation();
    if (rerunningId) return;
    setRerunning(a.id);
    try {
      const newA = await startAssessment(a.tenant_id);
      navigate(`/assessments/${newA.id}/progress`);
    } catch {
      toast.error("Failed to start assessment. Please try again.");
      setRerunning(null);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteAssessment(deleteTarget.id);
      setItems((prev) => prev.filter((a) => a.id !== deleteTarget.id));
      setTotal((t) => t - 1);
      toast.success(`Assessment deleted for ${deleteTarget.tenant_name}`);
      setDelete(null);
    } catch {
      toast.error("Failed to delete assessment. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-[#111827] m-0">Assessments</h2>
        <Button variant="primary" onClick={() => navigate("/assessments/new")}>
          <Plus size={16} /> New Assessment
        </Button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <AlertCircle size={16} className="flex-shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={fetchData}
            className="font-semibold text-red-700 hover:text-red-900 underline whitespace-nowrap"
          >
            Retry
          </button>
        </div>
      )}

      {/* Filter bar */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-4 flex flex-wrap items-center gap-3 shadow-sm">
        {/* Search */}
        <div className="flex items-center gap-2 flex-1 min-w-[200px] h-9 px-3 border border-[#D1D5DB] rounded-lg focus-within:border-[#0078D4] focus-within:ring-1 focus-within:ring-[#0078D4] transition-colors bg-white">
          <Search size={15} className="text-[#9CA3AF] flex-shrink-0" />
          <input
            type="text"
            placeholder="Search by tenant name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 text-sm outline-none text-[#111827] placeholder-[#9CA3AF]"
          />
          {search && (
            <button onClick={() => setSearch("")}>
              <X size={14} className="text-[#9CA3AF] hover:text-[#374151]" />
            </button>
          )}
        </div>

        {/* Status */}
        <select
          value={statusFilter}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="h-9 px-3 text-sm border border-[#D1D5DB] rounded-lg bg-white text-[#374151] focus:outline-none focus:border-[#0078D4]"
        >
          <option value="all">All Status</option>
          <option value="completed">Completed</option>
          <option value="running">Running</option>
          <option value="failed">Failed</option>
          <option value="queued">Pending</option>
        </select>

        {/* Sort */}
        <select
          value={sortBy}
          onChange={(e) => { setSort(e.target.value); setPage(1); }}
          className="h-9 px-3 text-sm border border-[#D1D5DB] rounded-lg bg-white text-[#374151] focus:outline-none focus:border-[#0078D4]"
        >
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="score_desc">Score ↓</option>
          <option value="score_asc">Score ↑</option>
        </select>

        {hasFilters && (
          <button
            onClick={clearFilters}
            className="text-sm text-[#0078D4] hover:underline whitespace-nowrap"
          >
            Clear filters
          </button>
        )}
      </div>

      <p className="text-xs text-[#6B7280]">
        {search
          ? `${filtered.length} result${filtered.length !== 1 ? "s" : ""} for "${search}"`
          : `Showing ${startItem}–${endItem} of ${total} assessment${total !== 1 ? "s" : ""}`}
      </p>

      {/* Table */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E5E7EB]">
                {["Tenant", "Score", "Findings", "Status", "Date", "Actions"].map((h) => (
                  <th key={h} className="text-left text-xs font-semibold text-[#6B7280] px-4 py-3 uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
                : filtered.length === 0
                ? (
                  <tr>
                    <td colSpan={6}>
                      <EmptyState
                        icon={ClipboardList}
                        title={hasFilters ? "No assessments found" : "No assessments yet"}
                        subtitle={hasFilters ? "Try adjusting your filters." : undefined}
                        action={
                          !hasFilters
                            ? <Button variant="primary" onClick={() => navigate("/assessments/new")}>
                                <Plus size={16} /> Start First Assessment
                              </Button>
                            : null
                        }
                      />
                    </td>
                  </tr>
                )
                : filtered.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-[#F3F4F6] hover:bg-[#F8F9FA] transition-colors cursor-pointer"
                    onClick={() => navigate(`/assessments/${a.id}/results`)}
                  >
                    <td className="px-4 py-3">
                      <p className="font-semibold text-[#111827] leading-tight">{a.tenant_name}</p>
                    </td>
                    <td className="px-4 py-3">
                      {a.overall_score != null
                        ? <ScoreBadge value={a.overall_score} />
                        : <span className="text-[#9CA3AF] text-xs">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[#374151]">{a.total_findings ?? 0}</span>
                        {(a.critical_findings ?? 0) > 0 && (
                          <span className="text-xs font-semibold text-[#D13438]">
                            {a.critical_findings} critical
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={STATUS_VARIANT[a.status] ?? "gray"} className="capitalize">
                        {a.status === "queued" ? "pending" : a.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-[#374151] whitespace-nowrap">{fmtDate(a.created_at)}</p>
                      <p className="text-xs text-[#9CA3AF] mt-0.5">{relTime(a.created_at)}</p>
                    </td>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-0.5">
                        <button
                          onClick={() => navigate(`/assessments/${a.id}/results`)}
                          className="p-1.5 rounded-md text-[#6B7280] hover:bg-[#EFF6FC] hover:text-[#0078D4] transition-colors"
                          title="View results"
                        >
                          <Eye size={15} />
                        </button>
                        <button
                          disabled={a.status !== "completed"}
                          className="p-1.5 rounded-md text-[#6B7280] hover:bg-[#EFF6FC] hover:text-[#0078D4] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                          title="Download report"
                        >
                          <FileDown size={15} />
                        </button>
                        <button
                          onClick={(e) => handleRerun(a, e)}
                          disabled={!!rerunningId}
                          className="p-1.5 rounded-md text-[#6B7280] hover:bg-[#EFF6FC] hover:text-[#0078D4] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                          title="Re-run assessment"
                        >
                          <RotateCcw size={15} className={rerunningId === a.id ? "animate-spin" : ""} />
                        </button>
                        <button
                          onClick={() => setDelete(a)}
                          className="p-1.5 rounded-md text-[#6B7280] hover:bg-[#FDE7E9] hover:text-[#D13438] transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!loading && total > PAGE_SIZE && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-[#E5E7EB]">
            <p className="text-xs text-[#6B7280]">
              Showing {startItem}–{endItem} of {total} · Page {page} of {totalPages}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-md border border-[#D1D5DB] text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1.5 rounded-md border border-[#D1D5DB] text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete confirmation modal */}
      {deleteTarget && (
        <Modal
          title="Delete Assessment"
          onClose={() => !deleting && setDelete(null)}
          footer={
            <>
              <Button variant="ghost" onClick={() => setDelete(null)} disabled={deleting}>
                Cancel
              </Button>
              <Button variant="danger" loading={deleting} onClick={handleDelete}>
                Delete
              </Button>
            </>
          }
        >
          <p className="text-sm text-[#374151]">
            Delete this assessment for{" "}
            <strong>{deleteTarget.tenant_name}</strong>? This cannot be undone.
          </p>
        </Modal>
      )}
    </div>
  );
}
