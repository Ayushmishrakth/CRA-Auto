import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  useRef,
} from "react";
import {
  getAssessment,
  getAssessmentEvents,
  getAssessmentFindings,
  getAssessmentJob,
  getAssessmentRecommendations,
  getAssessmentScore,
  getTenantAssessments,
  startAssessment as startAssessmentApi,
} from "../api/assessmentApi";
import { subscribeToAssessment } from "../services/websocketService";
import {
  makeTimelineEvent,
  normalizeAssessment,
  normalizeFinding,
  normalizeRecommendation,
  normalizeRuntimeEvent,
} from "../utils/assessmentFormatters";
import { extractApiError } from "../utils/apiErrors";
import { publishBackendError } from "../utils/backendErrors";

const AssessmentContext = createContext(null);

const initialState = {
  assessments: [],
  activeAssessment: null,
  findings: [],
  recommendations: [],
  scores: null,
  runtimeJob: null,
  executionEvents: [],
  timelineEvents: [],
  websocketStatus: "disconnected",
  progress: 0,
  loading: false,
  error: null,
};

function reducer(state, action) {
  switch (action.type) {
    case "loading":
      return { ...state, loading: action.value, error: action.value ? null : state.error };
    case "loadingActive":
      return {
        ...state,
        activeAssessment: null,
        findings: [],
        recommendations: [],
        scores: null,
        runtimeJob: null,
        executionEvents: [],
        timelineEvents: [],
        progress: 0,
        loading: true,
        error: null,
      };
    case "error":
      return { ...state, loading: false, error: action.error };
    case "setAssessments":
      return { ...state, assessments: action.assessments, loading: false, error: null };
    case "setActive":
      return {
        ...state,
        activeAssessment: action.assessment,
        progress: action.assessment?.progress_pct ?? 0,
        loading: false,
        error: null,
      };
    case "setFindings":
      return { ...state, findings: action.findings };
    case "appendFinding":
      if (state.findings.some((finding) => finding.id === action.finding.id)) return state;
      return { ...state, findings: [action.finding, ...state.findings] };
    case "setRecommendations":
      return { ...state, recommendations: action.recommendations };
    case "setScores":
      return { ...state, scores: action.scores };
    case "setJob":
      return { ...state, runtimeJob: action.job };
    case "setEvents":
      return {
        ...state,
        executionEvents: action.events,
        timelineEvents: action.events.map(makeTimelineEvent).slice(0, 40),
      };
    case "appendEvent":
      if (state.executionEvents.some((event) => event.id === action.event.id)) return state;
      return { ...state, executionEvents: [action.event, ...state.executionEvents].slice(0, 120) };
    case "websocketStatus":
      return { ...state, websocketStatus: action.status };
    case "updateProgress":
      return {
        ...state,
        progress: action.progress,
        activeAssessment: state.activeAssessment
          ? { ...state.activeAssessment, progress_pct: action.progress }
          : state.activeAssessment,
      };
    case "appendTimeline":
      if (state.timelineEvents.some((event) => event.id === action.event.id)) return state;
      return {
        ...state,
        timelineEvents: [action.event, ...state.timelineEvents].slice(0, 40),
      };
    case "appendRecommendation":
      if (state.recommendations.some((item) => item.id === action.recommendation.id)) return state;
      return {
        ...state,
        recommendations: [action.recommendation, ...state.recommendations],
      };
    case "resetActive":
      return {
        ...state,
        activeAssessment: null,
        findings: [],
        recommendations: [],
        scores: null,
        runtimeJob: null,
        executionEvents: [],
        timelineEvents: [],
        progress: 0,
      };
    case "resetTenant":
      return {
        ...state,
        assessments: state.assessments.filter((item) => item.tenant_id !== action.tenantId),
        activeAssessment:
          state.activeAssessment?.tenant_id === action.tenantId ? null : state.activeAssessment,
        findings: state.activeAssessment?.tenant_id === action.tenantId ? [] : state.findings,
        recommendations: state.activeAssessment?.tenant_id === action.tenantId ? [] : state.recommendations,
        scores: state.activeAssessment?.tenant_id === action.tenantId ? null : state.scores,
        runtimeJob: state.activeAssessment?.tenant_id === action.tenantId ? null : state.runtimeJob,
        executionEvents: state.activeAssessment?.tenant_id === action.tenantId ? [] : state.executionEvents,
        timelineEvents: state.activeAssessment?.tenant_id === action.tenantId ? [] : state.timelineEvents,
        progress: state.activeAssessment?.tenant_id === action.tenantId ? 0 : state.progress,
        error: null,
      };
    default:
      return state;
  }
}

