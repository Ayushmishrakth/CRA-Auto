import { RadialBar, RadialBarChart, ResponsiveContainer } from "recharts";
import { getScoreTone, numberOrZero } from "../../utils/assessmentFormatters";

export default function ReadinessRadialChart({ score = 0 }) {
  const value = Math.round(numberOrZero(score));
  return (
    <div className={`chart-card radial-card tone-${getScoreTone(value)}`}>
      <ResponsiveContainer width="100%" height={240}>
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="68%"
          outerRadius="92%"
          barSize={16}
          data={[{ name: "Readiness", value, fill: "var(--score-color)" }]}
          startAngle={90}
          endAngle={-270}
        >
          <RadialBar dataKey="value" cornerRadius={20} background />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="radial-center">
        <strong>{value}</strong>
        <span>Overall readiness</span>
      </div>
    </div>
  );
}
