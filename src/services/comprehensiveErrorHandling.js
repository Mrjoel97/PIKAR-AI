/**
 * Comprehensive Error Handling Service
 * Advanced error handling, logging, recovery, and monitoring system
 */

import { auditService } from './auditService'
import { performanceOptimizationService } from './performanceOptimizationService'
import { environmentConfig } from '@/config/environment'

class ComprehensiveErrorHandlingService {
  constructor() {
    this.errorCounts = new Map()
    this.errorPatterns = new Map()
    this.recoveryStrategies = new Map()
    this.circuitBreakers = new Map()
    this.errorQueue = []
    this.maxQueueSize = 1000
    
    this.errorThresholds = {
      api: 10,
      validation: 5,
      system: 3,
      network: 8,
      authentication: 3,
      authorization: 5,
      rateLimit: 15,
      agent: 7
    }
    
    this.circuitBreakerConfig = {
      failureThreshold: 5,
      recoveryTimeout: 30000, // 30 seconds
      monitoringPeriod: 60000  // 1 minute
    }
    
    // Error classification patterns
    this.errorClassifications = {
      network: [/ECONNREFUSED/, /ETIMEDOUT/, /ENOTFOUND/, /Network Error/i],
      authentication: [/401/, /unauthorized/i, /invalid.*token/i, /expired.*token/i],
      authorization: [/403/, /forbidden/i, /access.*denied/i, /insufficient.*permission/i],
      validation: [/validation/i, /invalid.*input/i, /required.*field/i, /format.*error/i],
      rateLimit: [/429/, /rate.*limit/i, /too.*many.*requests/i],
      server: [/5\d{2}/, /internal.*server/i, /service.*unavailable/i],
      client: [/4\d{2}/, /bad.*request/i, /not.*found/i],
      agent: [/agent.*error/i, /execution.*failed/i, /timeout.*agent/i]
    }
    
    this.setupRecoveryStrategies()
    this.setupGlobalErrorHandlers()
  }

  /**
   * Setup recovery strategies for different error types
   */
  setupRecoveryStrategies() {
    this.recoveryStrategies.set('network', {
      retry: true,
      maxRetries: 3,
      backoffStrategy: 'exponential',
      fallback: 'cache',
      userMessage: 'Connection issue. Retrying...'
    })
    
    this.recoveryStrategies.set('authentication', {
      retry: false,
      action: 'redirect_login',
      clearTokens: true,
      userMessage: 'Please log in again'
    })
    
    this.recoveryStrategies.set('authorization', {
      retry: false,
      action: 'show_permission_error',
      logSecurityEvent: true,
      userMessage: 'You do not have permission for this action'
    })
    
    this.recoveryStrategies.set('validation', {
      retry: false,
      action: 'show_validation_errors',
      sanitizeInput: true,
      userMessage: 'Please check your input and try again'
    })
    
    this.recoveryStrategies.set('rateLimit', {
      retry: true,
      maxRetries: 2,
      backoffStrategy: 'linear',
      respectRetryAfter: true,
      userMessage: 'Too many requests. Please wait a moment...'
    })
    
    this.recoveryStrategies.set('server', {
      retry: true,
      maxRetries: 2,
      backoffStrategy: 'exponential',
      fallback: 'degraded_service',
      userMessage: 'Server issue. Trying again...'
    })
    
    this.recoveryStrategies.set('agent', {
      retry: true,
      maxRetries: 2,
      backoffStrategy: 'linear',
      fallback: 'simplified_response',
      userMessage: 'AI agent is busy. Retrying...'
    })
  }

  /**
   * Setup global error handlers
   */
  setupGlobalErrorHandlers() {
    if (typeof window !== 'undefined') {
      // Handle unhandled promise rejections
      window.addEventListener('unhandledrejection', (event) => {
        this.handleUnhandledError(event.reason, 'unhandled_promise_rejection')
        event.preventDefault()
      })
      
      // Handle uncaught errors
      window.addEventListener('error', (event) => {
        this.handleUnhandledError(event.error, 'uncaught_error', {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno
        })
      })
      
      // Handle resource loading errors
      window.addEventListener('error', (event) => {
        if (event.target !== window) {
          this.handleResourceError({
            type: 'resource_error',
            element: event.target.tagName,
            source: event.target.src || event.target.href,
            message: `Failed to load ${event.target.tagName.toLowerCase()}`
          })
        }
      }, true)
    }
  }

