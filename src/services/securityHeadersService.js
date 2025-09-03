/**
 * Security Headers Service
 * Manages Content Security Policy and other security headers for the application
 */

import { auditService } from './auditService';

class SecurityHeadersService {
  constructor() {
    this.nonce = null;
    this.cspViolations = [];
    this.maxViolations = 100;
    this.trustedDomains = new Set([
      'self',
      'https://api.pikar-ai.com',
      'https://cdn.pikar-ai.com',
      'https://fonts.googleapis.com',
      'https://fonts.gstatic.com',
      'https://cdnjs.cloudflare.com'
    ]);
  }

  /**
   * Generate a cryptographic nonce for CSP
   * @returns {string} Base64 encoded nonce
   */
  generateNonce() {
    const array = new Uint8Array(16);
    crypto.getRandomValues(array);
    this.nonce = btoa(String.fromCharCode(...array));
    return this.nonce;
  }

  /**
   * Get current nonce
   * @returns {string} Current nonce
   */
  getCurrentNonce() {
    return this.nonce || this.generateNonce();
  }

  /**
   * Build Content Security Policy header
   * @param {Object} options - CSP configuration options
   * @returns {string} CSP header value
   */
  buildCSP(options = {}) {
    const {
      reportOnly = false,
      allowInlineStyles = false,
      allowInlineScripts = false,
      allowEval = false,
      reportUri = '/api/csp-report'
    } = options;

    const nonce = this.getCurrentNonce();
    
    const directives = {
      'default-src': ["'self'"],
      'script-src': [
        "'self'",
        `'nonce-${nonce}'`,
        'https://cdnjs.cloudflare.com',
        ...(allowInlineScripts ? ["'unsafe-inline'"] : []),
        ...(allowEval ? ["'unsafe-eval'"] : [])
      ],
      'style-src': [
        "'self'",
        `'nonce-${nonce}'`,
        'https://fonts.googleapis.com',
        'https://cdnjs.cloudflare.com',
        ...(allowInlineStyles ? ["'unsafe-inline'"] : [])
      ],
      'img-src': [
        "'self'",
        'data:',
        'blob:',
        'https:',
        'https://cdn.pikar-ai.com'
      ],
      'font-src': [
        "'self'",
        'https://fonts.gstatic.com',
        'https://cdnjs.cloudflare.com'
      ],
      'connect-src': [
        "'self'",
        'https://api.pikar-ai.com',
        'wss://api.pikar-ai.com',
        'https://base44.io'
      ],
      'media-src': [
        "'self'",
        'https://cdn.pikar-ai.com'
      ],
      'object-src': ["'none'"],
      'base-uri': ["'self'"],
      'form-action': ["'self'"],
      'frame-ancestors': ["'none'"],
      'upgrade-insecure-requests': [],
      'block-all-mixed-content': []
    };

    // Add report URI if specified
    if (reportUri) {
      directives['report-uri'] = [reportUri];
      directives['report-to'] = ['csp-endpoint'];
    }

    // Build CSP string
    const cspString = Object.entries(directives)
      .map(([directive, sources]) => {
        if (sources.length === 0) {
          return directive;
        }
        return `${directive} ${sources.join(' ')}`;
      })
      .join('; ');

    return cspString;
  }

