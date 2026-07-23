import { useCallback, useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  ClipboardList, CheckCircle2, Clock, Building2,
  Eye, FileDown, Plus, RotateCcw, Activity, AlertCircle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import ScoreBadge from "../components/ui/ScoreBadge";
import { getDashboardStats, listAssessments } from "../api/assessmentApi";

// ── Helpers ─────────────────────────────────────────────────
function relativeTime(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1)   return "just now";
  if (mins < 60)  return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)   return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function fmtDate(d) {
  return new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function statusBadge(status) {
  const map = {
    completed: "success",
    running:   "info",
    failed:    "danger",
    queued:    "gray",
  };
  return <Badge variant={map[status] ?? "gray"} className="capitalize">{status}</Badge>;
}

function deriveActivity(assessments) {
  return assessments.slice(0, 5).map((a, i) => {
    const name = a.tenant_name || "Unknown tenant";
    const date = a.completed_at || a.created_at;
    let action;
    if (a.status === "completed") action = `Assessment completed for ${name}`;
    else if (a.status === "running" || a.status === "queued") action = `Assessment running for ${name}`;
    else if (a.status === "failed") action = `Assessment failed for ${name}`;
    else action = `Assessment ${a.status} for ${name}`;
    return { id: i, action, time: date ? relativeTime(date) : "recently" };
  });
}

// ── Skeleton ─────────────────────────────────────────────────
function MetricSkeleton() {
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-xl p-5">
      <div className="flex items-start gap-4">
        <div className="skeleton w-11 h-11 rounded-full" />
        <div className="flex-1 space-y-2">
          <div className="skeleton h-4 w-20 rounded" />
          <div className="skeleton h-7 w-14 rounded" />
          <div className="skeleton h-3 w-28 rounded" />
        </div>
      </div>
    </div>
  );
}

// ── Metric card ───────────────────────────────────────────────
function MetricCard({ icon: Icon, iconBg, iconColor, label, value, sub, borderColor }) {
  return (
    <div
      className="bg-white border border-[#E5E7EB] rounded-xl p-5 shadow-sm flex items-start gap-4"
      style={{ borderLeft: `4px solid ${borderColor}` }}
    >
      <div
        className="w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0"
        style={{ backgroundColor: iconBg }}
      >
        <Icon size={20} style={{ color: iconColor }} />
      </div>
      <div>
        <p className="text-xs text-[#6B7280] font-medium mb-0.5">{label}</p>
        <p className="text-2xl font-bold text-[#111827] leading-tight">{value}</p>
        <p className="text-xs text-[#9CA3AF] mt-0.5">{sub}</p>
      </div>
    </div>
  );
}

