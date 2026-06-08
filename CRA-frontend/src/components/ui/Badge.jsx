const VARIANTS = {
  success: "bg-[#DFF6DD] text-[#107C10]",
  warning: "bg-[#FFF4CE] text-[#B45309]",
  danger:  "bg-[#FDE7E9] text-[#D13438]",
  info:    "bg-[#EFF6FC] text-[#0078D4]",
  purple:  "bg-[#F4EEF9] text-[#5C2D91]",
  gray:    "bg-[#F3F4F6] text-[#6B7280]",
  orange:  "bg-[#FFF4CE] text-[#FF8C00]",
};

const SIZES = {
  sm: "text-xs px-1.5 py-0.5",
  md: "text-xs px-2.5 py-1",
};

export default function Badge({ variant = "gray", size = "md", children, className = "" }) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 font-semibold rounded-full whitespace-nowrap",
        VARIANTS[variant] ?? VARIANTS.gray,
        SIZES[size] ?? SIZES.md,
        className,
      ].join(" ")}
    >
      {children}
    </span>
  );
}
