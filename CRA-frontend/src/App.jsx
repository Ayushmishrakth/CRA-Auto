import { MsalProvider } from "@azure/msal-react";
import { getMsalInstance } from "./auth/msalInstance";
import { AssessmentProvider } from "./context/AssessmentContext";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import AppErrorBoundary from "./components/AppErrorBoundary";
import BackendErrorToast from "./components/BackendErrorToast";
import ToastContainer from "./components/ui/Toast";
import AppRoutes from "./routes/AppRoutes";

export default function App() {
  return (
    <MsalProvider instance={getMsalInstance()}>
      <AuthProvider>
        <AssessmentProvider>
          <ToastProvider>
            <AppErrorBoundary>
              <AppRoutes />
              <BackendErrorToast />
              <ToastContainer />
            </AppErrorBoundary>
          </ToastProvider>
        </AssessmentProvider>
      </AuthProvider>
    </MsalProvider>
  );
}
