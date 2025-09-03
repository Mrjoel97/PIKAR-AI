import './App.css'
import Pages from "@/pages/index.jsx"
import { Toaster } from "@/components/ui/toaster"
import { AuthProvider } from "@/contexts/AuthContext"
import ErrorBoundary from "@/components/ErrorBoundary"
import RouteErrorBoundary from "@/components/error/RouteErrorBoundary"
import { useEffect } from 'react'
import { securityInitService } from '@/services/securityInitService'
import { environmentConfig } from '@/config/environment'

function App() {
  useEffect(() => {
    // Initialize security services on app startup
    const initializeSecurity = async () => {
      try {
        await securityInitService.initialize({
          enableCSP: environmentConfig.getSecurityConfig().enableCSP,
          enableHSTS: environmentConfig.getSecurityConfig().enableHSTS,
          enableEncryption: true,
          enableSecureStorage: true,
          enableAuditLogging: true,
          enableErrorHandling: true,
          enableSecretsManagement: true,
          cspReportOnly: environmentConfig.isDevelopment(),
          strictMode: environmentConfig.isProduction()
        });
      } catch (error) {
        console.error('Failed to initialize security services:', error);
      }
    };

    initializeSecurity();

    // Cleanup on unmount
    return () => {
      if (process.env.NODE_ENV !== 'development') {
        securityInitService.shutdown();
      }
    };
  }, []);

  return (
    <ErrorBoundary context="app_root">
      <RouteErrorBoundary>
        <AuthProvider>
          <Pages />
          <Toaster />
        </AuthProvider>
      </RouteErrorBoundary>
    </ErrorBoundary>
  )
}

export default App