  /**
   * Get all security headers
   * @param {Object} options - Header configuration options
   * @returns {Object} Security headers object
   */
  getSecurityHeaders(options = {}) {
    const {
      cspReportOnly = false,
      enableHSTS = true,
      hstsMaxAge = 31536000, // 1 year
      enableXFrameOptions = true,
      enableXContentTypeOptions = true,
      enableReferrerPolicy = true,
      enablePermissionsPolicy = true
    } = options;

    const headers = {};

    // Content Security Policy
    const cspHeaderName = cspReportOnly ? 'Content-Security-Policy-Report-Only' : 'Content-Security-Policy';
    headers[cspHeaderName] = this.buildCSP({ reportOnly: cspReportOnly });

    // HTTP Strict Transport Security
    if (enableHSTS) {
      headers['Strict-Transport-Security'] = `max-age=${hstsMaxAge}; includeSubDomains; preload`;
    }

    // X-Frame-Options
    if (enableXFrameOptions) {
      headers['X-Frame-Options'] = 'DENY';
    }

    // X-Content-Type-Options
    if (enableXContentTypeOptions) {
      headers['X-Content-Type-Options'] = 'nosniff';
    }

    // X-XSS-Protection (legacy, but still useful for older browsers)
    headers['X-XSS-Protection'] = '1; mode=block';

    // Referrer Policy
    if (enableReferrerPolicy) {
      headers['Referrer-Policy'] = 'strict-origin-when-cross-origin';
    }

    // Permissions Policy (formerly Feature Policy)
    if (enablePermissionsPolicy) {
      headers['Permissions-Policy'] = [
        'camera=()',
        'microphone=()',
        'geolocation=()',
        'payment=()',
        'usb=()',
        'magnetometer=()',
        'gyroscope=()',
        'accelerometer=()'
      ].join(', ');
    }

    // Cross-Origin Embedder Policy
    headers['Cross-Origin-Embedder-Policy'] = 'require-corp';

    // Cross-Origin Opener Policy
    headers['Cross-Origin-Opener-Policy'] = 'same-origin';

    // Cross-Origin Resource Policy
    headers['Cross-Origin-Resource-Policy'] = 'same-origin';

    return headers;
  }

  /**
   * Apply security headers to HTML document
   * @param {Object} options - Configuration options
   */
  applySecurityHeaders(options = {}) {
    if (typeof document === 'undefined') {
      console.warn('Security headers can only be applied in browser environment');
      return;
    }

    const headers = this.getSecurityHeaders(options);
    
    // Apply headers via meta tags (limited effectiveness, but better than nothing)
    Object.entries(headers).forEach(([name, value]) => {
      // Only certain headers can be set via meta tags
      const metaHeaders = [
        'Content-Security-Policy',
        'Content-Security-Policy-Report-Only',
        'Referrer-Policy'
      ];

      if (metaHeaders.includes(name)) {
        let metaTag = document.querySelector(`meta[http-equiv="${name}"]`);
        if (!metaTag) {
          metaTag = document.createElement('meta');
          metaTag.setAttribute('http-equiv', name);
          document.head.appendChild(metaTag);
        }
        metaTag.setAttribute('content', value);
      }
    });

    auditService.logSystem.configChange(null, 'security_headers_applied', null, 'headers_updated');
  }

