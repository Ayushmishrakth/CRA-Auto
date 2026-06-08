export default function EmptyState({ icon: Icon, title, subtitle, action, className = "" }) {
  return (
    <div className={["flex flex-col items-center justify-center py-16 text-center px-4", className].join(" ")}>
      {Icon && (
        <div className="w-16 h-16 rounded-full bg-[#F3F4F6] flex items-center justify-center mb-4">
          <Icon size={32} className="text-[#9CA3AF]" />
        </div>
      )}
      <h3 className="text-base font-semibold text-[#111827] mb-1 m-0">{title}</h3>
      {subtitle && (
        <p className="text-sm text-[#6B7280] max-w-xs mb-4 mt-1">{subtitle}</p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
