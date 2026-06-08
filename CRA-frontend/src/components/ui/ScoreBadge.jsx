function scoreStyle(v) {
  if (v >= 90) return { bg: "#DFF6DD", color: "#107C10" };
  if (v >= 75) return { bg: "#EFF6FC", color: "#0078D4" };
  if (v >= 50) return { bg: "#FFF4CE", color: "#B45309" };
  return { bg: "#FDE7E9", color: "#D13438" };
}

export default function ScoreBadge({ value = 0, className = "" }) {
  const { bg, color } = scoreStyle(value);
  return (
    <span
      className={[
        "inline-flex items-center justify-center font-bold text-sm px-3 py-1 rounded-full whitespace-nowrap",
        className,
      ].join(" ")}
      style={{ backgroundColor: bg, color }}
    >
      {value}%
    </span>
  );
}
