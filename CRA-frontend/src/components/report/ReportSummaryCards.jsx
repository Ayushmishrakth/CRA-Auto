export default function ReportSummaryCards({ summary = {} }) {
  const safeSummary = summary ?? {};
  return (
    <section className="metric-grid dashboard-metrics">
      <article className="metric-card">
        <span>Readiness</span>
        <strong>{safeSummary.overall_readiness ?? 0}%</strong>
      </article>
      <article className="metric-card">
        <span>Status</span>
        <strong className="small-metric">{safeSummary.readiness_status ?? "-"}</strong>
      </article>
      <article className="metric-card">
        <span>Pass / Fail</span>
        <strong>{safeSummary.pass_total ?? 0} / {safeSummary.fail_total ?? 0}</strong>
      </article>
      <article className="metric-card">
        <span>Critical / High</span>
        <strong>{safeSummary.critical_findings ?? 0} / {safeSummary.high_findings ?? 0}</strong>
      </article>
    </section>
  );
}
