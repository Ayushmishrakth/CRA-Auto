import {
  Activity,
  CheckCircle2,
  Clock3,
  DatabaseZap,
  RotateCw,
  ServerCog,
  TerminalSquare,
  XCircle,
} from "lucide-react";
import { formatDateTime } from "../../utils/assessmentFormatters";

const EVENT_ICON = {
  "assessment.started": ServerCog,
  "collector.started": DatabaseZap,
  "collector.stdout": TerminalSquare,
  "collector.warning": Activity,
  "collector.completed": CheckCircle2,
  "collector.failed": XCircle,
  "collector.timeout": Clock3,
  "finding.generated": Activity,
  "scoring.completed": CheckCircle2,
  "recommendation.generated": TerminalSquare,
  "assessment.completed": CheckCircle2,
  "assessment.failed": XCircle,
};

function eventLabel(type) {
  return String(type || "runtime.event").replaceAll(".", " ");
}

export default function AssessmentExecutionPanel({
  job,
  events = [],
  connectionStatus = "disconnected",
}) {
  const collectorEvents = events.filter((event) => event.type?.startsWith("collector."));
  const liveEvents = events.slice(0, 14);
  const retryEvents = events.filter(
    (event) => event.payload?.retry || event.payload?.throttled || event.payload?.retries > 0
  );
  const timeoutEvents = events.filter((event) => event.type === "collector.timeout");
  const stdoutEvents = events.filter((event) => event.type === "collector.stdout");
  const failureEvents = events.filter((event) => event.type === "collector.failed");
  const metadata = job?.metadata ?? {};

  return (
    <section className="panel execution-panel">
      <div className="panel-header">
        <div>
          <h2>Runtime Execution</h2>
          <p>Worker orchestration, collector activity, and persisted runtime events.</p>
        </div>
        <span className={`connection-pill ${connectionStatus}`}>{connectionStatus}</span>
      </div>

      <div className="execution-summary">
        <article>
          <span>Job status</span>
          <strong>{job?.status ?? "queued"}</strong>
        </article>
        <article>
          <span>Stage</span>
          <strong>{job?.current_stage ?? "queued"}</strong>
        </article>
        <article>
          <span>Worker</span>
          <strong className="mono">{job?.worker_id ?? "-"}</strong>
        </article>
        <article>
          <span>Runtime</span>
          <strong>{metadata.runtime ?? "phase7b_powershell"}</strong>
        </article>
        <article>
          <span>Collector failures</span>
          <strong>{metadata.collector_failures ?? failureEvents.length}</strong>
        </article>
        <article>
          <span>Timeouts</span>
          <strong>{metadata.collector_timeouts ?? timeoutEvents.length}</strong>
        </article>
        <article>
          <span>Retries</span>
          <strong>{metadata.collector_retries ?? retryEvents.length}</strong>
        </article>
        <article>
          <span>PS duration</span>
          <strong>{metadata.collector_duration_ms ? `${metadata.collector_duration_ms}ms` : "-"}</strong>
        </article>
      </div>

      {job?.error_message && <div className="error-banner">{job.error_message}</div>}

      <div className="runtime-grid">
        <div className="runtime-column">
          <div className="runtime-column-title">
            <DatabaseZap size={16} />
            <span>Collectors</span>
          </div>
          {collectorEvents.length === 0 && (
            <p className="muted-text">Collector events will appear when the worker starts.</p>
          )}
          {collectorEvents.slice(0, 8).map((event) => {
            const Icon = EVENT_ICON[event.type] || Clock3;
            return (
              <article className="runtime-event" key={event.id}>
                <Icon size={16} />
                <div>
                  <strong>{event.payload?.collector ?? event.payload?.parameter_key ?? eventLabel(event.type)}</strong>
                  <span>
                    {eventLabel(event.type)}
                    {event.payload?.duration_ms ? ` · ${event.payload.duration_ms}ms` : ""}
                    {event.payload?.exit_code != null ? ` · exit ${event.payload.exit_code}` : ""}
                  </span>
                </div>
                <time>{formatDateTime(event.timestamp)}</time>
              </article>
            );
          })}
        </div>

        <div className="runtime-column">
          <div className="runtime-column-title">
            <RotateCw size={16} />
            <span>Retries & throttling</span>
          </div>
          {retryEvents.length === 0 && <p className="muted-text">No retry or throttling events recorded.</p>}
          {retryEvents.slice(0, 6).map((event) => (
            <article className="runtime-event" key={event.id}>
              <RotateCw size={16} />
              <div>
                <strong>{event.payload?.parameter_key ?? eventLabel(event.type)}</strong>
                <span>
                  {event.payload?.retry ? "Retry scheduled" : "Retry telemetry"}
                  {event.payload?.retries ? ` · ${event.payload.retries} retries` : ""}
                  {event.payload?.attempts ? ` · ${event.payload.attempts} attempts` : ""}
                </span>
              </div>
              <time>{formatDateTime(event.timestamp)}</time>
            </article>
          ))}
        </div>
      </div>

      {stdoutEvents.length > 0 && (
        <div className="runtime-column runtime-log">
          <div className="runtime-column-title">
            <TerminalSquare size={16} />
            <span>PowerShell stdout</span>
          </div>
          {stdoutEvents.slice(0, 5).map((event) => (
            <article className="runtime-event stdout-event" key={event.id}>
              <TerminalSquare size={16} />
              <div>
                <strong>{event.payload?.parameter_key ?? event.payload?.collector ?? "collector.stdout"}</strong>
                <code>{event.payload?.stdout_preview ?? "-"}</code>
              </div>
              <time>{formatDateTime(event.timestamp)}</time>
            </article>
          ))}
        </div>
      )}

      <div className="runtime-column runtime-log">
        <div className="runtime-column-title">
          <ServerCog size={16} />
          <span>Execution log</span>
        </div>
        {liveEvents.length === 0 && <p className="muted-text">Waiting for runtime events.</p>}
        {liveEvents.map((event) => {
          const Icon = EVENT_ICON[event.type] || Activity;
          return (
            <article className="runtime-event" key={event.id}>
              <Icon size={16} />
              <div>
                <strong>{eventLabel(event.type)}</strong>
                <span>
                  {event.payload?.stage ??
                    event.payload?.parameter_key ??
                    event.payload?.finding?.parameter_name ??
                    event.payload?.recommendation?.title ??
                    event.severity}
                </span>
              </div>
              <time>{formatDateTime(event.timestamp)}</time>
            </article>
          );
        })}
      </div>
    </section>
  );
}
