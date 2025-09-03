/**
 * Security Initialization Service
 * Initializes all security services and applies security configurations
 */

import { securityHeadersService } from './securityHeadersService';
import { encryptionService } from './encryptionService';
import { secureStorageService } from './secureStorageService';
import { auditService } from './auditService';
import { errorHandlingService } from './errorHandlingService';
import { secretsManagementService } from './secretsManagementService';

import { typeSafetyImplementationService } from './typeSafetyImplementationService';
import { apiResponseValidationService } from './apiResponseValidationService';
import { performanceOptimizationService } from './performanceOptimizationService';
import { accessibilityService } from './accessibilityService';
import { environmentConfig } from '@/config/environment';

class SecurityInitService {
  constructor() {
    this.initialized = false;
    this.securityConfig = {
      enableCSP: environmentConfig.getSecurityConfig().enableCSP,
      enableHSTS: environmentConfig.getSecurityConfig().enableHSTS,
      enableEncryption: true,
      enableSecureStorage: true,
      enableAuditLogging: true,
      enableErrorHandling: true,
      enableSecretsManagement: true,
      enableBase44Verification: false,
      enableTypeSafety: true,
      enableApiResponseValidation: true,
      enablePerformanceOptimization: true,
      enableAccessibility: true,
      cspReportOnly: environmentConfig.isDevelopment(),
      strictMode: environmentConfig.isProduction()
    };
  }

  /**
   * Initialize all security services
   * @param {Object} config - Security configuration
   * @returns {Promise<boolean>} Initialization success
   */
  async initialize(config = {}) {
    if (this.initialized) {
      console.warn('Security services already initialized');
      return true;
    }

    try {
      // Merge configuration
      this.securityConfig = { ...this.securityConfig, ...config };

      console.log('🔒 Initializing PIKAR AI Security Services...');

      // 1. Initialize audit logging first
      if (this.securityConfig.enableAuditLogging) {
        await this.initializeAuditLogging();
      }

      // 2. Initialize secrets management
      if (this.securityConfig.enableSecretsManagement) {
        await this.initializeSecretsManagement();
      }

      // 3. Initialize error handling
      if (this.securityConfig.enableErrorHandling) {
        await this.initializeErrorHandling();
      }

      // 4. Initialize encryption services
      if (this.securityConfig.enableEncryption) {
        await this.initializeEncryption();
      }

      // 5. Initialize secure storage
      if (this.securityConfig.enableSecureStorage) {
        await this.initializeSecureStorage();
      }

      // 6. Initialize security headers and CSP
      if (this.securityConfig.enableCSP) {
        await this.initializeSecurityHeaders();
      }


      // 8. Initialize type safety implementation
      if (this.securityConfig.enableTypeSafety) {
        await this.initializeTypeSafety();
      }

      // 9. Initialize API response validation
      if (this.securityConfig.enableApiResponseValidation) {
        await this.initializeApiResponseValidation();
      }

      // 10. Initialize performance optimization
      if (this.securityConfig.enablePerformanceOptimization) {
        await this.initializePerformanceOptimization();
      }

      // 11. Initialize accessibility features
      if (this.securityConfig.enableAccessibility) {
        await this.initializeAccessibility();
      }

      // 12. Set up security monitoring
      await this.initializeSecurityMonitoring();

      // 6. Apply runtime security policies
      await this.applyRuntimeSecurity();

      this.initialized = true;
      
      auditService.logSystem.configChange(null, 'security_services_initialized', null, 'all_services');
      console.log('✅ Security services initialized successfully');

      return true;
    } catch (error) {
      auditService.logSystem.error(error, 'security_initialization');
      console.error('❌ Failed to initialize security services:', error);
      return false;
    }
  }

  /**
   * Initialize audit logging
   */
  async initializeAuditLogging() {
    try {
      // Audit service is already a singleton, just log initialization
      auditService.logSystem.configChange(null, 'audit_service_initialized', null, 'initialized');
      console.log('📋 Audit logging initialized');
    } catch (error) {
      console.error('Failed to initialize audit logging:', error);
      throw error;
    }
  }

