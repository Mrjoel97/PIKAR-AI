/**
 * Authentication Security Tests
 * Comprehensive security testing for authentication and authorization
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, testDataFactories } from '@/test/utils'
import { authService } from '@/services/authService'
import { securityService } from '@/services/securityService'
import { auditService } from '@/services/auditService'
import LoginForm from '@/components/auth/LoginForm'
import RegistrationForm from '@/components/auth/RegistrationForm'

// Mock dependencies
vi.mock('@/services/authService')
vi.mock('@/services/securityService')
vi.mock('@/services/auditService')

describe('Authentication Security Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock security service
    securityService.validateInput = vi.fn().mockReturnValue({ isValid: true, errors: [] })
    securityService.detectSQLInjection = vi.fn().mockReturnValue(false)
    securityService.detectXSS = vi.fn().mockReturnValue(false)
    securityService.checkPasswordStrength = vi.fn().mockReturnValue({ score: 4, feedback: [] })
    securityService.rateLimitCheck = vi.fn().mockReturnValue({ allowed: true, remaining: 10 })
    
    // Mock audit service
    auditService.logSecurity = vi.fn()
    auditService.logAccess = vi.fn()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Input Validation Security', () => {
    it('should prevent SQL injection in login form', async () => {
      const user = userEvent.setup()
      
      renderWithProviders(<LoginForm />)
      
      const maliciousInput = "admin'; DROP TABLE users; --"
      
      const emailInput = screen.getByLabelText(/email/i)
      await user.type(emailInput, maliciousInput)
      
      const passwordInput = screen.getByLabelText(/password/i)
      await user.type(passwordInput, 'password123')
      
      await user.click(screen.getByRole('button', { name: /sign in/i }))
      
      // Should detect and prevent SQL injection
      expect(securityService.detectSQLInjection).toHaveBeenCalledWith(maliciousInput)
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'sql_injection_attempt',
        expect.objectContaining({
          input: maliciousInput,
          blocked: true
        })
      )
    })

    it('should prevent XSS attacks in registration form', async () => {
      const user = userEvent.setup()
      
      renderWithProviders(<RegistrationForm />)
      
      const xssPayload = '<script>alert("XSS")</script>'
      
      const nameInput = screen.getByLabelText(/full name/i)
      await user.type(nameInput, xssPayload)
      
      const emailInput = screen.getByLabelText(/email/i)
      await user.type(emailInput, 'test@example.com')
      
      const passwordInput = screen.getByLabelText(/password/i)
      await user.type(passwordInput, 'SecurePass123!')
      
      await user.click(screen.getByRole('button', { name: /create account/i }))
      
      // Should detect and sanitize XSS
      expect(securityService.detectXSS).toHaveBeenCalledWith(xssPayload)
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'xss_attempt',
        expect.objectContaining({
          input: xssPayload,
          sanitized: true
        })
      )
    })

    it('should validate email format strictly', async () => {
      const user = userEvent.setup()
      
      renderWithProviders(<LoginForm />)
      
      const invalidEmails = [
        'invalid-email',
        'test@',
        '@example.com',
        'test..test@example.com',
        'test@example',
        'test@.com'
      ]
      
      const emailInput = screen.getByLabelText(/email/i)
      
      for (const invalidEmail of invalidEmails) {
        await user.clear(emailInput)
        await user.type(emailInput, invalidEmail)
        
        fireEvent.blur(emailInput)
        
        await waitFor(() => {
          expect(screen.getByText(/invalid email format/i)).toBeInTheDocument()
        })
      }
    })

    it('should enforce strong password requirements', async () => {
      const user = userEvent.setup()
      
      renderWithProviders(<RegistrationForm />)
      
      const weakPasswords = [
        'password',
        '123456',
        'qwerty',
        'abc123',
        'Password',
        'password123'
      ]
      
      const passwordInput = screen.getByLabelText(/password/i)
      
      for (const weakPassword of weakPasswords) {
        securityService.checkPasswordStrength.mockReturnValueOnce({
          score: 1,
          feedback: ['Password is too weak']
        })
        
        await user.clear(passwordInput)
        await user.type(passwordInput, weakPassword)
        
        fireEvent.blur(passwordInput)
        
        await waitFor(() => {
          expect(screen.getByText(/password is too weak/i)).toBeInTheDocument()
        })
      }
    })
  })

  describe('Rate Limiting Security', () => {
    it('should implement rate limiting for login attempts', async () => {
      const user = userEvent.setup()
      
      // Mock rate limit exceeded
      securityService.rateLimitCheck.mockReturnValue({
        allowed: false,
        remaining: 0,
        resetTime: Date.now() + 300000 // 5 minutes
      })
      
      renderWithProviders(<LoginForm />)
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const loginButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(loginButton)
      
      // Should show rate limit error
      await waitFor(() => {
        expect(screen.getByText(/too many login attempts/i)).toBeInTheDocument()
      })
      
      // Should log security event
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'rate_limit_exceeded',
        expect.objectContaining({
          action: 'login',
          ip: expect.any(String)
        })
      )
    })

    it('should implement progressive delays for failed attempts', async () => {
      const user = userEvent.setup()
      
      authService.login = vi.fn().mockRejectedValue(new Error('Invalid credentials'))
      
      renderWithProviders(<LoginForm />)
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const loginButton = screen.getByRole('button', { name: /sign in/i })
      
      // Simulate multiple failed attempts
      for (let attempt = 1; attempt <= 3; attempt++) {
        await user.clear(emailInput)
        await user.clear(passwordInput)
        await user.type(emailInput, 'test@example.com')
        await user.type(passwordInput, 'wrongpassword')
        
        const startTime = Date.now()
        await user.click(loginButton)
        
        await waitFor(() => {
          expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
        })
        
        // Should implement progressive delay
        const delay = Date.now() - startTime
        const expectedMinDelay = attempt * 1000 // 1s, 2s, 3s
        expect(delay).toBeGreaterThanOrEqual(expectedMinDelay - 100) // Allow 100ms tolerance
      }
    })
  })

  describe('Session Security', () => {
    it('should implement secure session management', async () => {
      const mockToken = 'secure.jwt.token'
      const mockUser = testDataFactories.user()
      
      authService.login = vi.fn().mockResolvedValue({
        success: true,
        data: {
          token: mockToken,
          user: mockUser,
          expiresAt: Date.now() + 3600000 // 1 hour
        }
      })
      
      const user = userEvent.setup()
      
      renderWithProviders(<LoginForm />)
      
      await user.type(screen.getByLabelText(/email/i), mockUser.email)
      await user.type(screen.getByLabelText(/password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))
      
      await waitFor(() => {
        expect(authService.login).toHaveBeenCalled()
      })
      
      // Should store token securely
      expect(localStorage.getItem('accessToken')).toBe(mockToken)
      
      // Should set secure headers
      expect(auditService.logAccess).toHaveBeenCalledWith(
        'login_success',
        expect.objectContaining({
          userId: mockUser.id,
          sessionId: expect.any(String)
        })
      )
    })

    it('should handle session expiration securely', async () => {
      const expiredToken = 'expired.jwt.token'
      
      // Mock expired token
      authService.validateToken = vi.fn().mockResolvedValue({
        valid: false,
        expired: true
      })
      
      // Set expired token in storage
      localStorage.setItem('accessToken', expiredToken)
      
      renderWithProviders(<div data-testid="protected-content">Protected Content</div>)
      
      // Should redirect to login
      await waitFor(() => {
        expect(authService.validateToken).toHaveBeenCalledWith(expiredToken)
      })
      
      // Should clear expired token
      expect(localStorage.getItem('accessToken')).toBeNull()
      
      // Should log security event
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'session_expired',
        expect.objectContaining({
          token: expiredToken
        })
      )
    })

    it('should implement secure logout', async () => {
      const mockToken = 'valid.jwt.token'
      localStorage.setItem('accessToken', mockToken)
      
      authService.logout = vi.fn().mockResolvedValue({ success: true })
      
      const user = userEvent.setup()
      
      renderWithProviders(
        <button onClick={() => authService.logout()} data-testid="logout-button">
          Logout
        </button>
      )
      
      await user.click(screen.getByTestId('logout-button'))
      
      await waitFor(() => {
        expect(authService.logout).toHaveBeenCalled()
      })
      
      // Should clear all tokens
      expect(localStorage.getItem('accessToken')).toBeNull()
      expect(localStorage.getItem('refreshToken')).toBeNull()
      
      // Should log security event
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'logout_success',
        expect.objectContaining({
          token: mockToken
        })
      )
    })
  })

  describe('Authorization Security', () => {
    it('should enforce role-based access control', async () => {
      const regularUser = testDataFactories.user({ role: 'user' })
      const adminUser = testDataFactories.user({ role: 'admin' })
      
      // Test regular user access to admin route
      authService.getCurrentUser = vi.fn().mockResolvedValue(regularUser)
      
      renderWithProviders(
        <div data-testid="admin-panel">Admin Panel</div>,
        {
          initialState: {
            auth: { user: regularUser, isAuthenticated: true }
          }
        }
      )
      
      // Should not show admin content
      expect(screen.queryByTestId('admin-panel')).not.toBeInTheDocument()
      
      // Should log unauthorized access attempt
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'unauthorized_access_attempt',
        expect.objectContaining({
          userId: regularUser.id,
          requiredRole: 'admin',
          userRole: 'user'
        })
      )
    })

    it('should validate JWT token integrity', async () => {
      const tamperedToken = 'tampered.jwt.token'
      
      authService.validateToken = vi.fn().mockResolvedValue({
        valid: false,
        reason: 'invalid_signature'
      })
      
      localStorage.setItem('accessToken', tamperedToken)
      
      renderWithProviders(<div data-testid="protected-content">Protected</div>)
      
      await waitFor(() => {
        expect(authService.validateToken).toHaveBeenCalledWith(tamperedToken)
      })
      
      // Should reject tampered token
      expect(localStorage.getItem('accessToken')).toBeNull()
      
      // Should log security incident
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'token_tampering_detected',
        expect.objectContaining({
          token: tamperedToken,
          reason: 'invalid_signature'
        })
      )
    })
  })

  describe('CSRF Protection', () => {
    it('should implement CSRF token validation', async () => {
      const csrfToken = 'csrf-token-123'
      
      // Mock CSRF token generation
      securityService.generateCSRFToken = vi.fn().mockReturnValue(csrfToken)
      securityService.validateCSRFToken = vi.fn().mockReturnValue(true)
      
      const user = userEvent.setup()
      
      renderWithProviders(<LoginForm />)
      
      // Should include CSRF token in form
      expect(securityService.generateCSRFToken).toHaveBeenCalled()
      
      await user.type(screen.getByLabelText(/email/i), 'test@example.com')
      await user.type(screen.getByLabelText(/password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))
      
      // Should validate CSRF token on submission
      expect(securityService.validateCSRFToken).toHaveBeenCalledWith(csrfToken)
    })

    it('should reject requests with invalid CSRF tokens', async () => {
      const invalidCSRFToken = 'invalid-csrf-token'
      
      securityService.validateCSRFToken = vi.fn().mockReturnValue(false)
      
      const user = userEvent.setup()
      
      renderWithProviders(<LoginForm />)
      
      await user.type(screen.getByLabelText(/email/i), 'test@example.com')
      await user.type(screen.getByLabelText(/password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))
      
      // Should show CSRF error
      await waitFor(() => {
        expect(screen.getByText(/security token invalid/i)).toBeInTheDocument()
      })
      
      // Should log security incident
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'csrf_token_invalid',
        expect.objectContaining({
          token: invalidCSRFToken
        })
      )
    })
  })

  describe('Brute Force Protection', () => {
    it('should implement account lockout after failed attempts', async () => {
      const user = userEvent.setup()
      const testEmail = 'test@example.com'
      
      // Mock failed login attempts
      authService.login = vi.fn().mockRejectedValue(new Error('Invalid credentials'))
      
      renderWithProviders(<LoginForm />)
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const loginButton = screen.getByRole('button', { name: /sign in/i })
      
      // Simulate 5 failed attempts
      for (let i = 0; i < 5; i++) {
        await user.clear(emailInput)
        await user.clear(passwordInput)
        await user.type(emailInput, testEmail)
        await user.type(passwordInput, 'wrongpassword')
        await user.click(loginButton)
        
        await waitFor(() => {
          expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
        })
      }
      
      // 6th attempt should show account locked
      securityService.isAccountLocked = vi.fn().mockReturnValue(true)
      
      await user.clear(emailInput)
      await user.clear(passwordInput)
      await user.type(emailInput, testEmail)
      await user.type(passwordInput, 'wrongpassword')
      await user.click(loginButton)
      
      await waitFor(() => {
        expect(screen.getByText(/account temporarily locked/i)).toBeInTheDocument()
      })
      
      // Should log security event
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'account_locked',
        expect.objectContaining({
          email: testEmail,
          failedAttempts: 5
        })
      )
    })

    it('should implement IP-based blocking', async () => {
      const suspiciousIP = '192.168.1.100'
      
      securityService.isIPBlocked = vi.fn().mockReturnValue(true)
      
      const user = userEvent.setup()
      
      renderWithProviders(<LoginForm />)
      
      await user.type(screen.getByLabelText(/email/i), 'test@example.com')
      await user.type(screen.getByLabelText(/password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))
      
      // Should show IP blocked message
      await waitFor(() => {
        expect(screen.getByText(/access denied/i)).toBeInTheDocument()
      })
      
      // Should log security event
      expect(auditService.logSecurity).toHaveBeenCalledWith(
        'ip_blocked',
        expect.objectContaining({
          ip: suspiciousIP,
          reason: 'suspicious_activity'
        })
      )
    })
  })

  describe('Security Headers', () => {
    it('should validate Content Security Policy', () => {
      // Mock CSP validation
      securityService.validateCSP = vi.fn().mockReturnValue({
        valid: true,
        violations: []
      })
      
      renderWithProviders(<LoginForm />)
      
      // Should validate CSP
      expect(securityService.validateCSP).toHaveBeenCalled()
    })

    it('should enforce HTTPS in production', () => {
      const originalEnv = process.env.NODE_ENV
      process.env.NODE_ENV = 'production'
      
      securityService.enforceHTTPS = vi.fn().mockReturnValue(true)
      
      renderWithProviders(<LoginForm />)
      
      // Should enforce HTTPS
      expect(securityService.enforceHTTPS).toHaveBeenCalled()
      
      process.env.NODE_ENV = originalEnv
    })
  })
})
