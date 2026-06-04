import { clampPercent } from "../../utils/assessmentFormatters";

export default function AssessmentProgress({ value = 0, compact = false }) {
  const progress = Math.round(clampPercent(value));
  return (
    <div className={compact ? "progress compact" : "progress"}>
      <div className="progress-meta">
        <span>Progress</span>
        <strong>{progress}%</strong>
      </div>
      <div className="progress-track" aria-label={`Assessment progress ${progress}%`}>
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