  /**
   * Initialize secrets management
   */
  async initializeSecretsManagement() {
    try {
      await secretsManagementService.initialize();
      console.log('🔐 Secrets management initialized');
    } catch (error) {
      console.error('Failed to initialize secrets management:', error);
      throw error;
    }
  }

  /**
   * Initialize error handling services
   */
  async initializeErrorHandling() {
    try {
      errorHandlingService.initialize();
      console.log('🚨 Error handling initialized');
    } catch (error) {
      console.error('Failed to initialize error handling:', error);
      throw error;
    }
  }


  /**
   * Initialize type safety implementation
   */
  async initializeTypeSafety() {
    try {
      const report = await typeSafetyImplementationService.initialize();

      if (report.summary.implementationRate < 90) {
        console.warn('⚠️ Type safety implementation rate is low:', report.summary.implementationRate + '%');
        console.warn('Pending components:', report.pending);
      }

      if (report.summary.errorCount > 0) {
        console.warn('⚠️ Type safety implementation errors:', report.errors);
      }

      console.log('🔒 Type safety implementation initialized');
    } catch (error) {
      console.error('Failed to initialize type safety implementation:', error);
      throw error;
    }
  }

  /**
   * Initialize API response validation
   */
  async initializeApiResponseValidation() {
    try {
      await apiResponseValidationService.initialize();

      const stats = apiResponseValidationService.getValidationStats();
      console.log('🔍 API response validation initialized');
      console.log(`📊 Registered ${stats.registeredSchemas} response schemas`);

    } catch (error) {
      console.error('Failed to initialize API response validation:', error);
      throw error;
    }
  }

  /**
   * Initialize performance optimization
   */
  async initializePerformanceOptimization() {
    try {
      await performanceOptimizationService.initialize();

      const metrics = performanceOptimizationService.getPerformanceMetrics();
      console.log('⚡ Performance optimization initialized');
      console.log('📊 Performance monitoring active');

    } catch (error) {
      console.error('Failed to initialize performance optimization:', error);
      throw error;
    }
  }

  /**
   * Initialize accessibility features
   */
  async initializeAccessibility() {
    try {
      await accessibilityService.initialize();

      const stats = accessibilityService.getAccessibilityStats();
      console.log('♿ Accessibility features initialized');
      console.log('🎯 Keyboard navigation and screen reader support active');

    } catch (error) {
      console.error('Failed to initialize accessibility features:', error);
      throw error;
    }
  }

  /**
   * Initialize encryption services
   */
  async initializeEncryption() {
    try {
      // Generate initial encryption key for the session
      await encryptionService.generateKey();
      
      // Clear any existing key cache for fresh start
      encryptionService.clearKeyCache();
      
      console.log('🔐 Encryption services initialized');
    } catch (error) {
      console.error('Failed to initialize encryption:', error);
      throw error;
    }
  }

  /**
   * Initialize secure storage
   */
  async initializeSecureStorage() {
    try {
      await secureStorageService.initialize();
      console.log('💾 Secure storage initialized');
    } catch (error) {
      console.error('Failed to initialize secure storage:', error);
      throw error;
    }
  }

  /**
   * Initialize security headers and CSP
   */
  async initializeSecurityHeaders() {
    try {
      // Generate nonce for CSP
      securityHeadersService.generateNonce();
      
      // Apply security headers
      securityHeadersService.applySecurityHeaders({
        cspReportOnly: this.securityConfig.cspReportOnly,
        enableHSTS: this.securityConfig.enableHSTS
      });

      // Initialize CSP violation reporting
      securityHeadersService.initializeCSPReporting();

      console.log('🛡️ Security headers and CSP initialized');
    } catch (error) {
      console.error('Failed to initialize security headers:', error);
      throw error;
    }
  }

