import { createContext, useContext, useState } from "react";

const WizardContext = createContext(null);

const INITIAL = {
  currentStep: 0,
  tenantInfo: {
    connected: false,
    tenantName: "",
    tenantId: "",
  },
  selectedModules: {
    identity: true,
    security: true,
    exchange: true,
    teams: true,
    sharepoint: true,
    licensing: true,
  },
};

export function WizardProvider({ children }) {
  const [state, setState] = useState(INITIAL);

  const setStep = (step) =>
    setState((p) => ({ ...p, currentStep: step }));

  const setTenantInfo = (info) =>
    setState((p) => ({ ...p, tenantInfo: { ...p.tenantInfo, ...info } }));

  const toggleModule = (key) =>
    setState((p) => ({
      ...p,
      selectedModules: {
        ...p.selectedModules,
        [key]: !p.selectedModules[key],
      },
    }));

  const resetWizard = () => setState(INITIAL);

  return (
    <WizardContext.Provider
      value={{ ...state, setStep, setTenantInfo, toggleModule, resetWizard }}
    >
      {children}
    </WizardContext.Provider>
  );
}

export function useWizard() {
  const ctx = useContext(WizardContext);
  if (!ctx) throw new Error("useWizard must be used within WizardProvider");
  return ctx;
}