  /**
   * Handle CSP violation reports
   * @param {Object} violationReport - CSP violation report
   */
  handleCSPViolation(violationReport) {
    try {
      const violation = {
        id: `csp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date().toISOString(),
        ...violationReport
      };

      // Store violation
      this.cspViolations.unshift(violation);
      
      // Keep only recent violations
      if (this.cspViolations.length > this.maxViolations) {
        this.cspViolations = this.cspViolations.slice(0, this.maxViolations);
      }

      // Log security event
      auditService.logAccess.suspiciousActivity(null, 'csp_violation', {
        blockedUri: violation['blocked-uri'],
        violatedDirective: violation['violated-directive'],
        sourceFile: violation['source-file'],
        lineNumber: violation['line-number']
      });

      // In development, log to console
      if (process.env.NODE_ENV === 'development') {
        console.warn('CSP Violation:', violation);
      }

      // In production, send to monitoring service
      if (process.env.NODE_ENV === 'production') {
        this.reportViolationToService(violation);
      }

    } catch (error) {
      console.error('Failed to handle CSP violation:', error);
    }
  }

  /**
   * Report violation to monitoring service
   * @param {Object} violation - Violation details
   */
  async reportViolationToService(violation) {
    try {
      // In a real implementation, this would send to your monitoring service
      await fetch('/api/security/csp-violation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(violation)
      });
    } catch (error) {
      console.error('Failed to report CSP violation:', error);
    }
  }

  /**
   * Get CSP violations
   * @param {Object} filters - Filter options
   * @returns {Array} Filtered violations
   */
  getCSPViolations(filters = {}) {
    let violations = [...this.cspViolations];

    if (filters.startDate) {
      violations = violations.filter(v => 
        new Date(v.timestamp) >= new Date(filters.startDate)
      );
    }

    if (filters.endDate) {
      violations = violations.filter(v => 
        new Date(v.timestamp) <= new Date(filters.endDate)
      );
    }

    if (filters.directive) {
      violations = violations.filter(v => 
        v['violated-directive']?.includes(filters.directive)
      );
    }

    return violations.slice(0, filters.limit || 50);
  }

  /**
   * Clear CSP violations
   */
  clearCSPViolations() {
    this.cspViolations = [];
    auditService.logSystem.configChange(null, 'csp_violations_cleared', null, 'violations_cleared');
  }

  /**
   * Add trusted domain
   * @param {string} domain - Domain to trust
   */
  addTrustedDomain(domain) {
    this.trustedDomains.add(domain);
    auditService.logSystem.configChange(null, 'trusted_domain_added', null, domain);
  }

  /**
   * Remove trusted domain
   * @param {string} domain - Domain to remove
   */
  removeTrustedDomain(domain) {
    this.trustedDomains.delete(domain);
    auditService.logSystem.configChange(null, 'trusted_domain_removed', domain, null);
  }

  /**
   * Get trusted domains
   * @returns {Array} List of trusted domains
   */
  getTrustedDomains() {
    return Array.from(this.trustedDomains);
  }

  /**
   * Initialize CSP violation reporting
   */
  initializeCSPReporting() {
    if (typeof document === 'undefined') return;

    // Listen for CSP violations
    document.addEventListener('securitypolicyviolation', (event) => {
      this.handleCSPViolation({
        'blocked-uri': event.blockedURI,
        'violated-directive': event.violatedDirective,
        'effective-directive': event.effectiveDirective,
        'original-policy': event.originalPolicy,
        'source-file': event.sourceFile,
        'line-number': event.lineNumber,
        'column-number': event.columnNumber,
        'status-code': event.statusCode
      });
    });

    // Set up reporting endpoint
    if ('ReportingObserver' in window) {
      const observer = new ReportingObserver((reports) => {
        reports.forEach(report => {
          if (report.type === 'csp-violation') {
            this.handleCSPViolation(report.body);
          }
        });
      });
      observer.observe();
    }
  }

  /**
   * Validate script nonce
   * @param {string} nonce - Nonce to validate
   * @returns {boolean} Whether nonce is valid
   */
  validateNonce(nonce) {
    return nonce === this.nonce;
  }

  /**
   * Create nonce-enabled script tag
   * @param {string} src - Script source
   * @param {Object} attributes - Additional attributes
   * @returns {HTMLScriptElement} Script element with nonce
   */
  createSecureScript(src, attributes = {}) {
    if (typeof document === 'undefined') {
      throw new Error('Cannot create script element outside browser environment');
    }

    const script = document.createElement('script');
    script.src = src;
    script.nonce = this.getCurrentNonce();
    
    Object.entries(attributes).forEach(([key, value]) => {
      script.setAttribute(key, value);
    });

    return script;
  }

  /**
   * Create nonce-enabled style tag
   * @param {string} css - CSS content
   * @param {Object} attributes - Additional attributes
   * @returns {HTMLStyleElement} Style element with nonce
   */
  createSecureStyle(css, attributes = {}) {
    if (typeof document === 'undefined') {
      throw new Error('Cannot create style element outside browser environment');
    }

    const style = document.createElement('style');
    style.textContent = css;
    style.nonce = this.getCurrentNonce();
    
    Object.entries(attributes).forEach(([key, value]) => {
      style.setAttribute(key, value);
    });

    return style;
  }
}

// Create and export singleton instance
export const securityHeadersService = new SecurityHeadersService();