  /**
   * Main error handling method
   */
  async handleError(error, context = {}) {
    try {
      // Generate unique error ID
      const errorId = this.generateErrorId()
      
      // Classify error
      const classification = this.classifyError(error)
      
      // Create comprehensive error info
      const errorInfo = {
        id: errorId,
        type: classification,
        message: error.message,
        status: error.status || error.response?.status,
        code: error.code,
        context,
        timestamp: Date.now(),
        stack: error.stack,
        userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : null,
        url: typeof window !== 'undefined' ? window.location.href : null,
        userId: context.userId || this.getCurrentUserId(),
        sessionId: context.sessionId || this.getSessionId()
      }
      
      // Add to error queue
      this.addToErrorQueue(errorInfo)
      
      // Log error
      await auditService.logSystem.error(error, classification, errorInfo)
      
      // Track error patterns
      this.trackErrorPattern(errorInfo)
      
      // Check circuit breaker
      const circuitBreakerKey = `${classification}_${context.operation || 'unknown'}`
      if (this.isCircuitBreakerOpen(circuitBreakerKey)) {
        return {
          success: false,
          error: 'Service temporarily unavailable due to repeated failures',
          canRetry: false,
          circuitBreakerOpen: true
        }
      }
      
      // Update circuit breaker
      this.updateCircuitBreaker(circuitBreakerKey, false)
      
      // Apply recovery strategy
      const recoveryResult = await this.applyRecoveryStrategy(error, classification, context)
      
      return recoveryResult
      
    } catch (handlingError) {
      // Error in error handling - log and return basic error
      console.error('Error in error handling:', handlingError)
      await auditService.logSystem.error(handlingError, 'error_handling_failure', {
        originalError: error.message
      })
      
      return {
        success: false,
        error: 'An unexpected error occurred',
        canRetry: false,
        handlingError: true
      }
    }
  }

  /**
   * Handle API errors with comprehensive recovery
   */
  async handleAPIError(error, context = '') {
    const apiContext = {
      type: 'api_error',
      operation: context,
      endpoint: error.config?.url || context.endpoint,
      method: error.config?.method || context.method
    }
    
    const result = await this.handleError(error, apiContext)
    
    // Track API error count
    this.trackError('api')
    
    if (!result.success && !result.handled) {
      throw new Error(this.getUserFriendlyMessage(error))
    }
    
    return result
  }

  /**
   * Handle validation errors
   */
  async handleValidationError(error, field = '') {
    const validationContext = {
      type: 'validation_error',
      field,
      operation: 'validation'
    }
    
    const result = await this.handleError(error, validationContext)
    
    this.trackError('validation')
    
    return {
      success: false,
      error: `Validation failed${field ? ` for ${field}` : ''}: ${error.message}`,
      field,
      canRetry: false,
      type: 'validation'
    }
  }

  /**
   * Handle system errors
   */
  async handleSystemError(error, component = '') {
    const systemContext = {
      type: 'system_error',
      component,
      operation: 'system'
    }
    
    const result = await this.handleError(error, systemContext)
    
    this.trackError('system')
    
    return {
      success: false,
      error: 'A system error occurred. Please try again later.',
      component,
      canRetry: true,
      type: 'system'
    }
  }

  /**
   * Handle agent execution errors
   */
  async handleAgentError(error, agentType, task) {
    const agentContext = {
      type: 'agent_error',
      agentType,
      task,
      operation: 'agent_execution'
    }
    
    const result = await this.handleError(error, agentContext)
    
    this.trackError('agent')
    
    // Log agent-specific error
    await auditService.logAccess.agentExecution('agent_execution_failed', {
      agentType,
      task,
      error: error.message,
      timestamp: Date.now()
    })
    
    return {
      success: false,
      error: `Agent execution failed: ${error.message}`,
      agentType,
      task,
      canRetry: true,
      type: 'agent'
    }
  }

  /**
   * Handle unhandled errors
   */
  async handleUnhandledError(error, type, details = {}) {
    const unhandledContext = {
      type: 'unhandled_error',
      subtype: type,
      operation: 'global_handler',
      ...details
    }
    
    await this.handleError(error, unhandledContext)
    
    // Always log unhandled errors as critical
    await auditService.logSystem.alert('unhandled_error_detected', {
      type,
      message: error?.message || 'Unknown error',
      stack: error?.stack,
      ...details
    })
  }

