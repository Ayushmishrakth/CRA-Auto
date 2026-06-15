import { useEffect } from "react";

export default function TenantDeploymentSuccessPage() {
  useEffect(() => {
    // Close the popup window that was opened for consent
    window.close();
  }, []);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="text-center">
        <p className="text-gray-600">Permission granted. Closing...</p>
      </div>
    </div>
  );
}
