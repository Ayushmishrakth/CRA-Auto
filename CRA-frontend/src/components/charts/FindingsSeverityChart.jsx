import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function FindingsSeverityChart({ data = [] }) {
  return (
    <div className="chart-card">
      <h2>Findings Severity</h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fill: "#64748b", fontSize: 12 }} />
          <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #d9e2ef", color: "#172033" }} />
          <Bar dataKey="value" fill="#0078d4" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
