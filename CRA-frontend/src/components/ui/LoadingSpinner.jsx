const SIZE_MAP = {
  sm: "w-4 h-4 border-2",
  md: "w-8 h-8 border-[3px]",
  lg: "w-12 h-12 border-4",
};

export default function LoadingSpinner({ size = "md", className = "" }) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={[
        "rounded-full border-[#E5E7EB] border-t-[#0078D4] animate-spin",
        SIZE_MAP[size] ?? SIZE_MAP.md,
        className,
      ].join(" ")}
    />
  );
}

/** Centered full-area spinner */
export function CenteredSpinner({ size = "md", label = "Loading..." }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[200px] gap-3">
      <LoadingSpinner size={size} />
      {label && <p className="text-sm text-[#6B7280]">{label}</p>}
    </div>
  );
}
