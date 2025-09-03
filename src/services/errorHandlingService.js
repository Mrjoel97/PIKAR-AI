/**
 * Error Handling Service
 * Centralized error management, logging, and recovery system
 */

import { auditService } from './auditService';
import { toast } from 'sonner';

class ErrorHandlingService {
  constructor() {
    this.errorQueue = [];
    this.maxQueueSize = 100;
    this.retryAttempts = new Map();
    this.maxRetryAttempts = 3;
    this.errorPatterns = new Map();
    this.recoveryStrategies = new Map();
    this.initialized = false;
  }

  /**
   * Initialize error handling service
   */
  initialize() {
    if (this.initialized) return;

    // Set up global error handlers
    this.setupGlobalErrorHandlers();
    
    // Register default recovery strategies
    this.registerDefaultRecoveryStrategies();
    
    // Set up error pattern detection
    this.setupErrorPatternDetection();
    
    this.initialized = true;
    console.log('🚨 Error Handling Service initialized');
  }

  /**
   * Set up global error handlers
   */
  setupGlobalErrorHandlers() {
    // Global JavaScript error handler
    window.addEventListener('error', (event) => {
      this.handleGlobalError({
        type: 'javascript',
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error,
        stack: event.error?.stack
      });
    });

    // Unhandled promise rejection handler
    window.addEventListener('unhandledrejection', (event) => {
      this.handleGlobalError({
        type: 'promise',
        message: event.reason?.message || 'Unhandled promise rejection',
        error: event.reason,
        stack: event.reason?.stack,
        promise: event.promise
      });
    });

    // Resource loading error handler
    window.addEventListener('error', (event) => {
      if (event.target !== window) {
        this.handleResourceError({
          type: 'resource',
          element: event.target.tagName,
          source: event.target.src || event.target.href,
          message: `Failed to load ${event.target.tagName.toLowerCase()}`
        });
      }
    }, true);
  }

  /**
   * Handle global JavaScript errors
   * @param {Object} errorInfo - Error information
   */
  handleGlobalError(errorInfo) {
    try {
      const errorId = this.generateErrorId();
      const enhancedError = {
        ...errorInfo,
        id: errorId,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        userAgent: navigator.userAgent,
        userId: this.getCurrentUserId(),
        sessionId: this.getSessionId(),
        severity: this.calculateSeverity(errorInfo),
        context: this.getErrorContext()
      };

      // Add to error queue
      this.addToErrorQueue(enhancedError);

      // Log to audit service
      auditService.logSystem.error(errorInfo.error || new Error(errorInfo.message), 'global_error_handler', {
        errorId,
        type: errorInfo.type,
        severity: enhancedError.severity
      });

      // Attempt recovery
      this.attemptRecovery(enhancedError);

      // Show user notification if severe
      if (enhancedError.severity === 'high' || enhancedError.severity === 'critical') {
        this.showErrorNotification(enhancedError);
      }

    } catch (handlingError) {
      console.error('Error in error handler:', handlingError);
    }
  }

  /**
   * Handle resource loading errors
   * @param {Object} errorInfo - Resource error information
   */
  handleResourceError(errorInfo) {
    const errorId = this.generateErrorId();
    const enhancedError = {
      ...errorInfo,
      id: errorId,
      timestamp: new Date().toISOString(),
      severity: 'medium'
    };

    this.addToErrorQueue(enhancedError);

    // Log resource error
    auditService.logSystem.error(new Error(errorInfo.message), 'resource_error', {
      errorId,
      element: errorInfo.element,
      source: errorInfo.source
    });

    // Attempt resource recovery
    this.attemptResourceRecovery(enhancedError);
  }

  /**
   * Handle API errors
   * @param {Error} error - API error
   * @param {Object} context - Request context
   * @returns {Object} Error handling result
   */
  handleApiError(error, context = {}) {
    const errorId = this.generateErrorId();
    const enhancedError = {
      id: errorId,
      type: 'api',
      message: error.message,
      status: error.status || context.status,
      endpoint: context.endpoint || context.url,
      method: context.method || 'GET',
      timestamp: new Date().toISOString(),
      severity: this.getApiErrorSeverity(error.status),
      retryable: this.isRetryableError(error.status),
      context
    };

    this.addToErrorQueue(enhancedError);

    // Log API error
    auditService.logSystem.error(error, 'api_error', {
      errorId,
      endpoint: enhancedError.endpoint,
      status: enhancedError.status,
      method: enhancedError.method
    });

    // Handle specific API error types
    return this.handleSpecificApiError(enhancedError);
  }