  /**
   * Handle resource loading errors
   */
  async handleResourceError(errorInfo) {
    await auditService.logSystem.error(new Error(errorInfo.message), 'resource_error', errorInfo)
    
    // Don't throw for resource errors, just log them
    console.warn('Resource loading error:', errorInfo)
  }

  /**
   * Classify error based on patterns
   */
  classifyError(error) {
    const errorString = `${error.message} ${error.status} ${error.code}`.toLowerCase()
    
    for (const [classification, patterns] of Object.entries(this.errorClassifications)) {
      if (patterns.some(pattern => pattern.test(errorString))) {
        return classification
      }
    }
    
    // Default classification based on status code
    if (error.status) {
      if (error.status >= 500) return 'server'
      if (error.status >= 400) return 'client'
    }
    
    return 'unknown'
  }

  /**
   * Apply recovery strategy based on error type
   */
  async applyRecoveryStrategy(error, classification, context) {
    const strategy = this.recoveryStrategies.get(classification)
    
    if (!strategy) {
      return {
        success: false,
        error: this.getUserFriendlyMessage(error),
        canRetry: false
      }
    }
    
    // Handle retry logic
    if (strategy.retry) {
      const retryKey = `${classification}_${context.operation || 'unknown'}`
      const currentAttempts = this.getRetryAttempts(retryKey)
      
      if (currentAttempts < (strategy.maxRetries || 3)) {
        this.incrementRetryAttempts(retryKey)
        
        // Calculate backoff delay
        const delay = this.calculateBackoffDelay(currentAttempts, strategy.backoffStrategy)
        
        return {
          success: false,
          error: strategy.userMessage || this.getUserFriendlyMessage(error),
          canRetry: true,
          retryAfter: delay,
          attempt: currentAttempts + 1,
          maxAttempts: strategy.maxRetries
        }
      }
    }
    
    // Handle specific actions
    if (strategy.action) {
      await this.executeRecoveryAction(strategy.action, error, context)
    }
    
    // Clear tokens if required
    if (strategy.clearTokens) {
      this.clearAuthTokens()
    }
    
    // Log security event if required
    if (strategy.logSecurityEvent) {
      await auditService.logSecurity('authorization_error', {
        error: error.message,
        context,
        timestamp: Date.now()
      })
    }
    
    return {
      success: false,
      error: strategy.userMessage || this.getUserFriendlyMessage(error),
      canRetry: strategy.retry || false,
      handled: true
    }
  }

  /**
   * Execute recovery action
   */
  async executeRecoveryAction(action, error, context) {
    switch (action) {
      case 'redirect_login':
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
        break
        
      case 'show_permission_error':
        // This would typically show a permission denied modal
        console.warn('Permission denied:', error.message)
        break
        
      case 'show_validation_errors':
        // This would typically highlight form validation errors
        console.warn('Validation error:', error.message)
        break
        
      case 'degraded_service':
        // Switch to degraded service mode
        console.warn('Switching to degraded service mode')
        break
        
      case 'simplified_response':
        // Provide simplified response for agent errors
        console.warn('Providing simplified response due to agent error')
        break
    }
  }

  /**
   * Track error occurrences
   */
  trackError(type) {
    const count = this.errorCounts.get(type) || 0
    this.errorCounts.set(type, count + 1)

    // Check if threshold exceeded
    if (count + 1 >= this.errorThresholds[type]) {
      auditService.logSystem.alert('error_threshold_exceeded', {
        type,
        count: count + 1,
        threshold: this.errorThresholds[type]
      })
    }
  }

  /**
   * Track error patterns for analysis
   */
  trackErrorPattern(errorInfo) {
    const patternKey = `${errorInfo.type}_${errorInfo.status || 'unknown'}`
    const pattern = this.errorPatterns.get(patternKey) || {
      count: 0,
      firstSeen: Date.now(),
      lastSeen: Date.now(),
      examples: []
    }
    
    pattern.count++
    pattern.lastSeen = Date.now()
    
    // Keep last 5 examples
    pattern.examples.push({
      message: errorInfo.message,
      timestamp: errorInfo.timestamp,
      context: errorInfo.context
    })
    
    if (pattern.examples.length > 5) {
      pattern.examples.shift()
    }
    
    this.errorPatterns.set(patternKey, pattern)
  }

