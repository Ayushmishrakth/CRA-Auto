import { Check } from "lucide-react";

export default function StepIndicator({ steps = [], currentStep = 0 }) {
  return (
    <div className="flex items-start w-full">
      {steps.map((step, i) => {
        const done   = i < currentStep;
        const active = i === currentStep;
        const future = i > currentStep;

        return (
          <div key={step} className="flex items-start flex-1 last:flex-none">
            {/* Step circle + label */}
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={[
                  "w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all",
                  done   ? "bg-[#0078D4] text-white" : "",
                  active ? "bg-[#0078D4] text-white ring-4 ring-[#EFF6FC]" : "",
                  future ? "bg-white border-2 border-[#D1D5DB] text-[#9CA3AF]" : "",
                ].join(" ")}
              >
                {done ? <Check size={15} strokeWidth={3} /> : i + 1}
              </div>
              <span
                className={[
                  "text-xs font-medium whitespace-nowrap",
                  active ? "text-[#0078D4]" : future ? "text-[#9CA3AF]" : "text-[#374151]",
                ].join(" ")}
              >
                {step}
              </span>
            </div>

            {/* Connector line */}
            {i < steps.length - 1 && (
              <div
                className={[
                  "flex-1 h-0.5 mx-2 mt-4 transition-colors",
                  done ? "bg-[#0078D4]" : "bg-[#E5E7EB]",
                ].join(" ")}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
