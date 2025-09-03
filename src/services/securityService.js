/**
 * Security Service
 * Comprehensive security utilities and validation functions
 */

import CryptoJS from 'crypto-js'
import DOMPurify from 'dompurify'
import { auditService } from './auditService'
import { environmentConfig } from '@/config/environment'

class SecurityService {
  constructor() {
    this.encryptionKey = environmentConfig.security.encryptionKey
    this.rateLimitStore = new Map()
    this.blockedIPs = new Set()
    this.lockedAccounts = new Map()
    this.csrfTokens = new Map()
    
    // Security patterns
    this.sqlInjectionPatterns = [
      /(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)/i,
      /(--|\/\*|\*\/|;|'|"|\||&)/,
      /(\b(OR|AND)\s+\d+\s*=\s*\d+)/i,
      /(UNION\s+SELECT)/i,
      /(DROP\s+TABLE)/i
    ]
    
    this.xssPatterns = [
      /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
      /<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi,
      /javascript:/gi,
      /on\w+\s*=/gi,
      /<img[^>]+onerror/gi,
      /<svg[^>]+onload/gi
    ]
    
    this.commandInjectionPatterns = [
      /[;&|`$(){}[\]]/,
      /(cat|ls|pwd|whoami|id|uname)/i,
      /(rm|mv|cp|chmod|chown)/i,
      /(\|\||&&|;)/
    ]
  }

  /**
   * Validate and sanitize user input
   */
  validateInput(input, options = {}) {
    const errors = []
    
    if (!input && options.required) {
      errors.push('Input is required')
      return { isValid: false, errors }
    }
    
    if (typeof input !== 'string') {
      input = String(input)
    }
    
    // Check length constraints
    if (options.minLength && input.length < options.minLength) {
      errors.push(`Input must be at least ${options.minLength} characters`)
    }
    
    if (options.maxLength && input.length > options.maxLength) {
      errors.push(`Input must not exceed ${options.maxLength} characters`)
    }
    
    // Check for malicious patterns
    if (this.detectSQLInjection(input)) {
      errors.push('Potentially malicious SQL patterns detected')
    }
    
    if (this.detectXSS(input)) {
      errors.push('Potentially malicious script patterns detected')
    }
    
    if (this.detectCommandInjection(input)) {
      errors.push('Potentially malicious command patterns detected')
    }
    
    // Validate format if specified
    if (options.format) {
      if (!this.validateFormat(input, options.format)) {
        errors.push(`Invalid ${options.format} format`)
      }
    }
    
    return {
      isValid: errors.length === 0,
      errors,
      sanitized: this.sanitizeInput(input)
    }
  }

  /**
   * Sanitize user input
   */
  sanitizeInput(input) {
    if (typeof input !== 'string') {
      input = String(input)
    }
    
    // Remove HTML tags and scripts
    let sanitized = DOMPurify.sanitize(input, { 
      ALLOWED_TAGS: [],
      ALLOWED_ATTR: []
    })
    
    // Escape special characters
    sanitized = sanitized
      .replace(/[<>]/g, '')
      .replace(/['"]/g, '')
      .replace(/[;&|`$(){}[\]]/g, '')
      .trim()
    
    return sanitized
  }

  /**
   * Detect SQL injection attempts
   */
  detectSQLInjection(input) {
    if (typeof input !== 'string') {
      input = String(input)
    }
    
    return this.sqlInjectionPatterns.some(pattern => pattern.test(input))
  }

  /**
   * Detect XSS attempts
   */
  detectXSS(input) {
    if (typeof input !== 'string') {
      input = String(input)
    }
    
    return this.xssPatterns.some(pattern => pattern.test(input))
  }

  /**
   * Detect command injection attempts
   */
  detectCommandInjection(input) {
    if (typeof input !== 'string') {
      input = String(input)
    }
    
    return this.commandInjectionPatterns.some(pattern => pattern.test(input))
  }

  /**
   * Validate input format
   */
  validateFormat(input, format) {
    const patterns = {
      email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      phone: /^\+?[\d\s\-\(\)]{10,}$/,
      url: /^https?:\/\/.+/,
      uuid: /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
      alphanumeric: /^[a-zA-Z0-9]+$/,
      numeric: /^\d+$/
    }
    
    return patterns[format] ? patterns[format].test(input) : true
  }

  /**
   * Check password strength
   */
  checkPasswordStrength(password) {
    const checks = {
      length: password.length >= 8,
      lowercase: /[a-z]/.test(password),
      uppercase: /[A-Z]/.test(password),
      numbers: /\d/.test(password),
      symbols: /[!@#$%^&*(),.?":{}|<>]/.test(password),
      noCommon: !this.isCommonPassword(password)
    }
    
    const score = Object.values(checks).filter(Boolean).length
    const feedback = []
    
    if (!checks.length) feedback.push('Password must be at least 8 characters long')
    if (!checks.lowercase) feedback.push('Password must contain lowercase letters')
    if (!checks.uppercase) feedback.push('Password must contain uppercase letters')
    if (!checks.numbers) feedback.push('Password must contain numbers')
    if (!checks.symbols) feedback.push('Password must contain special characters')
    if (!checks.noCommon) feedback.push('Password is too common')
    
    return {
      score,
      strength: this.getPasswordStrengthLabel(score),
      feedback,
      checks
    }
  }

  /**
   * Check if password is commonly used
   */
  isCommonPassword(password) {
    const commonPasswords = [
      'password', '123456', 'password123', 'admin', 'qwerty',
      'letmein', 'welcome', 'monkey', '1234567890', 'abc123'
    ]
    
    return commonPasswords.includes(password.toLowerCase())
  }

  /**
   * Get password strength label
   */
  getPasswordStrengthLabel(score) {
    if (score <= 2) return 'weak'
    if (score <= 4) return 'medium'
    return 'strong'
  }

  /**
   * Rate limiting check
   */
  rateLimitCheck(key, limit = 10, windowMs = 60000) {
    const now = Date.now()
    const windowStart = now - windowMs
    
    if (!this.rateLimitStore.has(key)) {
      this.rateLimitStore.set(key, [])
    }
    
    const requests = this.rateLimitStore.get(key)
    
    // Remove old requests outside the window
    const validRequests = requests.filter(timestamp => timestamp > windowStart)
    
    if (validRequests.length >= limit) {
      return {
        allowed: false,
        remaining: 0,
        resetTime: validRequests[0] + windowMs
      }
    }
    
    // Add current request
    validRequests.push(now)
    this.rateLimitStore.set(key, validRequests)
    
    return {
      allowed: true,
      remaining: limit - validRequests.length,
      resetTime: now + windowMs
    }
  }

  /**
   * Check if account is locked
   */
  isAccountLocked(identifier) {
    const lockInfo = this.lockedAccounts.get(identifier)
    
    if (!lockInfo) return false
    
    // Check if lock has expired
    if (Date.now() > lockInfo.expiresAt) {
      this.lockedAccounts.delete(identifier)
      return false
    }
    
    return true
  }

  /**
   * Lock account after failed attempts
   */
  lockAccount(identifier, duration = 300000) { // 5 minutes default
    const expiresAt = Date.now() + duration
    
    this.lockedAccounts.set(identifier, {
      lockedAt: Date.now(),
      expiresAt,
      attempts: this.getFailedAttempts(identifier)
    })
    
    auditService.logSecurity('account_locked', {
      identifier,
      duration,
      expiresAt
    })
  }

  /**
   * Get failed login attempts count
   */
  getFailedAttempts(identifier) {
    const key = `failed_attempts_${identifier}`
    const attempts = this.rateLimitStore.get(key) || []
    const recentAttempts = attempts.filter(timestamp => 
      Date.now() - timestamp < 300000 // Last 5 minutes
    )
    
    return recentAttempts.length
  }

  /**
   * Record failed login attempt
   */
  recordFailedAttempt(identifier) {
    const key = `failed_attempts_${identifier}`
    const attempts = this.rateLimitStore.get(key) || []
    
    attempts.push(Date.now())
    this.rateLimitStore.set(key, attempts)
    
    // Lock account after 5 failed attempts
    if (attempts.length >= 5) {
      this.lockAccount(identifier)
    }
  }

  /**
   * Clear failed attempts
   */
  clearFailedAttempts(identifier) {
    const key = `failed_attempts_${identifier}`
    this.rateLimitStore.delete(key)
  }

  /**
   * Check if IP is blocked
   */
  isIPBlocked(ip) {
    return this.blockedIPs.has(ip)
  }

  /**
   * Block IP address
   */
  blockIP(ip, reason = 'suspicious_activity') {
    this.blockedIPs.add(ip)
    
    auditService.logSecurity('ip_blocked', {
      ip,
      reason,
      timestamp: Date.now()
    })
  }

  /**
   * Unblock IP address
   */
  unblockIP(ip) {
    this.blockedIPs.delete(ip)
    
    auditService.logSecurity('ip_unblocked', {
      ip,
      timestamp: Date.now()
    })
  }

  /**
   * Generate CSRF token
   */
  generateCSRFToken(sessionId) {
    const token = CryptoJS.lib.WordArray.random(32).toString()
    const expiresAt = Date.now() + 3600000 // 1 hour
    
    this.csrfTokens.set(token, {
      sessionId,
      expiresAt
    })
    
    return token
  }

  /**
   * Validate CSRF token
   */
  validateCSRFToken(token, sessionId) {
    const tokenInfo = this.csrfTokens.get(token)
    
    if (!tokenInfo) return false
    
    // Check if token has expired
    if (Date.now() > tokenInfo.expiresAt) {
      this.csrfTokens.delete(token)
      return false
    }
    
    // Check if token belongs to the session
    if (tokenInfo.sessionId !== sessionId) {
      return false
    }
    
    return true
  }

  /**
   * Encrypt sensitive data
   */
  encryptSensitiveData(data) {
    if (!data) return data
    
    try {
      return CryptoJS.AES.encrypt(JSON.stringify(data), this.encryptionKey).toString()
    } catch (error) {
      console.error('Encryption error:', error)
      return data
    }
  }

  /**
   * Decrypt sensitive data
   */
  decryptSensitiveData(encryptedData) {
    if (!encryptedData) return encryptedData
    
    try {
      const bytes = CryptoJS.AES.decrypt(encryptedData, this.encryptionKey)
      return JSON.parse(bytes.toString(CryptoJS.enc.Utf8))
    } catch (error) {
      console.error('Decryption error:', error)
      return encryptedData
    }
  }

  /**
   * Mask sensitive data for logging
   */
  maskSensitiveData(data) {
    if (!data || typeof data !== 'object') return data
    
    const sensitiveFields = ['password', 'token', 'secret', 'key', 'ssn', 'creditCard', 'phone']
    const masked = { ...data }
    
    for (const [key, value] of Object.entries(masked)) {
      if (sensitiveFields.some(field => key.toLowerCase().includes(field))) {
        if (typeof value === 'string') {
          if (key.toLowerCase().includes('email')) {
            // Mask email: user@example.com -> u***@example.com
            masked[key] = value.replace(/^(.{1}).*(@.*)$/, '$1***$2')
          } else if (key.toLowerCase().includes('phone')) {
            // Mask phone: +1234567890 -> +123***7890
            masked[key] = value.replace(/^(.{4}).*(.{4})$/, '$1***$2')
          } else {
            // Mask other sensitive fields
            masked[key] = '***'
          }
        }
      }
    }
    
    return masked
  }

  /**
   * Validate file upload security
   */
  validateFileUpload(file) {
    const allowedTypes = [
      'image/jpeg', 'image/png', 'image/gif', 'image/webp',
      'application/pdf', 'text/plain', 'text/csv',
      'application/json', 'application/xml'
    ]
    
    const maxSize = 10 * 1024 * 1024 // 10MB
    const dangerousExtensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com']
    
    const errors = []
    
    // Check file type
    if (!allowedTypes.includes(file.type)) {
      errors.push('File type not allowed')
    }
    
    // Check file size
    if (file.size > maxSize) {
      errors.push('File size exceeds limit')
    }
    
    // Check file extension
    const extension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
    if (dangerousExtensions.includes(extension)) {
      errors.push('Potentially dangerous file extension')
    }
    
    // Check for embedded scripts in filename
    if (this.detectXSS(file.name)) {
      errors.push('Potentially malicious filename')
    }
    
    return {
      isValid: errors.length === 0,
      errors,
      reason: errors.join(', ')
    }
  }

  /**
   * Generate security headers
   */
  getSecurityHeaders() {
    return {
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block',
      'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
      'Content-Security-Policy': this.generateCSP(),
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }
  }

  /**
   * Generate Content Security Policy
   */
  generateCSP() {
    const directives = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      "font-src 'self' https://fonts.gstatic.com",
      "img-src 'self' data: https:",
      "connect-src 'self' https://api.pikar-ai.com",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'"
    ]
    
    return directives.join('; ')
  }

  /**
   * Validate security headers
   */
  validateSecurityHeaders(headers) {
    const requiredHeaders = [
      'X-Content-Type-Options',
      'X-Frame-Options',
      'X-XSS-Protection',
      'Strict-Transport-Security',
      'Content-Security-Policy'
    ]
    
    const missingHeaders = requiredHeaders.filter(header => !headers.has(header))
    
    return {
      valid: missingHeaders.length === 0,
      missingHeaders,
      presentHeaders: requiredHeaders.filter(header => headers.has(header))
    }
  }

  /**
   * Clean up expired tokens and rate limits
   */
  cleanup() {
    const now = Date.now()
    
    // Clean up expired CSRF tokens
    for (const [token, info] of this.csrfTokens.entries()) {
      if (now > info.expiresAt) {
        this.csrfTokens.delete(token)
      }
    }
    
    // Clean up expired account locks
    for (const [identifier, lockInfo] of this.lockedAccounts.entries()) {
      if (now > lockInfo.expiresAt) {
        this.lockedAccounts.delete(identifier)
      }
    }
    
    // Clean up old rate limit entries
    for (const [key, requests] of this.rateLimitStore.entries()) {
      if (Array.isArray(requests)) {
        const validRequests = requests.filter(timestamp => now - timestamp < 3600000) // Keep last hour
        if (validRequests.length === 0) {
          this.rateLimitStore.delete(key)
        } else {
          this.rateLimitStore.set(key, validRequests)
        }
      }
    }
  }
}

export const securityService = new SecurityService()

// Clean up expired data every 5 minutes
setInterval(() => {
  securityService.cleanup()
}, 300000)