  /**
   * Initialize security monitoring
   */
  async initializeSecurityMonitoring() {
    try {
      // Set up global error handler for security events
      window.addEventListener('error', (event) => {
        auditService.logSystem.error(event.error, 'global_error_handler');
      });

      // Set up unhandled promise rejection handler
      window.addEventListener('unhandledrejection', (event) => {
        auditService.logSystem.error(event.reason, 'unhandled_promise_rejection');
      });

      // Monitor for suspicious activity
      this.setupSuspiciousActivityMonitoring();

      console.log('👁️ Security monitoring initialized');
    } catch (error) {
      console.error('Failed to initialize security monitoring:', error);
      throw error;
    }
  }

  /**
   * Apply runtime security policies
   */
  async applyRuntimeSecurity() {
    try {
      // Disable dangerous functions in production
      if (this.securityConfig.strictMode) {
        this.disableDangerousFunctions();
      }

      // Set up secure defaults
      this.applySecureDefaults();

      // Initialize security timers
      this.initializeSecurityTimers();

      console.log('⚡ Runtime security policies applied');
    } catch (error) {
      console.error('Failed to apply runtime security:', error);
      throw error;
    }
  }

  /**
   * Set up suspicious activity monitoring
   */
  setupSuspiciousActivityMonitoring() {
    // Monitor for rapid-fire requests
    let requestCount = 0;
    let requestWindow = Date.now();

    const originalFetch = window.fetch;
    window.fetch = function(...args) {
      requestCount++;
      const now = Date.now();
      
      // Reset counter every minute
      if (now - requestWindow > 60000) {
        requestCount = 1;
        requestWindow = now;
      }
      
      // Flag suspicious activity (more than 100 requests per minute)
      if (requestCount > 100) {
        auditService.logAccess.suspiciousActivity(null, 'rapid_requests', {
          requestCount,
          timeWindow: now - requestWindow,
          url: args[0]
        });
      }
      
      return originalFetch.apply(this, args);
    };

    // Monitor for console access attempts
    let consoleAccessCount = 0;
    const originalLog = console.log;
    console.log = function(...args) {
      consoleAccessCount++;
      
      // Flag excessive console usage (potential debugging/tampering)
      if (consoleAccessCount > 50) {
        auditService.logAccess.suspiciousActivity(null, 'excessive_console_access', {
          accessCount: consoleAccessCount
        });
      }
      
      return originalLog.apply(this, args);
    };
  }

  /**
   * Disable dangerous functions in production
   */
  disableDangerousFunctions() {
    if (process.env.NODE_ENV !== 'production') return;

    // Disable eval
    window.eval = function() {
      auditService.logAccess.suspiciousActivity(null, 'eval_attempt', {});
      throw new Error('eval() is disabled for security reasons');
    };

    // Disable Function constructor
    const OriginalFunction = window.Function;
    window.Function = function() {
      auditService.logAccess.suspiciousActivity(null, 'function_constructor_attempt', {});
      throw new Error('Function constructor is disabled for security reasons');
    };

    // Disable setTimeout/setInterval with string arguments
    const originalSetTimeout = window.setTimeout;
    window.setTimeout = function(callback, delay, ...args) {
      if (typeof callback === 'string') {
        auditService.logAccess.suspiciousActivity(null, 'string_timeout_attempt', {});
        throw new Error('setTimeout with string callback is disabled for security reasons');
      }
      return originalSetTimeout.call(this, callback, delay, ...args);
    };

    const originalSetInterval = window.setInterval;
    window.setInterval = function(callback, delay, ...args) {
      if (typeof callback === 'string') {
        auditService.logAccess.suspiciousActivity(null, 'string_interval_attempt', {});
        throw new Error('setInterval with string callback is disabled for security reasons');
      }
      return originalSetInterval.call(this, callback, delay, ...args);
    };
  }

