const STATUS_LABELS = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

export default function AssessmentStatusBadge({ status = "queued" }) {
  const normalized = String(status).toLowerCase();
  return (
    <span className={`status-badge status-${normalized}`}>
      {STATUS_LABELS[normalized] || status}
    </span>
  );
}
