import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function ScoreTrendChart({ data = [] }) {
  return (
    <div className="chart-card">
      <h2>Score Trend</h2>
      {data.length ? (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data}>
            <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 12 }} />
            <YAxis domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 12 }} />
            <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #d9e2ef", color: "#172033" }} />
            <Area
              type="monotone"
              dataKey="score"
              stroke="#0078d4"
              fill="#0078d4"
              fillOpacity={0.16}
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="empty-chart">Run assessments to build a readiness trend.</div>
      )}
    </div>
  );
}
