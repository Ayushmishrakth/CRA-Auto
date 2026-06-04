export default function ReportStatusBadge({ status = "not_generated" }) {
  const normalized = String(status || "not_generated").toLowerCase();
  const tone = ["generation_failed", "failed"].includes(normalized)
    ? "critical"
    : normalized === "generated"
      ? "low"
      : "info";
  return <span className={`status-pill severity-${tone}`}>{normalized.replaceAll("_", " ")}</span>;
}
