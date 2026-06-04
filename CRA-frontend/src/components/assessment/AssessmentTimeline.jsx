import { Activity, CheckCircle2, CircleDot, XCircle } from "lucide-react";
import { formatDateTime } from "../../utils/assessmentFormatters";

const ICONS = {
  "assessment.failed": XCircle,
  "assessment.completed": CheckCircle2,
  "progress.update": Activity,
};

export default function AssessmentTimeline({ events = [], connectionStatus = "disconnected" }) {
  const visibleEvents = events.length
    ? events
    : [
        {
          id: "empty",
          type: "collector.started",
          title: "Waiting for workflow events",
          timestamp: new Date().toISOString(),
          detail: "Live assessment activity appears here.",
        },
      ];

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Live Workflow Timeline</h2>
          <p>Collector, findings, and scoring events stream in real time.</p>
        </div>
        <span className={`connection-pill ${connectionStatus}`}>{connectionStatus}</span>
      </div>
      {connectionStatus === "reconnecting" && (
        <div className="warning-banner">Live connection interrupted. Reconnecting...</div>
      )}
      <div className="timeline">
        {visibleEvents.map((event) => {
          const Icon = ICONS[event.type] || CircleDot;
          return (
            <article className="timeline-item" key={event.id}>
              <div className="timeline-icon">
                <Icon size={16} />
              </div>
              <div>
                <h3>{event.title}</h3>
                <p>{event.detail || event.type}</p>
                <time>{formatDateTime(event.timestamp)}</time>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
