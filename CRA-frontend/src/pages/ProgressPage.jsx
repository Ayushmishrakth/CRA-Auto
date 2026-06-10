import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import {
  Shield, Lock, Mail, Users, FolderOpen, CreditCard, Cloud,
  CheckCircle2, XCircle, AlertTriangle, AlertCircle,
  ChevronLeft, ArrowRight,
} from "lucide-react";
import { getAssessment, getAssessmentJob } from "../api/assessmentApi";
import { subscribeToAssessment } from "../services/websocketService";

// ── FIX 3: Backend module name → display config ──────────────
const MODULE_DISPLAY_MAP = {
  entra:      { icon: Shield,     color: "#0078D4", bg: "#EFF6FC", label: "Identity & Access"   },
  exchange:   { icon: Mail,       color: "#FF8C00", bg: "#FFF4CE", label: "Exchange Online"      },
  teams:      { icon: Users,      color: "#5C2D91", bg: "#F4EEF9", label: "Microsoft Teams"      },
  sharepoint: { icon: FolderOpen, color: "#107C10", bg: "#DFF6DD", label: "SharePoint"           },
  onedrive:   { icon: Cloud,      color: "#0078D4", bg: "#EFF6FC", label: "OneDrive"             },
  purview:    { icon: Lock,       color: "#D13438", bg: "#FDE7E9", label: "Compliance & Purview" },
  licensing:  { icon: CreditCard, color: "#0097A7", bg: "#E0F7FA", label: "Licensing"            },
};

function moduleStatusIcon(status) {
  if (status === "completed") return <CheckCircle2 size={22} className="text-[#107C10]" />;
  if (status === "failed")    return <XCircle      size={22} className="text-[#D13438]" />;
  if (status === "warning")   return <AlertTriangle size={22} className="text-[#FF8C00]" />;
  if (status === "running") {
    return (
      <div className="w-[22px] h-[22px] rounded-full border-2 border-[#E5E7EB] border-t-[#0078D4] animate-spin" />
    );
  }
  return <div className="w-[22px] h-[22px] rounded-full border-2 border-[#D1D5DB]" />;
}

const INITIAL_MODULE_STATES = () =>
  Object.fromEntries(
    Object.keys(MODULE_DISPLAY_MAP).map((key) => [
      key,
      { status: "queued", progress: 0, current_check: "Queued…" },
    ])
  );