// ── Main ────────────────────────────────────────────────────
export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [activity, setActivity] = useState([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, assessmentsData] = await Promise.all([
        getDashboardStats(),
        listAssessments({ per_page: 5, sort: "newest" }),
      ]);
      setStats(statsData);
      const items = assessmentsData?.items ?? [];
      setRecent(items);
      setActivity(deriveActivity(items));
    } catch {
      setError("Could not load dashboard data. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const METRICS = stats
    ? [
        {
          icon: ClipboardList, iconBg: "#EFF6FC", iconColor: "#0078D4",
          label: "Total Assessments", value: stats.total_assessments, sub: "All time",
          borderColor: "#0078D4",
        },
        {
          icon: CheckCircle2, iconBg: "#DFF6DD", iconColor: "#107C10",
          label: "Completed", value: stats.completed_assessments, sub: "Successfully completed",
          borderColor: "#107C10",
        },
        {
          icon: Clock, iconBg: "#FFF4CE", iconColor: "#FF8C00",
          label: "In Progress", value: stats.in_progress_assessments, sub: "Currently running",
          borderColor: "#FF8C00",
        },
        {
          icon: Building2, iconBg: "#F4EEF9", iconColor: "#5C2D91",
          label: "Customers", value: stats.connected_tenants, sub: "Tenants connected",
          borderColor: "#5C2D91",
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div>
        <h2 className="text-xl font-bold text-[#111827] m-0">
          {getGreeting()}{user?.display_name ? `, ${user.display_name.split(" ")[0]}` : ""} 👋
        </h2>
        <p className="text-sm text-[#6B7280] mt-1">Here's what's happening with your assessments.</p>
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

      {/* ── Metric cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => <MetricSkeleton key={i} />)
          : METRICS.map((m) => <MetricCard key={m.label} {...m} />)
        }
      </div>

      {/* ── Bottom two columns ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">

        {/* Recent assessments */}
        <Card
          header={{
            title: "Recent Assessments",
            action: (
              <Link to="/assessments" className="text-xs font-semibold text-[#0078D4] hover:underline">
                View all →
              </Link>
            ),
          }}
          padding="p-0"
        >
          {loading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex gap-3 items-center">
                  <div className="skeleton h-4 flex-1 rounded" />
                  <div className="skeleton h-4 w-16 rounded" />
                  <div className="skeleton h-4 w-20 rounded" />
                </div>
              ))}
            </div>
          ) : recent.length === 0 ? (
            <div className="p-8 text-center text-sm text-[#6B7280]">
              No assessments yet.{" "}
              <button onClick={() => navigate("/assessments/new")} className="text-[#0078D4] hover:underline font-semibold">
                Run your first assessment →
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#E5E7EB]">
                    {["Tenant", "Score", "Status", "Date", "Actions"].map((h) => (
                      <th key={h} className="text-left text-xs font-semibold text-[#6B7280] px-4 py-3 uppercase tracking-wide">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recent.map((a) => (
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
                          : <span className="text-[#9CA3AF]">—</span>}
                      </td>
                      <td className="px-4 py-3">{statusBadge(a.status)}</td>
                      <td className="px-4 py-3 text-[#6B7280] text-xs">{fmtDate(a.completed_at || a.created_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => { e.stopPropagation(); navigate(`/assessments/${a.id}/results`); }}
                            className="p-1.5 rounded-md text-[#6B7280] hover:bg-[#EFF6FC] hover:text-[#0078D4] transition-colors"
                            title="View results"
                          >
                            <Eye size={15} />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); }}
                            className="p-1.5 rounded-md text-[#6B7280] hover:bg-[#EFF6FC] hover:text-[#0078D4] transition-colors disabled:opacity-30"
                            title="Download report"
                            disabled={a.status !== "completed"}
                          >
                            <FileDown size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Quick actions + activity */}
        <div className="space-y-4">
          <Card header={{ title: "Quick Actions" }}>
            <div className="space-y-2">
              <Button
                variant="primary"
                fullWidth
                onClick={() => navigate("/assessments/new")}
                className="justify-start gap-3"
              >
                <Plus size={16} />
                New Assessment
              </Button>
              <Button
                variant="secondary"
                fullWidth
                onClick={() => navigate("/assessments/new")}
                className="justify-start gap-3"
              >
                <RotateCcw size={16} />
                Re-run Last Assessment
              </Button>
            </div>
          </Card>

          <Card header={{ title: "Recent Activity" }}>
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex gap-2">
                    <div className="skeleton w-6 h-6 rounded-full flex-shrink-0" />
                    <div className="flex-1 space-y-1">
                      <div className="skeleton h-3 w-full rounded" />
                      <div className="skeleton h-2 w-16 rounded" />
                    </div>
                  </div>
                ))}
              </div>
            ) : activity.length === 0 ? (
              <p className="text-xs text-[#9CA3AF] text-center py-2">No recent activity.</p>
            ) : (
              <ul className="space-y-3">
                {activity.map((a) => (
                  <li key={a.id} className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#EFF6FC] flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Activity size={12} className="text-[#0078D4]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-[#374151] leading-snug">{a.action}</p>
                      <p className="text-xs text-[#9CA3AF] mt-0.5">{a.time}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
