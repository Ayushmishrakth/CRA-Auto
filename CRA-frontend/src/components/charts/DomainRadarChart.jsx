import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import { buildDomainScores } from "../../utils/assessmentFormatters";

export default function DomainRadarChart({ assessment, scores }) {
  const data = buildDomainScores(assessment, scores);
  return (
    <div className="chart-card">
      <h2>Domain Coverage</h2>
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={data}>
          <PolarGrid stroke="rgba(148, 163, 184, 0.28)" />
          <PolarAngleAxis dataKey="label" tick={{ fill: "#cbd5e1", fontSize: 12 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
          <Radar
            dataKey="score"
            stroke="#3b82f6"
            fill="#3b82f6"
            fillOpacity={0.28}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
