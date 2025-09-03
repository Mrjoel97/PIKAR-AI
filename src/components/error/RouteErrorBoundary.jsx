import React, { Component } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Home, ArrowLeft, RefreshCw, MapPin } from 'lucide-react';
import { errorHandlingService } from '@/services/errorHandlingService';
import { toast } from 'sonner';

/**
 * Route Error Boundary for handling navigation and route-specific errors
 * Provides navigation recovery and route-specific error handling
 */
class RouteErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
      previousRoute: null,
      currentRoute: null
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error: error,
      errorId: `route_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      errorInfo: errorInfo,
      currentRoute: window.location.pathname,
      previousRoute: this.getPreviousRoute()
    });

    // Handle route-specific errors
    const routeError = {
      type: 'route',
      message: error.message,
      error: error,
      stack: error.stack,
      route: window.location.pathname,
      previousRoute: this.state.previousRoute,
      componentStack: errorInfo.componentStack
    };

    errorHandlingService.handleGlobalError(routeError);

    // Store current route for recovery
    this.storeRouteForRecovery();
  }

  getPreviousRoute = () => {
    try {
      return sessionStorage.getItem('previous_route') || '/dashboard';
    } catch {
      return '/dashboard';
    }
  };

  storeRouteForRecovery = () => {
    try {
      sessionStorage.setItem('error_route', window.location.pathname);
      sessionStorage.setItem('error_timestamp', new Date().toISOString());
    } catch (error) {
      console.warn('Failed to store route for recovery:', error);
    }
  };

  handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  handleGoBack = () => {
    const previousRoute = this.state.previousRoute;
    if (previousRoute && previousRoute !== window.location.pathname) {
      window.location.href = previousRoute;
    } else {
      window.history.back();
    }
  };

  handleRetry = () => {
    // Clear error state and retry current route
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });

    // Force a re-render by reloading the current route
    window.location.reload();
  };

  handleReportIssue = () => {
    const errorReport = {
      errorId: this.state.errorId,
      route: this.state.currentRoute,
      error: this.state.error?.message,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent
    };

    // In a real app, this would send to your support system
    console.log('Error report:', errorReport);
    
    // Copy to clipboard for now
    navigator.clipboard.writeText(JSON.stringify(errorReport, null, 2))
      .then(() => {
        toast.success('Error report copied to clipboard');
      })
      .catch(() => {
        toast.error('Failed to copy error report');
      });
  };

  getErrorTitle = () => {
    const { error } = this.state;
    
    if (error?.message?.includes('ChunkLoadError') || error?.message?.includes('Loading chunk')) {
      return 'Page Loading Error';
    }
    
    if (error?.message?.includes('404') || error?.message?.includes('Not Found')) {
      return 'Page Not Found';
    }
    
    if (error?.message?.includes('403') || error?.message?.includes('Forbidden')) {
      return 'Access Denied';
    }
    
    if (error?.message?.includes('401') || error?.message?.includes('Unauthorized')) {
      return 'Authentication Required';
    }
    
    return 'Page Error';
  };

  getErrorDescription = () => {
    const { error } = this.state;
    
    if (error?.message?.includes('ChunkLoadError') || error?.message?.includes('Loading chunk')) {
      return 'Failed to load page resources. This usually happens after an app update.';
    }
    
    if (error?.message?.includes('404') || error?.message?.includes('Not Found')) {
      return 'The page you\'re looking for doesn\'t exist or has been moved.';
    }
    
    if (error?.message?.includes('403') || error?.message?.includes('Forbidden')) {
      return 'You don\'t have permission to access this page.';
    }
    
    if (error?.message?.includes('401') || error?.message?.includes('Unauthorized')) {
      return 'Please log in to access this page.';
    }
    
    return 'Something went wrong while loading this page.';
  };

  getRecoveryActions = () => {
    const { error } = this.state;
    const actions = [];

    // Always show retry for chunk load errors
    if (error?.message?.includes('ChunkLoadError') || error?.message?.includes('Loading chunk')) {
      actions.push({
        label: 'Refresh Page',
        icon: RefreshCw,
        action: this.handleRetry,
        primary: true
      });
    } else {
      actions.push({
        label: 'Try Again',
        icon: RefreshCw,
        action: this.handleRetry,
        primary: true
      });
    }

    // Show go back if we have a previous route
    if (this.state.previousRoute && this.state.previousRoute !== this.state.currentRoute) {
      actions.push({
        label: 'Go Back',
        icon: ArrowLeft,
        action: this.handleGoBack,
        primary: false
      });
    }

    // Always show home
    actions.push({
      label: 'Go Home',
      icon: Home,
      action: this.handleGoHome,
      primary: false
    });

    return actions;
  };

  render() {
    if (this.state.hasError) {
      const title = this.getErrorTitle();
      const description = this.getErrorDescription();
      const actions = this.getRecoveryActions();

      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-lg">
            <CardHeader className="text-center">
              <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                <AlertTriangle className="w-8 h-8 text-red-600" />
              </div>
              <CardTitle className="text-xl font-bold text-gray-900">
                {title}
              </CardTitle>
              <CardDescription className="text-base">
                {description}
              </CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-6">
              {/* Route information */}
              <div className="bg-gray-100 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <MapPin className="w-4 h-4 text-gray-600" />
                  <span className="text-sm font-medium text-gray-700">Route Information</span>
                </div>
                <div className="space-y-1 text-sm text-gray-600">
                  <p><strong>Current:</strong> {this.state.currentRoute}</p>
                  {this.state.previousRoute && (
                    <p><strong>Previous:</strong> {this.state.previousRoute}</p>
                  )}
                  <p><strong>Error ID:</strong> {this.state.errorId}</p>
                </div>
              </div>

              {/* Development error details */}
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <details className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
                  <summary className="cursor-pointer font-medium text-yellow-800 mb-2">
                    Development Error Details
                  </summary>
                  <div className="space-y-2 text-sm">
                    <p><strong>Error:</strong> {this.state.error.message}</p>
                    <p><strong>Type:</strong> {this.state.error.name}</p>
                    {this.state.error.stack && (
                      <div>
                        <p><strong>Stack Trace:</strong></p>
                        <pre className="text-xs bg-white p-2 rounded border overflow-auto max-h-32 mt-1">
                          {this.state.error.stack}
                        </pre>
                      </div>
                    )}
                  </div>
                </details>
              )}

              {/* Action buttons */}
              <div className="space-y-3">
                {actions.map((action, index) => (
                  <Button
                    key={index}
                    onClick={action.action}
                    variant={action.primary ? 'default' : 'outline'}
                    className="w-full flex items-center justify-center gap-2"
                  >
                    <action.icon className="w-4 h-4" />
                    {action.label}
                  </Button>
                ))}
              </div>

              {/* Report issue */}
              <div className="pt-4 border-t">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={this.handleReportIssue}
                  className="w-full text-gray-600 hover:text-gray-800"
                >
                  Report this issue
                </Button>
              </div>

              {/* Help text */}
              <div className="text-center text-sm text-gray-500">
                If this problem persists, please contact support with the error ID above.
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }

  componentDidUpdate(prevProps) {
    // Track route changes
    if (prevProps.location !== this.props.location) {
      try {
        sessionStorage.setItem('previous_route', prevProps.location?.pathname || '/dashboard');
      } catch (error) {
        console.warn('Failed to store previous route:', error);
      }
    }
  }
}

export default RouteErrorBoundary;
