import React, { Component } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, RefreshCw, Loader2 } from 'lucide-react';
import { errorHandlingService } from '@/services/errorHandlingService';
import { toast } from 'sonner';

/**
 * Async Error Boundary for handling async operation errors
 * Specifically designed for API calls, data loading, and async components
 */
class AsyncErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      isRetrying: false,
      retryCount: 0,
      errorId: null
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error: error,
      errorId: `async_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      errorInfo: errorInfo
    });

    // Handle async-specific errors
    const enhancedError = {
      ...error,
      type: 'async',
      component: this.props.componentName || 'AsyncComponent',
      operation: this.props.operation || 'unknown',
      context: {
        ...this.props.context,
        retryCount: this.state.retryCount
      }
    };

    // Use error handling service
    errorHandlingService.handleGlobalError({
      type: 'async',
      message: error.message,
      error: enhancedError,
      stack: error.stack,
      componentStack: errorInfo.componentStack
    });
  }

  handleRetry = async () => {
    if (this.state.isRetrying) return;

    this.setState({ isRetrying: true });

    try {
      // Call retry function if provided
      if (this.props.onRetry) {
        await this.props.onRetry();
      }

      // Reset error state
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        isRetrying: false,
        retryCount: this.state.retryCount + 1
      });

      toast.success('Operation retried successfully');
    } catch (retryError) {
      this.setState({
        isRetrying: false,
        retryCount: this.state.retryCount + 1
      });

      toast.error('Retry failed. Please try again.');
      
      // Log retry failure
      errorHandlingService.handleGlobalError({
        type: 'retry_failed',
        message: retryError.message,
        error: retryError,
        originalError: this.state.error
      });
    }
  };

  handleFallback = () => {
    if (this.props.onFallback) {
      this.props.onFallback();
    } else {
      // Default fallback - redirect to safe page
      window.location.href = this.props.fallbackUrl || '/dashboard';
    }
  };

  render() {
    if (this.state.hasError) {
      const { error } = this.state;
      const isNetworkError = error?.message?.includes('fetch') || 
                            error?.message?.includes('network') ||
                            error?.name === 'NetworkError';
      
      const isTimeoutError = error?.message?.includes('timeout') ||
                            error?.code === 'TIMEOUT';

      const canRetry = this.state.retryCount < (this.props.maxRetries || 3) && 
                      (isNetworkError || isTimeoutError || this.props.retryable);

      return (
        <div className="flex items-center justify-center p-8">
          <Card className="w-full max-w-md">
            <CardHeader className="text-center">
              <div className="mx-auto w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center mb-3">
                <AlertTriangle className="w-6 h-6 text-orange-600" />
              </div>
              <CardTitle className="text-lg font-semibold text-gray-900">
                {isNetworkError ? 'Connection Error' :
                 isTimeoutError ? 'Request Timeout' :
                 this.props.title || 'Loading Failed'}
              </CardTitle>
              <CardDescription>
                {isNetworkError ? 
                  'Unable to connect to the server. Please check your internet connection.' :
                 isTimeoutError ?
                  'The request took too long to complete. Please try again.' :
                  this.props.description || 'Failed to load the requested data.'}
              </CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-4">
              {/* Error details for development */}
              {process.env.NODE_ENV === 'development' && (
                <div className="bg-gray-50 p-3 rounded text-xs">
                  <p><strong>Component:</strong> {this.props.componentName}</p>
                  <p><strong>Operation:</strong> {this.props.operation}</p>
                  <p><strong>Retry Count:</strong> {this.state.retryCount}</p>
                  <p><strong>Error:</strong> {error?.message}</p>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-2">
                {canRetry && (
                  <Button
                    onClick={this.handleRetry}
                    disabled={this.state.isRetrying}
                    className="flex-1"
                  >
                    {this.state.isRetrying ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Retrying...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Retry ({this.props.maxRetries - this.state.retryCount} left)
                      </>
                    )}
                  </Button>
                )}
                
                <Button
                  variant="outline"
                  onClick={this.handleFallback}
                  className={canRetry ? '' : 'flex-1'}
                >
                  {this.props.fallbackLabel || 'Go Back'}
                </Button>
              </div>

              {/* Retry information */}
              {this.state.retryCount > 0 && (
                <div className="text-sm text-gray-600 text-center">
                  Attempted {this.state.retryCount} time{this.state.retryCount > 1 ? 's' : ''}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default AsyncErrorBoundary;
