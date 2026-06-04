import { MsalProvider } from "@azure/msal-react";
import { getMsalInstance } from "./auth/msalInstance";
import { AssessmentProvider } from "./context/AssessmentContext";
import { AuthProvider } from "./context/AuthContext";
import AppErrorBoundary from "./components/AppErrorBoundary";
import AppRoutes from "./routes/AppRoutes";

export default function App() {
  return (
    <MsalProvider instance={getMsalInstance()}>
      <AuthProvider>
        <AssessmentProvider>
          <AppErrorBoundary>
            <AppRoutes />
          </AppErrorBoundary>
        </AssessmentProvider>
      </AuthProvider>
    </MsalProvider>
  );
}
