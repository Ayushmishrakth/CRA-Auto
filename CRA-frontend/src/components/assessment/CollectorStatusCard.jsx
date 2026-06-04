import { Activity, Database, FileSearch, Gauge } from "lucide-react";

const COLLECTORS = [
  { key: "identity", label: "Identity collector", icon: Database },
  { key: "security", label: "Security collector", icon: FileSearch },
  { key: "findings", label: "Findings engine", icon: Activity },
  { key: "scoring", label: "Scoring engine", icon: Gauge },
];

export default function CollectorStatusCard({ progress = 0 }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Collector Activity</h2>
          <p>Workflow stages update as assessment progress advances.</p>
        </div>
      </div>
      <div className="collector-grid">
        {COLLECTORS.map((collector, index) => {
          const Icon = collector.icon;
          const active = progress >= index * 25;
          const complete = progress >= (index + 1) * 25;
          return (
            <article
              className={`collector-card ${active ? "active" : ""} ${complete ? "complete" : ""}`}
              key={collector.key}
            >
              <Icon size={18} />
              <div>
                <strong>{collector.label}</strong>
                <span>{complete ? "Completed" : active ? "Running" : "Waiting"}</span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
