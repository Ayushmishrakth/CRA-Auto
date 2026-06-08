import { createPortal } from "react-dom";
import { X, CheckCircle2, AlertCircle, Info } from "lucide-react";
import { useToastState } from "../../context/ToastContext";

const CONFIG = {
  success: {
    icon: CheckCircle2,
    iconClass: "text-[#107C10]",
    bar: "border-l-4 border-[#107C10] bg-white",
  },
  error: {
    icon: AlertCircle,
    iconClass: "text-[#D13438]",
    bar: "border-l-4 border-[#D13438] bg-white",
  },
  info: {
    icon: Info,
    iconClass: "text-[#0078D4]",
    bar: "border-l-4 border-[#0078D4] bg-white",
  },
};

function Toast({ id, message, type, onDismiss }) {
  const cfg = CONFIG[type] ?? CONFIG.info;
  const Icon = cfg.icon;

  return (
    <div
      className={[
        "flex items-start gap-3 p-4 rounded-lg shadow-md min-w-[280px] max-w-sm",
        cfg.bar,
      ].join(" ")}
      role="alert"
    >
      <Icon size={18} className={["mt-0.5 flex-shrink-0", cfg.iconClass].join(" ")} />
      <p className="flex-1 text-sm text-[#111827] font-medium leading-snug">{message}</p>
      <button
        onClick={() => onDismiss(id)}
        className="flex-shrink-0 text-[#9CA3AF] hover:text-[#374151] transition-colors"
        aria-label="Dismiss"
      >
        <X size={16} />
      </button>
    </div>
  );
}

export default function ToastContainer() {
  const { toasts, dismiss } = useToastState();
  if (!toasts.length) return null;

  return createPortal(
    <div
      className="fixed bottom-6 right-6 z-50 flex flex-col gap-2"
      aria-live="polite"
      aria-atomic="false"
    >
      {toasts.map((t) => (
        <Toast key={t.id} {...t} onDismiss={dismiss} />
      ))}
    </div>,
    document.body
  );
}
