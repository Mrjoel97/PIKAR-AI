/**
 * Security Audit Service
 * Handles logging and monitoring of security events
 */

class AuditService {
  constructor() {
    this.events = [];
    this.maxEvents = 1000;
    this.storageKey = 'pikar_audit_log';
    this.loadEvents();
  }

  /**
   * Log a security event
   * @param {string} eventType - Type of event
   * @param {Object} data - Event data
   * @param {string} severity - Event severity (low, medium, high, critical)
   */
  logEvent(eventType, data = {}, severity = 'medium') {
    const event = {
      id: this.generateEventId(),
      type: eventType,
      severity,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      sessionId: this.getSessionId(),
      data: this.sanitizeData(data)
    };

    this.events.unshift(event);
    
    // Keep only the most recent events
    if (this.events.length > this.maxEvents) {
      this.events = this.events.slice(0, this.maxEvents);
    }

    this.saveEvents();
    this.handleEvent(event);
  }

  /**
   * Log authentication events
   */
  logAuth = {
    loginAttempt: (email, success, reason = null) => {
      this.logEvent('auth_login_attempt', {
        email: this.hashEmail(email),
        success,
        reason,
        ip: this.getClientIP()
      }, success ? 'low' : 'medium');
    },

    loginSuccess: (userId, email) => {
      this.logEvent('auth_login_success', {
        userId,
        email: this.hashEmail(email),
        ip: this.getClientIP()
      }, 'low');
    },

    loginFailure: (email, reason, attemptCount = 1) => {
      this.logEvent('auth_login_failure', {
        email: this.hashEmail(email),
        reason,
        attemptCount,
        ip: this.getClientIP()
      }, attemptCount > 3 ? 'high' : 'medium');
    },

    logout: (userId) => {
      this.logEvent('auth_logout', {
        userId
      }, 'low');
    },

    tokenRefresh: (userId, success) => {
      this.logEvent('auth_token_refresh', {
        userId,
        success
      }, success ? 'low' : 'medium');
    },

    passwordChange: (userId) => {
      this.logEvent('auth_password_change', {
        userId
      }, 'medium');
    },

    accountLockout: (email, reason) => {
      this.logEvent('auth_account_lockout', {
        email: this.hashEmail(email),
        reason,
        ip: this.getClientIP()
      }, 'high');
    }
  };

  /**
   * Log access control events
   */
  logAccess = {
    permissionDenied: (userId, resource, requiredPermission) => {
      this.logEvent('access_permission_denied', {
        userId,
        resource,
        requiredPermission,
        userTier: this.getCurrentUserTier()
      }, 'medium');
    },

    tierUpgrade: (userId, fromTier, toTier) => {
      this.logEvent('access_tier_upgrade', {
        userId,
        fromTier,
        toTier
      }, 'low');
    },

    suspiciousActivity: (userId, activity, details) => {
      this.logEvent('access_suspicious_activity', {
        userId,
        activity,
        details,
        ip: this.getClientIP()
      }, 'high');
    }
  };

  /**
   * Log data events
   */
  logData = {
    export: (userId, dataType, recordCount) => {
      this.logEvent('data_export', {
        userId,
        dataType,
        recordCount
      }, 'medium');
    },

    deletion: (userId, dataType, recordId) => {
      this.logEvent('data_deletion', {
        userId,
        dataType,
        recordId
      }, 'medium');
    },

    modification: (userId, dataType, recordId, changes) => {
      this.logEvent('data_modification', {
        userId,
        dataType,
        recordId,
        changesCount: Object.keys(changes).length
      }, 'low');
    }
  };

  /**
   * Log system events
   */
  logSystem = {
    error: (error, context) => {
      this.logEvent('system_error', {
        error: error.message,
        stack: error.stack,
        context
      }, 'high');
    },

    configChange: (userId, setting, oldValue, newValue) => {
      this.logEvent('system_config_change', {
        userId,
        setting,
        oldValue: this.sanitizeValue(oldValue),
        newValue: this.sanitizeValue(newValue)
      }, 'medium');
    }
  };

  /**
   * Get events with filtering
   * @param {Object} filters - Filter criteria
   * @returns {Array} Filtered events
   */
  getEvents(filters = {}) {
    let filteredEvents = [...this.events];

    if (filters.type) {
      filteredEvents = filteredEvents.filter(event => event.type === filters.type);
    }

    if (filters.severity) {
      filteredEvents = filteredEvents.filter(event => event.severity === filters.severity);
    }

    if (filters.startDate) {
      filteredEvents = filteredEvents.filter(event => 
        new Date(event.timestamp) >= new Date(filters.startDate)
      );
    }

    if (filters.endDate) {
      filteredEvents = filteredEvents.filter(event => 
        new Date(event.timestamp) <= new Date(filters.endDate)
      );
    }

    if (filters.userId) {
      filteredEvents = filteredEvents.filter(event => 
        event.data.userId === filters.userId
      );
    }

    return filteredEvents.slice(0, filters.limit || 100);
  }

