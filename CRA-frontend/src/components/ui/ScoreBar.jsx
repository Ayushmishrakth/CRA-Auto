function scoreColor(v) {
  if (v >= 90) return "#107C10";
  if (v >= 75) return "#0078D4";
  if (v >= 50) return "#FF8C00";
  return "#D13438";
}

export default function ScoreBar({ value = 0, height = 8, className = "" }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div
      className={["w-full bg-[#E5E7EB] rounded-full overflow-hidden", className].join(" ")}
      style={{ height }}
    >
      <div
        style={{ width: `${pct}%`, backgroundColor: scoreColor(pct), height: "100%" }}
        className="rounded-full transition-all duration-500"
      />
    </div>
  );
}