  /**
   * Add error to queue for batch processing
   */
  addToErrorQueue(errorInfo) {
    this.errorQueue.push(errorInfo)
    
    // Maintain queue size
    if (this.errorQueue.length > this.maxQueueSize) {
      this.errorQueue.shift()
    }
  }

  /**
   * Circuit breaker implementation
   */
  isCircuitBreakerOpen(key) {
    const breaker = this.circuitBreakers.get(key)
    
    if (!breaker) return false
    
    // Check if recovery timeout has passed
    if (breaker.state === 'open' && 
        Date.now() - breaker.lastFailure > this.circuitBreakerConfig.recoveryTimeout) {
      breaker.state = 'half-open'
      breaker.failures = 0
    }
    
    return breaker.state === 'open'
  }

  /**
   * Update circuit breaker state
   */
  updateCircuitBreaker(key, success) {
    let breaker = this.circuitBreakers.get(key) || {
      state: 'closed',
      failures: 0,
      lastFailure: null
    }
    
    if (success) {
      breaker.failures = 0
      breaker.state = 'closed'
    } else {
      breaker.failures++
      breaker.lastFailure = Date.now()
      
      if (breaker.failures >= this.circuitBreakerConfig.failureThreshold) {
        breaker.state = 'open'
      }
    }
    
    this.circuitBreakers.set(key, breaker)
  }

  /**
   * Get retry attempts for a key
   */
  getRetryAttempts(key) {
    return this.retryAttempts?.get(key) || 0
  }

  /**
   * Increment retry attempts
   */
  incrementRetryAttempts(key) {
    const current = this.getRetryAttempts(key)
    if (!this.retryAttempts) this.retryAttempts = new Map()
    this.retryAttempts.set(key, current + 1)
  }

  /**
   * Calculate backoff delay
   */
  calculateBackoffDelay(attempt, strategy = 'exponential') {
    const baseDelay = 1000 // 1 second
    
    switch (strategy) {
      case 'exponential':
        return baseDelay * Math.pow(2, attempt)
      case 'linear':
        return baseDelay * (attempt + 1)
      case 'fixed':
        return baseDelay
      default:
        return baseDelay
    }
  }

  /**
   * Get user-friendly error message
   */
  getUserFriendlyMessage(error) {
    if (error.status === 401) {
      return 'Authentication required. Please log in again.'
    }
    if (error.status === 403) {
      return 'You do not have permission to perform this action.'
    }
    if (error.status === 404) {
      return 'The requested resource was not found.'
    }
    if (error.status === 429) {
      return 'Too many requests. Please wait a moment and try again.'
    }
    if (error.status >= 500) {
      return 'Server error. Please try again later.'
    }
    
    return error.message || 'An unexpected error occurred.'
  }

  /**
   * Generate unique error ID
   */
  generateErrorId() {
    return `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Get current user ID
   */
  getCurrentUserId() {
    // This would typically get the user ID from auth context
    return localStorage.getItem('userId') || null
  }

  /**
   * Get session ID
   */
  getSessionId() {
    // This would typically get the session ID from auth context
    return localStorage.getItem('sessionId') || null
  }

  /**
   * Clear authentication tokens
   */
  clearAuthTokens() {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('userId')
    localStorage.removeItem('sessionId')
  }

  /**
   * Get error statistics
   */
  getErrorStatistics() {
    return {
      totalErrors: Array.from(this.errorCounts.values()).reduce((sum, count) => sum + count, 0),
      errorsByType: Object.fromEntries(this.errorCounts),
      errorPatterns: Object.fromEntries(this.errorPatterns),
      circuitBreakers: Object.fromEntries(this.circuitBreakers),
      queueSize: this.errorQueue.length
    }
  }

  /**
   * Reset error counts and patterns
   */
  reset() {
    this.errorCounts.clear()
    this.errorPatterns.clear()
    this.circuitBreakers.clear()
    this.errorQueue.length = 0
    if (this.retryAttempts) this.retryAttempts.clear()
  }
}

export const comprehensiveErrorHandlingService = new ComprehensiveErrorHandlingService()
