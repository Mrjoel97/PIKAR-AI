/**
 * Authentication Service Tests
 * Comprehensive unit tests for the authentication service
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { authService } from '../authService'
import { testDataFactories, mockApiClient } from '@/test/utils'

// Mock dependencies
vi.mock('../apiClient', () => ({
  apiClient: mockApiClient
}))

vi.mock('../auditService', () => ({
  auditService: {
    logAuth: {
      loginAttempt: vi.fn(),
      loginSuccess: vi.fn(),
      loginFailure: vi.fn(),
      logout: vi.fn(),
      tokenRefresh: vi.fn(),
    }
  }
}))

describe('AuthService', () => {
  const mockUser = testDataFactories.user()
  const mockTokens = {
    accessToken: 'mock-access-token',
    refreshToken: 'mock-refresh-token',
    expiresIn: 3600
  }

  beforeEach(() => {
    // Clear localStorage
    localStorage.clear()
    
    // Reset all mocks
    vi.clearAllMocks()
    
    // Reset auth service state
    authService.currentUser = null
    authService.isAuthenticated = false
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Login', () => {
    it('successfully logs in with valid credentials', async () => {
      const credentials = {
        email: 'test@example.com',
        password: 'password123'
      }

      mockApiClient.post.mockResolvedValueOnce({
        ok: true,
        data: {
          user: mockUser,
          tokens: mockTokens
        }
      })

      const result = await authService.login(credentials)

      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/login', credentials)
      expect(result.success).toBe(true)
      expect(result.user).toEqual(mockUser)
      expect(authService.isAuthenticated).toBe(true)
      expect(authService.currentUser).toEqual(mockUser)
    })

    it('fails login with invalid credentials', async () => {
      const credentials = {
        email: 'test@example.com',
        password: 'wrongpassword'
      }

      mockApiClient.post.mockRejectedValueOnce({
        status: 401,
        message: 'Invalid credentials'
      })

      const result = await authService.login(credentials)

      expect(result.success).toBe(false)
      expect(result.error).toBe('Invalid credentials')
      expect(authService.isAuthenticated).toBe(false)
      expect(authService.currentUser).toBeNull()
    })

    it('stores tokens in localStorage on successful login', async () => {
      const credentials = {
        email: 'test@example.com',
        password: 'password123'
      }

      mockApiClient.post.mockResolvedValueOnce({
        ok: true,
        data: {
          user: mockUser,
          tokens: mockTokens
        }
      })

      await authService.login(credentials)

      expect(localStorage.getItem('accessToken')).toBe(mockTokens.accessToken)
      expect(localStorage.getItem('refreshToken')).toBe(mockTokens.refreshToken)
    })

    it('validates email format', async () => {
      const credentials = {
        email: 'invalid-email',
        password: 'password123'
      }

      const result = await authService.login(credentials)

      expect(result.success).toBe(false)
      expect(result.error).toContain('Invalid email format')
      expect(mockApiClient.post).not.toHaveBeenCalled()
    })

    it('validates password requirements', async () => {
      const credentials = {
        email: 'test@example.com',
        password: '123' // Too short
      }

      const result = await authService.login(credentials)

      expect(result.success).toBe(false)
      expect(result.error).toContain('Password must be at least')
      expect(mockApiClient.post).not.toHaveBeenCalled()
    })

    it('handles network errors gracefully', async () => {
      const credentials = {
        email: 'test@example.com',
        password: 'password123'
      }

      mockApiClient.post.mockRejectedValueOnce(new Error('Network error'))

      const result = await authService.login(credentials)

      expect(result.success).toBe(false)
      expect(result.error).toContain('Network error')
    })
  })

  describe('Registration', () => {
    it('successfully registers new user', async () => {
      const userData = {
        email: 'newuser@example.com',
        password: 'password123',
        name: 'New User',
        company: 'Test Company'
      }

      mockApiClient.post.mockResolvedValueOnce({
        ok: true,
        data: {
          user: { ...mockUser, ...userData },
          tokens: mockTokens
        }
      })

      const result = await authService.register(userData)

      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/register', userData)
      expect(result.success).toBe(true)
      expect(result.user.email).toBe(userData.email)
    })

    it('fails registration with existing email', async () => {
      const userData = {
        email: 'existing@example.com',
        password: 'password123',
        name: 'Test User'
      }

      mockApiClient.post.mockRejectedValueOnce({
        status: 409,
        message: 'Email already exists'
      })

      const result = await authService.register(userData)

      expect(result.success).toBe(false)
      expect(result.error).toBe('Email already exists')
    })

    it('validates required fields', async () => {
      const incompleteData = {
        email: 'test@example.com'
        // Missing password and name
      }

      const result = await authService.register(incompleteData)

      expect(result.success).toBe(false)
      expect(result.error).toContain('required')
      expect(mockApiClient.post).not.toHaveBeenCalled()
    })
  })

  describe('Logout', () => {
    beforeEach(async () => {
      // Set up authenticated state
      authService.currentUser = mockUser
      authService.isAuthenticated = true
      localStorage.setItem('accessToken', mockTokens.accessToken)
      localStorage.setItem('refreshToken', mockTokens.refreshToken)
    })

    it('successfully logs out user', async () => {
      mockApiClient.post.mockResolvedValueOnce({ ok: true })

      const result = await authService.logout()

      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/logout')
      expect(result.success).toBe(true)
      expect(authService.isAuthenticated).toBe(false)
      expect(authService.currentUser).toBeNull()
    })

    it('clears tokens from localStorage', async () => {
      mockApiClient.post.mockResolvedValueOnce({ ok: true })

      await authService.logout()

      expect(localStorage.getItem('accessToken')).toBeNull()
      expect(localStorage.getItem('refreshToken')).toBeNull()
    })

    it('logs out even if API call fails', async () => {
      mockApiClient.post.mockRejectedValueOnce(new Error('Network error'))

      const result = await authService.logout()

      expect(result.success).toBe(true) // Should still succeed locally
      expect(authService.isAuthenticated).toBe(false)
      expect(localStorage.getItem('accessToken')).toBeNull()
    })
  })

  describe('Token Management', () => {
    it('refreshes token when expired', async () => {
      localStorage.setItem('refreshToken', mockTokens.refreshToken)

      const newTokens = {
        accessToken: 'new-access-token',
        refreshToken: 'new-refresh-token',
        expiresIn: 3600
      }

      mockApiClient.post.mockResolvedValueOnce({
        ok: true,
        data: { tokens: newTokens }
      })

      const result = await authService.refreshToken()

      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/refresh', {
        refreshToken: mockTokens.refreshToken
      })
      expect(result.success).toBe(true)
      expect(localStorage.getItem('accessToken')).toBe(newTokens.accessToken)
    })

    it('logs out when refresh token is invalid', async () => {
      localStorage.setItem('refreshToken', 'invalid-token')

      mockApiClient.post.mockRejectedValueOnce({
        status: 401,
        message: 'Invalid refresh token'
      })

      const result = await authService.refreshToken()

      expect(result.success).toBe(false)
      expect(authService.isAuthenticated).toBe(false)
      expect(localStorage.getItem('accessToken')).toBeNull()
    })

    it('automatically refreshes token before expiration', async () => {
      vi.useFakeTimers()

      // Set up token that expires in 1 hour
      const expirationTime = Date.now() + 3600000
      localStorage.setItem('accessToken', mockTokens.accessToken)
      localStorage.setItem('tokenExpiration', expirationTime.toString())

      const newTokens = {
        accessToken: 'refreshed-token',
        refreshToken: 'refreshed-refresh-token',
        expiresIn: 3600
      }

      mockApiClient.post.mockResolvedValueOnce({
        ok: true,
        data: { tokens: newTokens }
      })

      // Start auto-refresh
      authService.startTokenRefreshTimer()

      // Fast-forward to 5 minutes before expiration
      vi.advanceTimersByTime(3300000) // 55 minutes

      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/refresh', expect.any(Object))

      vi.useRealTimers()
    })
  })

  describe('User Profile', () => {
    beforeEach(() => {
      authService.currentUser = mockUser
      authService.isAuthenticated = true
    })

    it('gets current user profile', () => {
      const user = authService.getCurrentUser()
      expect(user).toEqual(mockUser)
    })

    it('updates user profile', async () => {
      const updates = {
        name: 'Updated Name',
        company: 'Updated Company'
      }

      const updatedUser = { ...mockUser, ...updates }

      mockApiClient.put.mockResolvedValueOnce({
        ok: true,
        data: { user: updatedUser }
      })

      const result = await authService.updateProfile(updates)

      expect(mockApiClient.put).toHaveBeenCalledWith('/auth/profile', updates)
      expect(result.success).toBe(true)
      expect(authService.currentUser).toEqual(updatedUser)
    })

    it('validates profile update data', async () => {
      const invalidUpdates = {
        email: 'invalid-email-format'
      }

      const result = await authService.updateProfile(invalidUpdates)

      expect(result.success).toBe(false)
      expect(result.error).toContain('Invalid email format')
      expect(mockApiClient.put).not.toHaveBeenCalled()
    })
  })

  describe('Authentication State', () => {
    it('checks if user is authenticated', () => {
      expect(authService.isAuthenticated).toBe(false)

      authService.currentUser = mockUser
      authService.isAuthenticated = true

      expect(authService.isAuthenticated).toBe(true)
    })

    it('restores authentication state from localStorage', async () => {
      localStorage.setItem('accessToken', mockTokens.accessToken)
      localStorage.setItem('user', JSON.stringify(mockUser))

      mockApiClient.get.mockResolvedValueOnce({
        ok: true,
        data: { user: mockUser }
      })

      await authService.initializeAuth()

      expect(authService.isAuthenticated).toBe(true)
      expect(authService.currentUser).toEqual(mockUser)
    })

    it('clears invalid authentication state', async () => {
      localStorage.setItem('accessToken', 'invalid-token')
      localStorage.setItem('user', JSON.stringify(mockUser))

      mockApiClient.get.mockRejectedValueOnce({
        status: 401,
        message: 'Invalid token'
      })

      await authService.initializeAuth()

      expect(authService.isAuthenticated).toBe(false)
      expect(authService.currentUser).toBeNull()
      expect(localStorage.getItem('accessToken')).toBeNull()
    })
  })

  describe('Security Features', () => {
    it('implements rate limiting for login attempts', async () => {
      const credentials = {
        email: 'test@example.com',
        password: 'wrongpassword'
      }

      // Mock multiple failed attempts
      mockApiClient.post.mockRejectedValue({
        status: 401,
        message: 'Invalid credentials'
      })

      // Attempt login multiple times
      for (let i = 0; i < 5; i++) {
        await authService.login(credentials)
      }

      // 6th attempt should be rate limited
      const result = await authService.login(credentials)

      expect(result.success).toBe(false)
      expect(result.error).toContain('Too many login attempts')
    })

    it('validates token format', () => {
      const validToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
      const invalidToken = 'invalid-token-format'

      expect(authService.isValidTokenFormat(validToken)).toBe(true)
      expect(authService.isValidTokenFormat(invalidToken)).toBe(false)
    })

    it('handles concurrent login attempts', async () => {
      const credentials = {
        email: 'test@example.com',
        password: 'password123'
      }

      mockApiClient.post.mockResolvedValue({
        ok: true,
        data: {
          user: mockUser,
          tokens: mockTokens
        }
      })

      // Simulate concurrent login attempts
      const promises = Array(3).fill().map(() => authService.login(credentials))
      const results = await Promise.all(promises)

      // Only one should succeed, others should be ignored
      const successCount = results.filter(r => r.success).length
      expect(successCount).toBe(1)
    })
  })
})