  /**
   * Handle validation errors
   * @param {Object} validationError - Validation error details
   * @param {Object} context - Validation context
   */
  handleValidationError(validationError, context = {}) {
    const errorId = this.generateErrorId();
    const enhancedError = {
      id: errorId,
      type: 'validation',
      message: 'Data validation failed',
      errors: validationError.errors || [],
      field: validationError.field,
      value: validationError.value,
      timestamp: new Date().toISOString(),
      severity: 'medium',
      context
    };

    this.addToErrorQueue(enhancedError);

    // Log validation error
    auditService.logData.modification(context.userId, 'validation_error', context.formName || 'unknown', {
      errorId,
      field: enhancedError.field,
      errorCount: enhancedError.errors.length
    });

    // Show user-friendly validation messages
    this.showValidationErrors(enhancedError);

    return enhancedError;
  }

  /**
   * Register recovery strategy for error pattern
   * @param {string} pattern - Error pattern (regex string or error type)
   * @param {Function} strategy - Recovery strategy function
   */
  registerRecoveryStrategy(pattern, strategy) {
    this.recoveryStrategies.set(pattern, strategy);
  }

  /**
   * Register default recovery strategies
   */
  registerDefaultRecoveryStrategies() {
    // Chunk loading error recovery
    this.registerRecoveryStrategy('ChunkLoadError', (error) => {
      toast.error('Loading error detected. Refreshing page...', {
        duration: 3000
      });
      setTimeout(() => window.location.reload(), 3000);
    });

    // Network error recovery
    this.registerRecoveryStrategy(/network|fetch/i, (error) => {
      if (navigator.onLine) {
        toast.error('Network error. Retrying in 5 seconds...', {
          duration: 5000
        });
        setTimeout(() => this.retryLastOperation(error), 5000);
      } else {
        toast.error('You appear to be offline. Please check your connection.', {
          duration: 10000
        });
      }
    });

    // Authentication error recovery
    this.registerRecoveryStrategy(/401|unauthorized/i, (error) => {
      toast.error('Session expired. Redirecting to login...', {
        duration: 3000
      });
      setTimeout(() => {
        window.location.href = '/login';
      }, 3000);
    });

    // Permission error recovery
    this.registerRecoveryStrategy(/403|forbidden/i, (error) => {
      toast.error('Access denied. Redirecting to dashboard...', {
        duration: 3000
      });
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 3000);
    });

