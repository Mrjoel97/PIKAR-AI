import React, { Component } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle, RefreshCw, Save, X } from 'lucide-react';
import { errorHandlingService } from '@/services/errorHandlingService';
import { toast } from 'sonner';

/**
 * Form Error Boundary for handling form-specific errors
 * Provides form data recovery and validation error handling
 */
class FormErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      savedFormData: null,
      errorId: null,
      showRecovery: false
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error: error,
      errorId: `form_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      errorInfo: errorInfo
    });

    // Try to save form data before error
    this.saveFormData();

    // Handle form-specific errors
    const isValidationError = error.name === 'ZodError' || 
                             error.message.includes('validation') ||
                             error.message.includes('required');

    if (isValidationError) {
      errorHandlingService.handleValidationError({
        errors: error.errors || [{ message: error.message }],
        field: error.path?.[0],
        value: error.value
      }, {
        formName: this.props.formName,
        userId: this.props.userId
      });
    } else {
      errorHandlingService.handleGlobalError({
        type: 'form',
        message: error.message,
        error: error,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        formName: this.props.formName
      });
    }
  }

  saveFormData = () => {
    try {
      // Try to extract form data from props or DOM
      let formData = null;

      if (this.props.formData) {
        formData = this.props.formData;
      } else if (this.props.formRef?.current) {
        // Extract data from form ref
        const formElement = this.props.formRef.current;
        const formDataObj = new FormData(formElement);
        formData = Object.fromEntries(formDataObj.entries());
      } else {
        // Try to find form data in the component tree
        formData = this.extractFormDataFromDOM();
      }

      if (formData && Object.keys(formData).length > 0) {
        const savedData = {
          data: formData,
          timestamp: new Date().toISOString(),
          formName: this.props.formName,
          errorId: this.state.errorId
        };

        localStorage.setItem(`form_recovery_${this.props.formName}`, JSON.stringify(savedData));
        this.setState({ savedFormData: savedData });
      }
    } catch (saveError) {
      console.warn('Failed to save form data:', saveError);
    }
  };

  extractFormDataFromDOM = () => {
    try {
      const formElements = document.querySelectorAll('input, select, textarea');
      const formData = {};

      formElements.forEach(element => {
        if (element.name && element.value) {
          formData[element.name] = element.value;
        }
      });

      return formData;
    } catch (error) {
      return {};
    }
  };

  handleRecoverData = () => {
    if (this.state.savedFormData && this.props.onDataRecover) {
      this.props.onDataRecover(this.state.savedFormData.data);
      this.setState({ hasError: false, showRecovery: false });
      toast.success('Form data recovered successfully');
    }
  };

  handleDiscardData = () => {
    if (this.props.formName) {
      localStorage.removeItem(`form_recovery_${this.props.formName}`);
    }
    this.setState({ savedFormData: null, showRecovery: false });
    toast.info('Saved form data discarded');
  };

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  handleReset = () => {
    if (this.props.onReset) {
      this.props.onReset();
    }
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      savedFormData: null
    });
  };

  componentDidMount() {
    // Check for existing saved form data
    if (this.props.formName) {
      const savedData = localStorage.getItem(`form_recovery_${this.props.formName}`);
      if (savedData) {
        try {
          const parsedData = JSON.parse(savedData);
          // Only show recovery if data is recent (within 1 hour)
          const dataAge = Date.now() - new Date(parsedData.timestamp).getTime();
          if (dataAge < 60 * 60 * 1000) {
            this.setState({ savedFormData: parsedData, showRecovery: true });
          } else {
            localStorage.removeItem(`form_recovery_${this.props.formName}`);
          }
        } catch (error) {
          localStorage.removeItem(`form_recovery_${this.props.formName}`);
        }
      }
    }
  }

  render() {
    // Show data recovery prompt if available
    if (this.state.showRecovery && this.state.savedFormData && !this.state.hasError) {
      return (
        <Alert className="mb-4 border-blue-200 bg-blue-50">
          <AlertTriangle className="h-4 w-4 text-blue-600" />
          <AlertDescription className="text-blue-800">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Unsaved form data found</p>
                <p className="text-sm">
                  We found form data from {new Date(this.state.savedFormData.timestamp).toLocaleString()}. 
                  Would you like to recover it?
                </p>
              </div>
              <div className="flex gap-2 ml-4">
                <Button
                  size="sm"
                  onClick={this.handleRecoverData}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  <Save className="w-4 h-4 mr-1" />
                  Recover
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={this.handleDiscardData}
                >
                  <X className="w-4 h-4 mr-1" />
                  Discard
                </Button>
              </div>
            </div>
          </AlertDescription>
        </Alert>
      );
    }

    if (this.state.hasError) {
      const { error } = this.state;
      const isValidationError = error?.name === 'ZodError' || 
                               error?.message?.includes('validation');

      return (
        <div className="p-6">
          <Card className="border-red-200 bg-red-50">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <CardTitle className="text-red-900">
                    {isValidationError ? 'Form Validation Error' : 'Form Error'}
                  </CardTitle>
                  <CardDescription className="text-red-700">
                    {isValidationError ? 
                      'Please check your input and try again.' :
                      'An error occurred while processing the form.'}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            
            <CardContent className="space-y-4">
              {/* Error details */}
              {error?.message && (
                <Alert className="border-red-200 bg-red-50">
                  <AlertDescription className="text-red-800">
                    {error.message}
                  </AlertDescription>
                </Alert>
              )}

              {/* Validation errors */}
              {isValidationError && error?.errors && (
                <div className="space-y-2">
                  <p className="font-medium text-red-900">Validation Issues:</p>
                  <ul className="list-disc list-inside space-y-1 text-red-800">
                    {error.errors.map((err, index) => (
                      <li key={index} className="text-sm">
                        {err.path ? `${err.path.join('.')}: ` : ''}{err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Saved data notification */}
              {this.state.savedFormData && (
                <Alert className="border-blue-200 bg-blue-50">
                  <AlertDescription className="text-blue-800">
                    <div className="flex items-center justify-between">
                      <span>Your form data has been saved and can be recovered.</span>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={this.handleRecoverData}
                        className="border-blue-300 text-blue-700 hover:bg-blue-100"
                      >
                        <Save className="w-4 h-4 mr-1" />
                        Recover Data
                      </Button>
                    </div>
                  </AlertDescription>
                </Alert>
              )}

              {/* Development error details */}
              {process.env.NODE_ENV === 'development' && (
                <details className="bg-gray-100 p-3 rounded text-xs">
                  <summary className="cursor-pointer font-medium">Debug Information</summary>
                  <div className="mt-2 space-y-1">
                    <p><strong>Form:</strong> {this.props.formName}</p>
                    <p><strong>Error ID:</strong> {this.state.errorId}</p>
                    <p><strong>Error Type:</strong> {error?.name}</p>
                    <p><strong>Stack:</strong></p>
                    <pre className="text-xs bg-white p-2 rounded overflow-auto max-h-32">
                      {error?.stack}
                    </pre>
                  </div>
                </details>
              )}

              {/* Action buttons */}
              <div className="flex gap-2 pt-2">
                <Button
                  onClick={this.handleRetry}
                  className="flex-1"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Try Again
                </Button>
                
                <Button
                  variant="outline"
                  onClick={this.handleReset}
                  className="flex-1"
                >
                  Reset Form
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default FormErrorBoundary;
