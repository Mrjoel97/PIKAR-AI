import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        this.setState({
            error: error,
            errorInfo: errorInfo
        });
        
        // Log error to monitoring service
        console.error('Error Boundary caught an error:', error, errorInfo);
        
        // Send to analytics/monitoring
        if (window.analytics) {
            window.analytics.track('Error Boundary Triggered', {
                error: error.message,
                stack: error.stack,
                componentStack: errorInfo.componentStack
            });
        }
    }

    render() {
        if (this.state.hasError) {
            // Simple development detection without import.meta
            const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            
            return (
                <div className="min-h-screen flex items-center justify-center p-4">
                    <Card className="w-full max-w-md">
                        <CardHeader className="text-center">
                            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                            <CardTitle>Something went wrong</CardTitle>
                        </CardHeader>
                        <CardContent className="text-center space-y-4">
                            <p className="text-gray-600">
                                We apologize for the inconvenience. The application encountered an unexpected error.
                            </p>
                            <Button 
                                onClick={() => window.location.reload()}
                                className="w-full"
                            >
                                <RefreshCw className="w-4 h-4 mr-2" />
                                Reload Application
                            </Button>
                            {isDevelopment && (
                                <details className="text-left mt-4">
                                    <summary className="cursor-pointer font-medium">Technical Details</summary>
                                    <div className="mt-2 p-3 bg-gray-50 rounded text-xs">
                                        <div className="font-medium">Error:</div>
                                        <div className="text-red-600">{this.state.error && this.state.error.toString()}</div>
                                        <div className="font-medium mt-2">Component Stack:</div>
                                        <div className="text-gray-600">{this.state.errorInfo.componentStack}</div>
                                    </div>
                                </details>
                            )}
                        </CardContent>
                    </Card>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;