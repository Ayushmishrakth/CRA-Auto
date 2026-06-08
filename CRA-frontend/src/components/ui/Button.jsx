import { Loader2 } from "lucide-react";

const VARIANTS = {
  primary:   "bg-[#0078D4] text-white border-transparent hover:bg-[#005A9E] active:bg-[#004E8C]",
  secondary: "bg-white text-[#374151] border-[#D1D5DB] hover:border-[#0078D4] hover:text-[#0078D4]",
  danger:    "bg-[#D13438] text-white border-transparent hover:bg-[#B02428]",
  ghost:     "bg-transparent text-[#6B7280] border-transparent hover:bg-[#F3F4F6] hover:text-[#111827]",
};

const SIZES = {
  sm: "px-3 py-1.5 text-xs h-8 rounded-md",
  md: "px-4 py-2 text-sm h-9 rounded-md",
  lg: "px-5 py-2.5 text-sm h-11 rounded-lg",
};

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  fullWidth = false,
  children,
  className = "",
  ...props
}) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={[
        "inline-flex items-center justify-center gap-2 font-semibold border",
        "transition-colors cursor-pointer select-none",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0078D4] focus-visible:ring-offset-2",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        VARIANTS[variant] ?? VARIANTS.primary,
        SIZES[size] ?? SIZES.md,
        fullWidth ? "w-full" : "",
        className,
      ].join(" ")}
    >
      {loading && <Loader2 size={14} className="animate-spin flex-shrink-0" />}
      {children}
    </button>
  );
}
