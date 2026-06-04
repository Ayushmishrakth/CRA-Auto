import { getScoreTone } from "../../utils/assessmentFormatters";

export default function ScoreCard({ label, value, icon: Icon, trend, status }) {
  const score = Math.round(Number(value) || 0);
  return (
    <article className={`score-card tone-${getScoreTone(score)}`}>
      <div className="score-card-icon">{Icon ? <Icon size={20} /> : null}</div>
      <div>
        <span>{label}</span>
        <strong>{score}</strong>
        <p>{trend ? `${status} · ${trend}` : status}</p>
      </div>
    </article>
  );
}