    // Server error recovery
    this.registerRecoveryStrategy(/5\d\d/, (error) => {
      toast.error('Server error. Please try again later.', {
        duration: 5000
      });
    });
  }

  /**
   * Attempt error recovery
   * @param {Object} error - Enhanced error object
   */
  attemptRecovery(error) {
    // Check for registered recovery strategies
    for (const [pattern, strategy] of this.recoveryStrategies.entries()) {
      if (this.matchesPattern(error, pattern)) {
        try {
          strategy(error);
          auditService.logSystem.configChange(null, 'error_recovery_attempted', error.id, pattern.toString());
          return;
        } catch (recoveryError) {
          console.error('Recovery strategy failed:', recoveryError);
        }
      }
    }

    // Default recovery for unhandled errors
    if (error.severity === 'critical') {
      this.performCriticalErrorRecovery(error);
    }
  }

  /**
   * Attempt resource recovery
   * @param {Object} error - Resource error
   */
  attemptResourceRecovery(error) {
    const retryCount = this.retryAttempts.get(error.source) || 0;
    
    if (retryCount < this.maxRetryAttempts) {
      this.retryAttempts.set(error.source, retryCount + 1);
      
      setTimeout(() => {
        if (error.element === 'SCRIPT') {
          this.retryScriptLoad(error.source);
        } else if (error.element === 'LINK') {
          this.retryStylesheetLoad(error.source);
        } else if (error.element === 'IMG') {
          this.retryImageLoad(error.source);
        }
      }, Math.pow(2, retryCount) * 1000); // Exponential backoff
    }
  }

  /**
   * Show error notification to user
   * @param {Object} error - Error object
   */
  showErrorNotification(error) {
    const message = this.getUserFriendlyMessage(error);
    
    if (error.severity === 'critical') {
      toast.error(message, {
        duration: 10000,
        action: {
          label: 'Report',
          onClick: () => this.reportError(error)
        }
      });
    } else if (error.severity === 'high') {
      toast.error(message, {
        duration: 5000
      });
    } else {
      toast.warning(message, {
        duration: 3000
      });
    }
  }

  /**
   * Show validation errors to user
   * @param {Object} error - Validation error
   */
  showValidationErrors(error) {
    if (error.errors && error.errors.length > 0) {
      error.errors.forEach(validationError => {
        toast.error(validationError.message || 'Validation error', {
          duration: 5000
        });
      });
    } else {
      toast.error('Please check your input and try again', {
        duration: 3000
      });
    }
  }

  /**
   * Get user-friendly error message
   * @param {Object} error - Error object
   * @returns {string} User-friendly message
   */
  getUserFriendlyMessage(error) {
    const messageMap = {
      'ChunkLoadError': 'Failed to load application resources. The page will refresh automatically.',
      'TypeError': 'An unexpected error occurred. Please try refreshing the page.',
      'ReferenceError': 'A system error occurred. Please contact support if this persists.',
      'NetworkError': 'Unable to connect to our servers. Please check your internet connection.',
      'ValidationError': 'Please check your input and try again.',
      'AuthenticationError': 'Your session has expired. Please log in again.',
      'PermissionError': 'You don\'t have permission to perform this action.',
      'ServerError': 'Our servers are experiencing issues. Please try again later.'
    };

    return messageMap[error.type] || 
           messageMap[error.error?.name] || 
           'An unexpected error occurred. Our team has been notified.';
  }

  // Utility methods
  generateErrorId() {
    return `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  getCurrentUserId() {
    try {
      const userData = JSON.parse(localStorage.getItem('pikar_user_data') || '{}');
      return userData.id || 'anonymous';
    } catch {
      return 'anonymous';
    }
  }

  getSessionId() {
    let sessionId = sessionStorage.getItem('session_id');
    if (!sessionId) {
      sessionId = `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('session_id', sessionId);
    }
    return sessionId;
  }

  calculateSeverity(errorInfo) {
    if (errorInfo.type === 'promise' && errorInfo.message.includes('ChunkLoadError')) {
      return 'high';
    }
    if (errorInfo.error?.name === 'TypeError' || errorInfo.error?.name === 'ReferenceError') {
      return 'high';
    }
    if (errorInfo.message.includes('Network') || errorInfo.message.includes('fetch')) {
      return 'medium';
    }
    return 'medium';
  }

  getApiErrorSeverity(status) {
    if (status >= 500) return 'high';
    if (status === 401 || status === 403) return 'medium';
    if (status >= 400) return 'low';
    return 'low';
  }

  isRetryableError(status) {
    return status >= 500 || status === 408 || status === 429;
  }

  matchesPattern(error, pattern) {
    if (pattern instanceof RegExp) {
      return pattern.test(error.message) || pattern.test(error.type) || pattern.test(error.status?.toString());
    }
    return error.type === pattern || error.error?.name === pattern || error.message.includes(pattern);
  }

  addToErrorQueue(error) {
    this.errorQueue.unshift(error);
    if (this.errorQueue.length > this.maxQueueSize) {
      this.errorQueue.pop();
    }
  }

  getErrorContext() {
    return {
      url: window.location.href,
      timestamp: new Date().toISOString(),
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      },
      userAgent: navigator.userAgent,
      online: navigator.onLine
    };
  }

  /**
   * Get error statistics
   * @returns {Object} Error statistics
   */
  getErrorStats() {
    const now = Date.now();
    const oneHourAgo = now - (60 * 60 * 1000);
    
    const recentErrors = this.errorQueue.filter(error => 
      new Date(error.timestamp).getTime() > oneHourAgo
    );

    return {
      totalErrors: this.errorQueue.length,
      recentErrors: recentErrors.length,
      errorsByType: this.groupErrorsByType(recentErrors),
      errorsBySeverity: this.groupErrorsBySeverity(recentErrors),
      topErrors: this.getTopErrors(recentErrors)
    };
  }

  groupErrorsByType(errors) {
    return errors.reduce((acc, error) => {
      acc[error.type] = (acc[error.type] || 0) + 1;
      return acc;
    }, {});
  }

  groupErrorsBySeverity(errors) {
    return errors.reduce((acc, error) => {
      acc[error.severity] = (acc[error.severity] || 0) + 1;
      return acc;
    }, {});
  }

  getTopErrors(errors) {
    const errorCounts = errors.reduce((acc, error) => {
      const key = error.message || error.type;
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(errorCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([message, count]) => ({ message, count }));
  }

  /**
   * Clear error queue
   */
  clearErrors() {
    this.errorQueue = [];
    this.retryAttempts.clear();
    auditService.logSystem.configChange(null, 'error_queue_cleared', null, 'cleared');
  }
}

// Create and export singleton instance
export const errorHandlingService = new ErrorHandlingService();
