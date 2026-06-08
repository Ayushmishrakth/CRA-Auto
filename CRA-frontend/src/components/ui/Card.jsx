export default function Card({ children, header, padding = "p-6", className = "", ...props }) {
  return (
    <div
      {...props}
      className={[
        "bg-white border border-[#E5E7EB] rounded-xl shadow-sm",
        className,
      ].join(" ")}
    >
      {header && (
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5E7EB]">
          <div>
            {header.title && (
              <h3 className="text-sm font-semibold text-[#111827] m-0 leading-tight">
                {header.title}
              </h3>
            )}
            {header.subtitle && (
              <p className="text-xs text-[#6B7280] mt-0.5 m-0">{header.subtitle}</p>
            )}
          </div>
          {header.action && <div className="flex-shrink-0">{header.action}</div>}
        </div>
      )}
      <div className={padding}>{children}</div>
    </div>
  );
}