export function AssessmentProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const unsubscribeRef = useRef(null);

  const fetchTenantAssessments = useCallback(async (tenantId, params = {}) => {
    dispatch({ type: "loading", value: true });
    try {
      const assessments = await getTenantAssessments(tenantId, params);
      dispatch({ type: "setAssessments", assessments });
      return assessments;
    } catch (err) {
      dispatch({ type: "error", error: extractApiError(err) });
      return [];
    }
  }, []);

  const fetchAssessment = useCallback(async (assessmentId) => {
    dispatch({ type: "loadingActive" });
    try {
      const assessment = await getAssessment(assessmentId);
      const [findings, recommendations, scores, events, job] = await Promise.all([
        getAssessmentFindings(assessmentId, { limit: 100 }).catch((err) => {
          console.error("ASSESSMENT_FINDINGS_API_ERROR", err.response?.data || err.message);
          return [];
        }),
        getAssessmentRecommendations(assessmentId).catch((err) => {
          console.error("ASSESSMENT_RECOMMENDATIONS_API_ERROR", err.response?.data || err.message);
          return [];
        }),
        getAssessmentScore(assessmentId).catch((err) => {
          console.error("ASSESSMENT_SCORE_API_ERROR", err.response?.data || err.message);
          return null;
        }),
        getAssessmentEvents(assessmentId, { limit: 100 }).catch((err) => {
          console.error("ASSESSMENT_EVENTS_API_ERROR", err.response?.data || err.message);
          return [];
        }),
        getAssessmentJob(assessmentId).catch((err) => {
          console.error("ASSESSMENT_JOB_API_ERROR", err.response?.data || err.message);
          return null;
        }),
      ]);
      dispatch({ type: "setActive", assessment });
      dispatch({ type: "setFindings", findings });
      dispatch({ type: "setRecommendations", recommendations });
      dispatch({ type: "setScores", scores });
      dispatch({ type: "setEvents", events });
      dispatch({ type: "setJob", job });
      return assessment;
    } catch (err) {
      dispatch({ type: "error", error: extractApiError(err) });
      return null;
    }
  }, []);

  const startAssessment = useCallback(async (tenantId) => {
    dispatch({ type: "loading", value: true });
    try {
      const assessment = await startAssessmentApi(tenantId);
      dispatch({ type: "setActive", assessment });
      dispatch({ type: "setJob", job: assessment.job_id ? { id: assessment.job_id, status: "queued" } : null });
      dispatch({ type: "appendTimeline", event: makeTimelineEvent({ type: "assessment.started" }) });
      return assessment;
    } catch (err) {
      dispatch({ type: "error", error: extractApiError(err) });
      throw err;
    }
  }, []);

  const updateProgress = useCallback((progress) => {
    dispatch({ type: "updateProgress", progress });
  }, []);

  const clearTenantAssessments = useCallback((tenantId) => {
    unsubscribeRef.current?.();
    dispatch({ type: "resetTenant", tenantId });
  }, []);

  const appendFinding = useCallback((finding) => {
    dispatch({ type: "appendFinding", finding: normalizeFinding(finding) });
  }, []);

  const appendTimelineEvent = useCallback((event) => {
    const normalized = normalizeRuntimeEvent(event);
    dispatch({ type: "appendEvent", event: normalized });
    dispatch({ type: "appendTimeline", event: makeTimelineEvent(normalized) });
  }, []);

  const subscribeAssessment = useCallback((assessmentId) => {
    unsubscribeRef.current?.();
    dispatch({ type: "websocketStatus", status: "connecting" });
    unsubscribeRef.current = subscribeToAssessment(assessmentId, {
      onStatus: (status) => dispatch({ type: "websocketStatus", status }),
      onEvent: (event) => {
        const normalized = normalizeRuntimeEvent(event);
        const eventType = normalized.type ?? normalized.event;
        const payload = normalized.payload ?? {};
        appendTimelineEvent(normalized);
        if (eventType === "progress.update") {
          updateProgress(normalized.progress_pct ?? payload.progress_pct ?? 0);
        }
        if (eventType === "finding.generated" && normalized.finding) {
          appendFinding(normalized.finding);
        }
        if (eventType === "recommendation.generated" && normalized.recommendation) {
          dispatch({
            type: "appendRecommendation",
            recommendation: normalizeRecommendation(normalized.recommendation),
          });
        }
        if (eventType === "scoring.completed" && normalized.scores) {
          dispatch({ type: "setScores", scores: normalized.scores });
        }
        if (eventType === "assessment.completed" && normalized.assessment) {
          dispatch({ type: "setActive", assessment: normalizeAssessment(normalized.assessment) });
          updateProgress(100);
        }
        if (eventType === "assessment.failed") {
          publishBackendError({
            source: "assessment-runtime",
            message: payload.error || normalized.error || "Assessment failed in backend runtime",
            eventType,
            parameterKey: payload.parameter_key,
            parameterName: payload.parameter_name,
            collector: payload.collector,
            exceptionType: payload.exception_type,
            raw: normalized,
          });
          dispatch({ type: "setJob", job: { id: payload.job_id, status: "failed", error_message: payload.error } });
        }
        if (
          eventType !== "assessment.failed" &&
          (String(eventType || "").toLowerCase().includes("failed") ||
            String(eventType || "").toLowerCase().includes("error") ||
            normalized.status === "failed" ||
            payload.error ||
            payload.error_message)
        ) {
          publishBackendError({
            source: "assessment-runtime",
            message: payload.error || payload.error_message || normalized.message || "Backend runtime error",
            eventType,
            script: payload.script || payload.script_path,
            parameterKey: payload.parameter_key,
            parameterName: payload.parameter_name,
            collector: payload.collector,
            exceptionType: payload.exception_type,
            raw: normalized,
          });
        }
      },
    });
    return unsubscribeRef.current;
  }, [appendFinding, appendTimelineEvent, updateProgress]);

  const value = useMemo(
    () => ({
      ...state,
      fetchTenantAssessments,
      fetchAssessment,
      startAssessment,
      subscribeAssessment,
      updateProgress,
      clearTenantAssessments,
      appendFinding,
      appendTimelineEvent,
    }),
    [
      state,
      fetchTenantAssessments,
      fetchAssessment,
      startAssessment,
      subscribeAssessment,
      updateProgress,
      clearTenantAssessments,
      appendFinding,
      appendTimelineEvent,
    ]
  );

  return <AssessmentContext.Provider value={value}>{children}</AssessmentContext.Provider>;
}

export function useAssessments() {
  const context = useContext(AssessmentContext);
  if (!context) {
    throw new Error("useAssessments must be used within AssessmentProvider");
  }
  return context;
}