export default function ProgressPage() {
  const { assessmentId } = useParams();
  const navigate = useNavigate();

  // FIX 1: Real tenant name
  const [tenantName, setTenantName]       = useState(null);
  const [tenantLoading, setTenantLoading] = useState(true);

  const [moduleStates, setModuleStates]     = useState(INITIAL_MODULE_STATES);
  const [overallProgress, setOverallProgress] = useState(0);
  const [complete, setComplete]             = useState(false);
  const [error, setError]                   = useState(null);
  const [countdown, setCountdown]           = useState(3);
  const [startTime]                         = useState(Date.now());
  const [elapsedDisplay, setElapsedDisplay] = useState("0:00");

  const pollRef    = useRef(null);
  const completeRef = useRef(false);

  // ── FIX 1: Load tenant name ──────────────────────────────
  useEffect(() => {
    getAssessment(assessmentId)
      .then((a) => setTenantName(a.tenant_name || a.tenant_id || "Your Assessment"))
      .catch(() => setTenantName("Your Assessment"))
      .finally(() => setTenantLoading(false));
  }, [assessmentId]);

  // Elapsed timer
  useEffect(() => {
    const t = setInterval(() => {
      const secs = Math.floor((Date.now() - startTime) / 1000);
      setElapsedDisplay(`${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`);
    }, 1000);
    return () => clearInterval(t);
  }, [startTime]);

  // ── FIX 2: WebSocket + polling fallback ──────────────────
  useEffect(() => {
    const stopPolling = () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    };

    // Apply a WS event or poll snapshot to component state
    const applyEvent = (event) => {
      if (completeRef.current) return;

      const type    = (event.type || event.event || "").toLowerCase();
      const payload = event.payload ?? {};
      const collector  = ((event.collector ?? payload.collector) || "").toLowerCase();
      const progress   = event.progress_pct ?? payload.progress_pct ?? null;
      const stageMsg   = payload.stage ?? payload.parameter_key ?? payload.detail ?? "";

      if (type.includes("assessment.completed") || type === "complete") {
        completeRef.current = true;
        setOverallProgress(100);
        setComplete(true);
        stopPolling();
        return;
      }
      if (type.includes("assessment.failed") || type === "error") {
        setError(payload.error_message || "Assessment failed. Please try again.");
        stopPolling();
        return;
      }

      if (progress != null) setOverallProgress(Math.round(progress));

      if (!collector || !MODULE_DISPLAY_MAP[collector]) return;

      setModuleStates((prev) => {
        const cur = prev[collector] ?? { status: "queued", progress: 0, current_check: "Queued…" };
        if (type.includes("collector.completed")) {
          return { ...prev, [collector]: { status: "completed", progress: 100, current_check: "Done" } };
        }
        if (type.includes("collector.failed")) {
          return { ...prev, [collector]: { ...cur, status: "failed", current_check: "Failed" } };
        }
        if (type.includes("collector.started") || type.includes("progress.update") || type.includes("collector.stdout") || type.includes("collector.warning")) {
          return {
            ...prev,
            [collector]: {
              ...cur,
              status: cur.status === "completed" ? "completed" : "running",
              progress: progress != null ? Math.round(progress) : cur.progress,
              current_check: stageMsg || cur.current_check || "Collecting…",
            },
          };
        }
        return prev;
      });
    };

    // Polling fallback — 3-second interval
    const startPolling = () => {
      if (pollRef.current || completeRef.current) return;
      pollRef.current = setInterval(async () => {
        if (completeRef.current) { stopPolling(); return; }
        try {
          const job = await getAssessmentJob(assessmentId);
          if (job.progress_pct != null) setOverallProgress(Math.round(job.progress_pct));
          const stage = (job.current_stage || "").toLowerCase();
          if (stage && MODULE_DISPLAY_MAP[stage]) {
            setModuleStates((prev) => ({
              ...prev,
              [stage]: {
                ...prev[stage],
                status: prev[stage].status === "completed" ? "completed" : "running",
                current_check: prev[stage].current_check || "Collecting…",
              },
            }));
          }
          if (job.status === "completed") {
            completeRef.current = true;
            setOverallProgress(100);
            setComplete(true);
            stopPolling();
          } else if (job.status === "failed") {
            setError(job.error_message || "Assessment failed.");
            stopPolling();
          }
        } catch { /* ignore individual poll errors */ }
      }, 3000);
    };

    // Connect WS; fall back to polling if it doesn't connect
    let wsConnected = false;
    const unsubscribe = subscribeToAssessment(assessmentId, {
      onEvent: applyEvent,
      onStatus: (status) => {
        if (status === "connected") {
          wsConnected = true;
          stopPolling();
        } else if (!wsConnected && (status === "disconnected" || status === "error" || status === "reconnecting")) {
          startPolling();
        }
      },
    });

    // Start polling immediately — WS success will cancel it
    startPolling();

    // Check current job state immediately (handles already-running or already-complete)
    getAssessmentJob(assessmentId)
      .then((job) => {
        if (completeRef.current) return;
        if (job.progress_pct != null) setOverallProgress(Math.round(job.progress_pct));
        if (job.status === "completed") {
          completeRef.current = true;
          setOverallProgress(100);
          setComplete(true);
          stopPolling();
        } else if (job.status === "failed") {
          setError(job.error_message || "Assessment failed.");
          stopPolling();
        }
      })
      .catch(() => {});

    return () => {
      unsubscribe();
      stopPolling();
    };
  }, [assessmentId]); // only re-run if assessmentId changes

  // Auto-redirect after completion
  useEffect(() => {
    if (!complete) return;
    const t = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          clearInterval(t);
          navigate(`/assessments/${assessmentId}/results`);
          return 0;
        }
        return c - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [complete, navigate, assessmentId]);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <Link to="/assessments" className="inline-flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#111827] mb-3">
          <ChevronLeft size={16} /> Assessments
        </Link>
        {tenantLoading
          ? <div className="skeleton h-7 w-48 rounded mb-1" />
          : <h2 className="text-xl font-bold text-[#111827] m-0">{tenantName}</h2>
        }
        <p className="text-sm text-[#6B7280] mt-1">
          {complete ? "Assessment complete!" : "Assessment in progress"} · Elapsed: {elapsedDisplay}
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <AlertCircle size={16} className="flex-shrink-0" />
          <span className="flex-1">{error}</span>
        </div>
      )}

      {/* Overall progress bar */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-semibold text-[#374151]">
            {complete ? "Assessment Complete!" : "Analyzing your Microsoft 365 tenant…"}
          </p>
          <span className="text-sm font-bold" style={{ color: complete ? "#107C10" : "#0078D4" }}>
            {overallProgress}%
          </span>
        </div>
        <div className="w-full rounded-full overflow-hidden" style={{ height: 12, backgroundColor: "#E5E7EB" }}>
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${overallProgress}%`, backgroundColor: complete ? "#107C10" : "#0078D4" }}
          />
        </div>

        {complete && (
          <div className="mt-4 text-center space-y-3">
            <p className="text-sm text-[#6B7280]">
              Redirecting to results in <strong className="text-[#111827]">{countdown}</strong>…
            </p>
            <button
              onClick={() => navigate(`/assessments/${assessmentId}/results`)}
              className="inline-flex items-center gap-2 text-sm font-semibold text-[#0078D4] hover:underline"
            >
              View Results Now <ArrowRight size={16} />
            </button>
          </div>
        )}
      </div>

    </div>
  );
}