  /**
   * Get security metrics
   * @returns {Object} Security metrics
   */
  getSecurityMetrics() {
    const last24Hours = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const recentEvents = this.events.filter(event => 
      new Date(event.timestamp) >= last24Hours
    );

    return {
      totalEvents: this.events.length,
      recentEvents: recentEvents.length,
      failedLogins: recentEvents.filter(e => e.type === 'auth_login_failure').length,
      permissionDenials: recentEvents.filter(e => e.type === 'access_permission_denied').length,
      suspiciousActivity: recentEvents.filter(e => e.type === 'access_suspicious_activity').length,
      criticalEvents: recentEvents.filter(e => e.severity === 'critical').length,
      highSeverityEvents: recentEvents.filter(e => e.severity === 'high').length
    };
  }

  /**
   * Handle event based on severity
   * @param {Object} event - Event to handle
   */
  handleEvent(event) {
    // In production, you would send high/critical events to monitoring service
    if (event.severity === 'critical' || event.severity === 'high') {
      console.warn('High severity security event:', event);
      
      // Could trigger alerts, notifications, etc.
      this.triggerAlert(event);
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log('Security Event:', event);
    }
  }

  /**
   * Trigger security alert
   * @param {Object} event - Event that triggered alert
   */
  triggerAlert(event) {
    // In production, this would integrate with alerting systems
    // For now, just store the alert
    const alert = {
      id: this.generateEventId(),
      eventId: event.id,
      timestamp: new Date().toISOString(),
      acknowledged: false
    };

    const alerts = JSON.parse(localStorage.getItem('security_alerts') || '[]');
    alerts.unshift(alert);
    
    // Keep only last 50 alerts
    if (alerts.length > 50) {
      alerts.splice(50);
    }
    
    localStorage.setItem('security_alerts', JSON.stringify(alerts));
  }

  // Utility methods
  generateEventId() {
    return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  getSessionId() {
    let sessionId = sessionStorage.getItem('session_id');
    if (!sessionId) {
      sessionId = `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('session_id', sessionId);
    }
    return sessionId;
  }

  hashEmail(email) {
    // Simple hash for privacy (in production, use proper hashing)
    return btoa(email).substr(0, 8) + '***';
  }

  getClientIP() {
    // In production, this would be handled server-side
    return 'client-side';
  }

  getCurrentUserTier() {
    try {
      const userData = JSON.parse(localStorage.getItem('pikar_user_data') || '{}');
      return userData.tier || 'unknown';
    } catch {
      return 'unknown';
    }
  }

  sanitizeData(data) {
    // Remove sensitive information from logged data
    const sanitized = { ...data };
    const sensitiveFields = ['password', 'token', 'secret', 'key'];
    
    for (const field of sensitiveFields) {
      if (sanitized[field]) {
        sanitized[field] = '[REDACTED]';
      }
    }
    
    return sanitized;
  }

  sanitizeValue(value) {
    if (typeof value === 'string' && value.length > 100) {
      return value.substr(0, 100) + '...';
    }
    return value;
  }

  loadEvents() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        this.events = JSON.parse(stored);
      }
    } catch (error) {
      console.error('Failed to load audit events:', error);
      this.events = [];
    }
  }

  saveEvents() {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.events));
    } catch (error) {
      console.error('Failed to save audit events:', error);
    }
  }

  /**
   * Clear all events (admin only)
   */
  clearEvents() {
    this.events = [];
    this.saveEvents();
    this.logEvent('system_audit_cleared', {}, 'medium');
  }

  /**
   * Export events for analysis
   * @param {Object} filters - Export filters
   * @returns {string} CSV formatted events
   */
  exportEvents(filters = {}) {
    const events = this.getEvents(filters);
    const headers = ['Timestamp', 'Type', 'Severity', 'User ID', 'Details'];
    
    const csv = [
      headers.join(','),
      ...events.map(event => [
        event.timestamp,
        event.type,
        event.severity,
        event.data.userId || 'N/A',
        JSON.stringify(event.data).replace(/,/g, ';')
      ].join(','))
    ].join('\n');

    return csv;
  }
}

// Create and export singleton instance
export const auditService = new AuditService();
