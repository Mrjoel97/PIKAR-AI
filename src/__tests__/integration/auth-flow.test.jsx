/**
 * Authentication Flow Integration Tests
 * End-to-end testing of authentication workflows
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, testDataFactories, mockBase44Client } from '@/test/utils'
import App from '@/App'
import { authService } from '@/services/authService'
import { auditService } from '@/services/auditService'

// Mock dependencies
vi.mock('@/services/authService')
vi.mock('@/services/auditService')
vi.mock('@/api/base44Client', () => ({
  base44: mockBase44Client,
  validatedBase44: mockBase44Client
}))

describe('Authentication Flow Integration', () => {
  const mockUser = testDataFactories.user()
  const mockTokens = {
    accessToken: 'mock-access-token',
    refreshToken: 'mock-refresh-token',
    expiresIn: 3600
  }

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    
    // Mock audit service
    auditService.logAuth = {
      loginAttempt: vi.fn(),
      loginSuccess: vi.fn(),
      loginFailure: vi.fn(),
      logout: vi.fn()
    }
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Login Flow', () => {
    it('completes full login workflow from landing to dashboard', async () => {
      const user = userEvent.setup()

      // Mock successful login
      authService.login.mockResolvedValueOnce({
        success: true,
        user: mockUser,
        tokens: mockTokens
      })

      authService.getCurrentUser.mockReturnValue(null)
      authService.isAuthenticated = false

      renderWithProviders(<App />)

      // Should show login form initially
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
      })

      // Fill in login form
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const loginButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, mockUser.email)
      await user.type(passwordInput, 'password123')
      await user.click(loginButton)

      // Verify login was called with correct credentials
      expect(authService.login).toHaveBeenCalledWith({
        email: mockUser.email,
        password: 'password123'
      })

      // Mock authenticated state after login
      authService.getCurrentUser.mockReturnValue(mockUser)
      authService.isAuthenticated = true

      // Should navigate to dashboard after successful login
      await waitFor(() => {
        expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
      }, { timeout: 5000 })

      // Verify audit logging
      expect(auditService.logAuth.loginSuccess).toHaveBeenCalledWith(
        mockUser.id,
        mockUser.email
      )
    })

    it('handles login failure with proper error display', async () => {
      const user = userEvent.setup()
      const errorMessage = 'Invalid credentials'

      // Mock failed login
      authService.login.mockResolvedValueOnce({
        success: false,
        error: errorMessage
      })

      authService.getCurrentUser.mockReturnValue(null)
      authService.isAuthenticated = false

      renderWithProviders(<App />)

      // Fill in login form with invalid credentials
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const loginButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'invalid@example.com')
      await user.type(passwordInput, 'wrongpassword')
      await user.click(loginButton)

      // Should display error message
      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument()
      })

      // Should remain on login page
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()

      // Verify audit logging
      expect(auditService.logAuth.loginFailure).toHaveBeenCalledWith(
        'invalid@example.com',
        errorMessage
      )
    })

    it('handles network errors gracefully', async () => {
      const user = userEvent.setup()

      // Mock network error
      authService.login.mockRejectedValueOnce(new Error('Network error'))

      authService.getCurrentUser.mockReturnValue(null)
      authService.isAuthenticated = false

      renderWithProviders(<App />)

      // Attempt login
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const loginButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, mockUser.email)
      await user.type(passwordInput, 'password123')
      await user.click(loginButton)

      // Should display network error message
      await waitFor(() => {
        expect(screen.getByText(/network error/i)).toBeInTheDocument()
      })
    })
  })

  describe('Registration Flow', () => {
    it('completes full registration workflow', async () => {
      const user = userEvent.setup()
      const registrationData = {
        email: 'newuser@example.com',
        password: 'password123',
        name: 'New User',
        company: 'Test Company'
      }

      // Mock successful registration
      authService.register.mockResolvedValueOnce({
        success: true,
        user: { ...mockUser, ...registrationData },
        tokens: mockTokens
      })

      authService.getCurrentUser.mockReturnValue(null)
      authService.isAuthenticated = false

      renderWithProviders(<App />)

      // Navigate to registration
      const registerLink = screen.getByText(/sign up/i)
      await user.click(registerLink)

      // Fill in registration form
      await user.type(screen.getByLabelText(/email/i), registrationData.email)
      await user.type(screen.getByLabelText(/password/i), registrationData.password)
      await user.type(screen.getByLabelText(/name/i), registrationData.name)
      await user.type(screen.getByLabelText(/company/i), registrationData.company)

      const registerButton = screen.getByRole('button', { name: /create account/i })
      await user.click(registerButton)

      // Verify registration was called
      expect(authService.register).toHaveBeenCalledWith(registrationData)

      // Mock authenticated state after registration
      authService.getCurrentUser.mockReturnValue({ ...mockUser, ...registrationData })
      authService.isAuthenticated = true

      // Should navigate to dashboard
      await waitFor(() => {
        expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
      })
    })

    it('validates registration form fields', async () => {
      const user = userEvent.setup()

      authService.getCurrentUser.mockReturnValue(null)
      authService.isAuthenticated = false

      renderWithProviders(<App />)

      // Navigate to registration
      const registerLink = screen.getByText(/sign up/i)
      await user.click(registerLink)

      // Try to submit empty form
      const registerButton = screen.getByRole('button', { name: /create account/i })
      await user.click(registerButton)

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument()
        expect(screen.getByText(/password is required/i)).toBeInTheDocument()
        expect(screen.getByText(/name is required/i)).toBeInTheDocument()
      })

      // Should not call register service
      expect(authService.register).not.toHaveBeenCalled()
    })
  })

  describe('Logout Flow', () => {
    beforeEach(() => {
      // Set up authenticated state
      authService.getCurrentUser.mockReturnValue(mockUser)
      authService.isAuthenticated = true
      localStorage.setItem('accessToken', mockTokens.accessToken)
    })

    it('completes full logout workflow', async () => {
      const user = userEvent.setup()

      // Mock successful logout
      authService.logout.mockResolvedValueOnce({
        success: true
      })

      renderWithProviders(<App />)

      // Should show dashboard initially
      await waitFor(() => {
        expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
      })

      // Find and click logout button
      const logoutButton = screen.getByRole('button', { name: /logout/i })
      await user.click(logoutButton)

      // Verify logout was called
      expect(authService.logout).toHaveBeenCalledTimes(1)

      // Mock unauthenticated state after logout
      authService.getCurrentUser.mockReturnValue(null)
      authService.isAuthenticated = false

      // Should navigate back to login
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
      })

      // Verify audit logging
      expect(auditService.logAuth.logout).toHaveBeenCalledWith(mockUser.id)
    })
  })

  describe('Token Refresh Flow', () => {
    it('automatically refreshes expired tokens', async () => {
      vi.useFakeTimers()

      // Mock token refresh
      authService.refreshToken.mockResolvedValueOnce({
        success: true,
        tokens: {
          accessToken: 'new-access-token',
          refreshToken: 'new-refresh-token',
          expiresIn: 3600
        }
      })

      // Set up authenticated state with expiring token
      authService.getCurrentUser.mockReturnValue(mockUser)
      authService.isAuthenticated = true
      localStorage.setItem('accessToken', mockTokens.accessToken)
      localStorage.setItem('tokenExpiration', (Date.now() + 300000).toString()) // 5 minutes

      renderWithProviders(<App />)

      // Fast-forward to near token expiration
      vi.advanceTimersByTime(240000) // 4 minutes

      // Should trigger token refresh
      await waitFor(() => {
        expect(authService.refreshToken).toHaveBeenCalled()
      })

      vi.useRealTimers()
    })

    it('logs out when token refresh fails', async () => {
      // Mock failed token refresh
      authService.refreshToken.mockResolvedValueOnce({
        success: false,
        error: 'Invalid refresh token'
      })

      authService.logout.mockResolvedValueOnce({
        success: true
      })

      // Set up authenticated state
      authService.getCurrentUser.mockReturnValue(mockUser)
      authService.isAuthenticated = true

      renderWithProviders(<App />)

      // Trigger token refresh failure
      await authService.refreshToken()

      // Should automatically log out
      expect(authService.logout).toHaveBeenCalled()
    })
  })

  describe('Protected Route Access', () => {
    it('redirects unauthenticated users to login', async () => {
      authService.getCurrentUser.mockReturnValue(null)
      authService.isAuthenticated = false

      renderWithProviders(<App />)

      // Try to navigate to protected route
      window.history.pushState({}, '', '/dashboard')

      // Should redirect to login
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
      })
    })

    it('allows authenticated users to access protected routes', async () => {
      authService.getCurrentUser.mockReturnValue(mockUser)
      authService.isAuthenticated = true

      renderWithProviders(<App />)

      // Navigate to protected route
      window.history.pushState({}, '', '/dashboard')

      // Should show dashboard
      await waitFor(() => {
        expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
      })
    })
  })

  describe('Session Persistence', () => {
    it('restores session from localStorage on app load', async () => {
      // Set up stored session
      localStorage.setItem('accessToken', mockTokens.accessToken)
      localStorage.setItem('user', JSON.stringify(mockUser))

      // Mock session validation
      authService.initializeAuth.mockResolvedValueOnce({
        success: true,
        user: mockUser
      })

      authService.getCurrentUser.mockReturnValue(mockUser)
      authService.isAuthenticated = true

      renderWithProviders(<App />)

      // Should initialize auth on load
      expect(authService.initializeAuth).toHaveBeenCalled()

      // Should show dashboard without login
      await waitFor(() => {
        expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
      })
    })

    it('clears invalid session data', async () => {
      // Set up invalid stored session
      localStorage.setItem('accessToken', 'invalid-token')
      localStorage.setItem('user', JSON.stringify(mockUser))

      // Mock session validation failure
      authService.initializeAuth.mockResolvedValueOnce({
        success: false,
        error: 'Invalid token'
      })

      authService.getCurrentUser.mockReturnValue(null)
      authService.isAuthenticated = false

      renderWithProviders(<App />)

      // Should clear invalid session and show login
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
      })

      // Should clear localStorage
      expect(localStorage.getItem('accessToken')).toBeNull()
      expect(localStorage.getItem('user')).toBeNull()
    })
  })
})