  /**
   * Apply secure defaults
   */
  applySecureDefaults() {
    // Prevent right-click in production
    if (this.securityConfig.strictMode) {
      document.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        auditService.logAccess.suspiciousActivity(null, 'context_menu_attempt', {});
      });

      // Prevent F12 and other dev tools shortcuts
      document.addEventListener('keydown', (e) => {
        if (e.key === 'F12' || 
            (e.ctrlKey && e.shiftKey && e.key === 'I') ||
            (e.ctrlKey && e.shiftKey && e.key === 'C') ||
            (e.ctrlKey && e.key === 'U')) {
          e.preventDefault();
          auditService.logAccess.suspiciousActivity(null, 'devtools_shortcut_attempt', {
            key: e.key,
            ctrlKey: e.ctrlKey,
            shiftKey: e.shiftKey
          });
        }
      });
    }

    // Set secure cookie defaults
    if (document.cookie) {
      document.cookie = document.cookie.replace(/(?:^|; )([^=]+)=([^;]*)/g, 
        '$1=$2; Secure; SameSite=Strict; HttpOnly');
    }
  }

  /**
   * Initialize security timers
   */
  initializeSecurityTimers() {
    // Periodic security health check
    setInterval(() => {
      this.performSecurityHealthCheck();
    }, 5 * 60 * 1000); // Every 5 minutes

    // Periodic cleanup
    setInterval(() => {
      this.performSecurityCleanup();
    }, 30 * 60 * 1000); // Every 30 minutes
  }

  /**
   * Perform security health check
   */
  async performSecurityHealthCheck() {
    try {
      const healthStatus = {
        timestamp: new Date().toISOString(),
        encryptionService: !!encryptionService,
        secureStorage: !!secureStorageService,
        auditService: !!auditService,
        cspViolations: securityHeadersService.getCSPViolations().length,
        storageStats: secureStorageService.getStorageStats()
      };

      // Log health check
      auditService.logSystem.configChange(null, 'security_health_check', null, JSON.stringify(healthStatus));

      // Alert on issues
      if (healthStatus.cspViolations > 10) {
        console.warn('⚠️ High number of CSP violations detected:', healthStatus.cspViolations);
      }

    } catch (error) {
      auditService.logSystem.error(error, 'security_health_check');
    }
  }

  /**
   * Perform security cleanup
   */
  async performSecurityCleanup() {
    try {
      // Clean up expired secure storage
      const cleanedItems = await secureStorageService.cleanup();
      
      // Clear old CSP violations
      const violations = securityHeadersService.getCSPViolations();
      if (violations.length > 50) {
        securityHeadersService.clearCSPViolations();
      }

      if (cleanedItems > 0) {
        auditService.logSystem.configChange(null, 'security_cleanup', null, `${cleanedItems}_items_cleaned`);
      }

    } catch (error) {
      auditService.logSystem.error(error, 'security_cleanup');
    }
  }

  /**
   * Get security status
   * @returns {Object} Current security status
   */
  getSecurityStatus() {
    return {
      initialized: this.initialized,
      config: this.securityConfig,
      services: {
        encryption: !!encryptionService,
        secureStorage: !!secureStorageService,
        securityHeaders: !!securityHeadersService,
        auditLogging: !!auditService
      },
      metrics: {
        cspViolations: securityHeadersService.getCSPViolations().length,
        storageStats: secureStorageService.getStorageStats(),
        auditEvents: auditService.getSecurityMetrics()
      }
    };
  }

  /**
   * Shutdown security services
   */
  async shutdown() {
    try {
      // Clear sensitive data
      encryptionService.clearKeyCache();
      await secureStorageService.clear();
      
      // Log shutdown
      auditService.logSystem.configChange(null, 'security_services_shutdown', null, 'shutdown');
      
      this.initialized = false;
      console.log('🔒 Security services shut down');
    } catch (error) {
      console.error('Failed to shutdown security services:', error);
    }
  }
}

// Create and export singleton instance
export const securityInitService = new SecurityInitService();
