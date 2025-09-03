import React from 'react';
import { AlertTriangle, RefreshCw, Home, Bug, Copy, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { auditService } from '@/services/auditService';
import { toast } from 'sonner';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      errorId: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // In production, you would send this to your error reporting service
    this.logErrorToService(error, errorInfo);
  }

  logErrorToService = (error, errorInfo) => {
    try {
      // Enhanced error data collection
      const errorData = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        errorId: this.state.errorId,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
        userId: this.props.userId || 'anonymous',
        errorType: error.name || 'UnknownError',
        severity: this.getErrorSeverity(error),
        context: this.props.context || 'unknown',
        userActions: this.getUserActions(),
        browserInfo: this.getBrowserInfo(),
        performanceMetrics: this.getPerformanceMetrics()
      };

      // Log to audit service
      auditService.logSystem.error(error, 'error_boundary', {
        errorId: this.state.errorId,
        componentStack: errorInfo.componentStack,
        context: this.props.context,
        severity: errorData.severity
      });

      // Send to external error reporting service in production
      if (process.env.NODE_ENV === 'production') {
        this.sendToErrorReportingService(errorData);
      }

      // Store error locally for debugging
      this.storeErrorLocally(errorData);

    } catch (loggingError) {
      console.error('Failed to log error:', loggingError);
      // Fallback logging
      console.error('Original error:', error, errorInfo);
    }
  };

  // Helper methods for enhanced error logging
  getErrorSeverity = (error) => {
    if (error.name === 'ChunkLoadError' || error.message.includes('Loading chunk')) {
      return 'medium';
    }
    if (error.name === 'TypeError' || error.name === 'ReferenceError') {
      return 'high';
    }
    if (error.message.includes('Network Error') || error.message.includes('fetch')) {
      return 'medium';
    }
    return 'high';
  };

  getUserActions = () => {
    // Get recent user actions from session storage or state management
    try {
      const actions = JSON.parse(sessionStorage.getItem('user_actions') || '[]');
      return actions.slice(-5); // Last 5 actions
    } catch {
      return [];
    }
  };

  getBrowserInfo = () => {
    return {
      userAgent: navigator.userAgent,
      language: navigator.language,
      platform: navigator.platform,
      cookieEnabled: navigator.cookieEnabled,
      onLine: navigator.onLine,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      },
      screen: {
        width: window.screen.width,
        height: window.screen.height,
        colorDepth: window.screen.colorDepth
      }
    };
  };

  getPerformanceMetrics = () => {
    if (window.performance && window.performance.timing) {
      const timing = window.performance.timing;
      return {
        loadTime: timing.loadEventEnd - timing.navigationStart,
        domReady: timing.domContentLoadedEventEnd - timing.navigationStart,
        firstPaint: timing.responseStart - timing.navigationStart
      };
    }
    return {};
  };

  sendToErrorReportingService = async (errorData) => {
    try {
      await fetch('/api/errors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(errorData)
      });
    } catch (err) {
      console.error('Failed to send error to reporting service:', err);
    }
  };

  storeErrorLocally = (errorData) => {
    try {
      const errors = JSON.parse(localStorage.getItem('error_logs') || '[]');
      errors.unshift(errorData);

      // Keep only last 10 errors
      if (errors.length > 10) {
        errors.splice(10);
      }

      localStorage.setItem('error_logs', JSON.stringify(errors));
    } catch (err) {
      console.error('Failed to store error locally:', err);
    }
  };

  copyErrorToClipboard = () => {
    const errorText = `Error ID: ${this.state.errorId}\nMessage: ${this.state.error?.message}\nStack: ${this.state.error?.stack}`;
    navigator.clipboard.writeText(errorText).then(() => {
      toast.success('Error details copied to clipboard');
    }).catch(() => {
      toast.error('Failed to copy error details');
    });
  };

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null
    });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  handleReportBug = () => {
    const subject = encodeURIComponent(`Bug Report - Error ID: ${this.state.errorId}`);
    const body = encodeURIComponent(`
Error ID: ${this.state.errorId}
Error Message: ${this.state.error?.message || 'Unknown error'}
URL: ${window.location.href}
Timestamp: ${new Date().toISOString()}

Please describe what you were doing when this error occurred:
[Your description here]
    `);
    
    window.open(`mailto:support@pikar-ai.com?subject=${subject}&body=${body}`);
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI based on error type
      const isNetworkError = this.state.error?.message?.includes('fetch') || 
                            this.state.error?.message?.includes('network');
      
      const isValidationError = this.state.error?.message?.includes('validation') ||
                               this.state.error?.name === 'ZodError';

      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-2xl">
            <CardHeader className="text-center">
              <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                <AlertTriangle className="w-8 h-8 text-red-600" />
              </div>
              <CardTitle className="text-2xl font-bold text-gray-900">
                {isNetworkError ? 'Connection Error' : 
                 isValidationError ? 'Data Error' : 
                 'Something went wrong'}
              </CardTitle>
              <CardDescription className="text-lg">
                {isNetworkError ? 
                  'Unable to connect to our servers. Please check your internet connection.' :
                 isValidationError ?
                  'There was an issue with the data format. Please try refreshing the page.' :
                  'An unexpected error occurred. Our team has been notified.'}
              </CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-6">
              {/* Error ID for support */}
              <div className="bg-gray-100 p-4 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm text-gray-600">Error ID (for support):</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={this.copyErrorToClipboard}
                    className="flex items-center gap-2"
                  >
                    <Copy className="w-4 h-4" />
                    Copy Details
                  </Button>
                </div>
                <code className="text-sm font-mono bg-white px-2 py-1 rounded border block">
                  {this.state.errorId}
                </code>
              </div>

              {/* Development error details */}
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <details className="bg-red-50 p-4 rounded-lg">
                  <summary className="cursor-pointer text-red-800 font-medium mb-2">
                    Development Error Details
                  </summary>
                  <div className="space-y-2">
                    <div>
                      <strong>Error:</strong>
                      <pre className="text-sm bg-white p-2 rounded mt-1 overflow-auto">
                        {this.state.error.message}
                      </pre>
                    </div>
                    <div>
                      <strong>Stack Trace:</strong>
                      <pre className="text-sm bg-white p-2 rounded mt-1 overflow-auto max-h-40">
                        {this.state.error.stack}
                      </pre>
                    </div>
                    {this.state.errorInfo && (
                      <div>
                        <strong>Component Stack:</strong>
                        <pre className="text-sm bg-white p-2 rounded mt-1 overflow-auto max-h-40">
                          {this.state.errorInfo.componentStack}
                        </pre>
                      </div>
                    )}
                  </div>
                </details>
              )}

              {/* Action buttons */}
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button 
                  onClick={this.handleRetry}
                  className="flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Try Again
                </Button>
                
                <Button 
                  variant="outline"
                  onClick={this.handleGoHome}
                  className="flex items-center gap-2"
                >
                  <Home className="w-4 h-4" />
                  Go Home
                </Button>
                
                <Button 
                  variant="outline"
                  onClick={this.handleReportBug}
                  className="flex items-center gap-2"
                >
                  <Bug className="w-4 h-4" />
                  Report Bug
                </Button>
              </div>

              {/* Help text */}
              <div className="text-center text-sm text-gray-500">
                <p>
                  If this problem persists, please contact our support team at{' '}
                  <a 
                    href="mailto:support@pikar-ai.com" 
                    className="text-emerald-600 hover:underline"
                  >
                    support@pikar-ai.com
                  </a>
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

// Higher-order component for wrapping components with error boundary
export const withErrorBoundary = (Component, errorBoundaryProps = {}) => {
  const WrappedComponent = (props) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );
  
  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  return WrappedComponent;
};

// Hook for handling errors in functional components
export const useErrorHandler = () => {
  const handleError = React.useCallback((error, errorInfo = {}) => {
    // Log error
    console.error('Error caught by useErrorHandler:', error);
    
    // You could also throw the error to be caught by ErrorBoundary
    // or handle it differently based on your needs
    
    // For now, we'll just log it and show a toast
    if (typeof window !== 'undefined' && window.toast) {
      window.toast.error('An error occurred. Please try again.');
    }
  }, []);

  return { handleError };
};

export default ErrorBoundary;
