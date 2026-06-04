import { DOMAIN_KEYS, DOMAIN_LABELS } from "./assessmentTypes";

export function unwrapApiData(response) {
  return response?.data?.data ?? response?.data ?? response;
}

export function numberOrZero(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function clampPercent(value) {
  return Math.max(0, Math.min(100, numberOrZero(value)));
}

export function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString();
}

export function formatDuration(start, end) {
  if (!start) return "-";
  const startMs = new Date(start).getTime();
  const endMs = end ? new Date(end).getTime() : Date.now();
  if (Number.isNaN(startMs) || Number.isNaN(endMs) || endMs < startMs) return "-";
  const minutes = Math.max(1, Math.round((endMs - startMs) / 60000));
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

export function getScoreTone(score) {
  const value = numberOrZero(score);
  if (value >= 90) return "excellent";
  if (value >= 75) return "good";
  if (value >= 60) return "warning";
  if (value >= 40) return "risk";
  return "critical";
}

export function normalizeAssessment(raw = {}) {
  return {
    ...raw,
    id: String(raw.id ?? ""),
    tenant_id: raw.tenant_id ?? raw.tenantId ?? "",
    status: raw.status ?? "queued",
    progress_pct: clampPercent(raw.progress_pct ?? raw.progress ?? 0),
    overall_score: raw.overall_score ?? null,
    total_findings: raw.total_findings ?? 0,
    critical_findings: raw.critical_findings ?? 0,
    high_findings: raw.high_findings ?? 0,
  };
}

export function normalizeFinding(raw = {}) {
  const rawObject = raw.raw_value && typeof raw.raw_value === "object" ? raw.raw_value : {};
  const rawValue =
    typeof raw.raw_value === "string"
      ? raw.raw_value
      : JSON.stringify(raw.raw_value ?? {}, null, 2);
  return {
    ...raw,
    id: String(raw.id ?? `${raw.parameter_id}-${raw.status}`),
    parameter: raw.parameter ?? raw.parameter_name ?? String(raw.parameter_id ?? "Parameter"),
    category: raw.category ?? raw.domain ?? "Assessment",
    severity: (raw.severity ?? "info").toLowerCase(),
    status: raw.status ?? "observed",
    value: raw.evaluated_value ?? rawValue,
    actual_value: raw.actual_value ?? rawObject.actual_value ?? rawObject.evidence?.actual_value,
    expected_value: raw.expected_value ?? rawObject.expected_value,
    collector_name: raw.collector_name ?? rawObject.collector_name,
    raw_evidence_json: JSON.stringify(raw.raw_evidence_json ?? rawObject.evidence ?? rawObject.raw_response ?? {}, null, 2),
    collection_timestamp: raw.collection_timestamp ?? raw.collected_at,
    recommendation:
      raw.recommendation ??
      raw.recommendation_title ??
      "",
  };
}

export function normalizeRecommendation(raw = {}, index = 0) {
  const steps = raw.remediation_steps ?? raw.steps ?? raw.actions ?? [];
  return {
    ...raw,
    id: String(raw.id ?? raw.title ?? `recommendation-${index}`),
    title: raw.title ?? raw.name ?? "Recommendation",
    severity: (raw.severity ?? raw.priority ?? "medium").toLowerCase(),
    remediation_steps: Array.isArray(steps) ? steps : [String(steps)],
    recommendation_text: raw.recommendation_text ?? raw.text ?? raw.description ?? "",
    business_impact: raw.business_impact ?? raw.impact ?? "",
    impact: raw.impact ?? raw.business_impact ?? "",
    effort: raw.effort ?? raw.estimated_effort ?? "medium",
    priority_score: raw.priority_score == null && raw.score == null ? null : numberOrZero(raw.priority_score ?? raw.score),
  };
}

export function normalizeRuntimeEvent(raw = {}) {
  const payload = raw.payload ?? raw.event_payload ?? {};
  const eventType = raw.event ?? raw.type ?? raw.event_type ?? "progress.update";
  return {
    ...raw,
    id: String(raw.id ?? `${eventType}-${raw.timestamp ?? raw.created_at ?? Date.now()}`),
    event: eventType,
    type: eventType,
    timestamp: raw.timestamp ?? raw.created_at ?? new Date().toISOString(),
    severity: raw.severity ?? payload.severity ?? "info",
    payload,
    progress_pct: raw.progress_pct ?? payload.progress_pct,
    finding: raw.finding ?? payload.finding,
    recommendation: raw.recommendation ?? payload.recommendation,
    scores: raw.scores ?? payload.scores,
    assessment: raw.assessment ?? payload.assessment,
  };
}

export function buildDomainScores(assessment = {}, scorePayload = null) {
  const categories = scorePayload?.categories ?? {};
  return DOMAIN_KEYS.map((key) => {
    const value = categories[key] ?? assessment[`${key}_score`];
    const score = value == null ? 0 : Math.round(Number(value));
    return {
      key,
      label: DOMAIN_LABELS[key],
      score,
      status: score >= 75 ? "ready" : score >= 60 ? "watch" : "needs work",
      trend: null,
    };
  });
}

export function makeTimelineEvent(event) {
  const type = event?.type ?? event?.event ?? "progress.update";
  const payload = event?.payload ?? {};
  const labels = {
    connected: "Connected",
    "assessment.started": "Assessment started",
    "progress.update": "Progress updated",
    "collector.started": "Collector started",
    "collector.completed": "Collector completed",
    "collector.failed": "Collector failed",
    "finding.generated": "Finding generated",
    "scoring.completed": "Scoring completed",
    "recommendation.generated": "Recommendation generated",
    "assessment.completed": "Scoring complete",
    "assessment.failed": "Assessment failed",
  };
  const detail =
    event?.detail ??
    event?.message ??
    event?.collector ??
    payload.collector ??
    payload.parameter_key ??
    payload.stage ??
    payload.finding?.parameter_name ??
    payload.recommendation?.title ??
    "";
  return {
    id: event?.id ?? `${type}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    type,
    title: event?.title ?? labels[type] ?? type,
    timestamp: event?.timestamp ?? new Date().toISOString(),
    status: event?.status ?? (type.includes("failed") ? "failed" : "completed"),
    detail,
  };
}

export function buildSeverityData(findings = []) {
  const counts = findings.reduce((acc, finding) => {
    const key = (finding.severity ?? "info").toLowerCase();
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
  return ["critical", "high", "medium", "low", "info"].map((name) => ({
    name,
    value: counts[name] ?? 0,
  }));
}

export function buildScoreTrend(assessments = []) {
  return [...assessments]
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    .slice(-8)
    .map((item, index) => ({
      name: item.created_at ? new Date(item.created_at).toLocaleDateString() : `A${index + 1}`,
      score: Math.round(numberOrZero(item.overall_score)),
    }));
}
