/**
 * useAuth Hook Tests
 * Comprehensive unit tests for the useAuth hook
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useAuth } from '../useAuth'
import { testDataFactories, mockApiClient } from '@/test/utils'

// Mock dependencies
vi.mock('@/services/authService', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    updateProfile: vi.fn(),
    isAuthenticated: false,
    currentUser: null,
    initializeAuth: vi.fn(),
    refreshToken: vi.fn(),
  }
}))

vi.mock('@/services/auditService', () => ({
  auditService: {
    logAuth: {
      loginAttempt: vi.fn(),
      loginSuccess: vi.fn(),
      loginFailure: vi.fn(),
      logout: vi.fn(),
    }
  }
}))

import { authService } from '@/services/authService'

describe('useAuth Hook', () => {
  const mockUser = testDataFactories.user()

  beforeEach(() => {
    vi.clearAllMocks()
    authService.isAuthenticated = false
    authService.currentUser = null
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Initial State', () => {
    it('returns initial unauthenticated state', () => {
      const { result } = renderHook(() => useAuth())

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.isLoading).toBe(true) // Initially loading
      expect(result.current.error).toBeNull()
    })

    it('initializes authentication on mount', async () => {
      authService.initializeAuth.mockResolvedValueOnce({
        success: true,
        user: mockUser
      })

      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(authService.initializeAuth).toHaveBeenCalledTimes(1)
    })
  })

  describe('Login', () => {
    it('successfully logs in user', async () => {
      authService.login.mockResolvedValueOnce({
        success: true,
        user: mockUser
      })

      const { result } = renderHook(() => useAuth())

      const credentials = {
        email: 'test@example.com',
        password: 'password123'
      }

      await act(async () => {
        await result.current.login(credentials)
      })

      expect(authService.login).toHaveBeenCalledWith(credentials)
      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.error).toBeNull()
    })

    it('handles login failure', async () => {
      const errorMessage = 'Invalid credentials'
      authService.login.mockResolvedValueOnce({
        success: false,
        error: errorMessage
      })

      const { result } = renderHook(() => useAuth())

      const credentials = {
        email: 'test@example.com',
        password: 'wrongpassword'
      }

      await act(async () => {
        await result.current.login(credentials)
      })

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.error).toBe(errorMessage)
    })

    it('sets loading state during login', async () => {
      let resolveLogin
      const loginPromise = new Promise(resolve => {
        resolveLogin = resolve
      })

      authService.login.mockReturnValueOnce(loginPromise)

      const { result } = renderHook(() => useAuth())

      act(() => {
        result.current.login({
          email: 'test@example.com',
          password: 'password123'
        })
      })

      expect(result.current.isLoading).toBe(true)

      await act(async () => {
        resolveLogin({ success: true, user: mockUser })
        await loginPromise
      })

      expect(result.current.isLoading).toBe(false)
    })

    it('validates credentials before login', async () => {
      const { result } = renderHook(() => useAuth())

      const invalidCredentials = {
        email: 'invalid-email',
        password: '123'
      }

      await act(async () => {
        await result.current.login(invalidCredentials)
      })

      expect(authService.login).not.toHaveBeenCalled()
      expect(result.current.error).toContain('Invalid')
    })
  })

  describe('Registration', () => {
    it('successfully registers new user', async () => {
      authService.register.mockResolvedValueOnce({
        success: true,
        user: mockUser
      })

      const { result } = renderHook(() => useAuth())

      const userData = {
        email: 'newuser@example.com',
        password: 'password123',
        name: 'New User',
        company: 'Test Company'
      }

      await act(async () => {
        await result.current.register(userData)
      })

      expect(authService.register).toHaveBeenCalledWith(userData)
      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
    })

    it('handles registration failure', async () => {
      const errorMessage = 'Email already exists'
      authService.register.mockResolvedValueOnce({
        success: false,
        error: errorMessage
      })

      const { result } = renderHook(() => useAuth())

      const userData = {
        email: 'existing@example.com',
        password: 'password123',
        name: 'Test User'
      }

      await act(async () => {
        await result.current.register(userData)
      })

      expect(result.current.error).toBe(errorMessage)
      expect(result.current.isAuthenticated).toBe(false)
    })

    it('validates registration data', async () => {
      const { result } = renderHook(() => useAuth())

      const invalidData = {
        email: 'invalid-email',
        password: '123', // Too short
        name: '' // Empty name
      }

      await act(async () => {
        await result.current.register(invalidData)
      })

      expect(authService.register).not.toHaveBeenCalled()
      expect(result.current.error).toContain('Invalid')
    })
  })

  describe('Logout', () => {
    beforeEach(() => {
      authService.isAuthenticated = true
      authService.currentUser = mockUser
    })

    it('successfully logs out user', async () => {
      authService.logout.mockResolvedValueOnce({
        success: true
      })

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        await result.current.logout()
      })

      expect(authService.logout).toHaveBeenCalledTimes(1)
      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })

    it('handles logout errors gracefully', async () => {
      authService.logout.mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        await result.current.logout()
      })

      // Should still log out locally even if API call fails
      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })
  })

  describe('Profile Updates', () => {
    beforeEach(() => {
      authService.isAuthenticated = true
      authService.currentUser = mockUser
    })

    it('successfully updates user profile', async () => {
      const updates = {
        name: 'Updated Name',
        company: 'Updated Company'
      }

      const updatedUser = { ...mockUser, ...updates }

      authService.updateProfile.mockResolvedValueOnce({
        success: true,
        user: updatedUser
      })

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        await result.current.updateProfile(updates)
      })

      expect(authService.updateProfile).toHaveBeenCalledWith(updates)
      expect(result.current.user).toEqual(updatedUser)
    })

    it('handles profile update failure', async () => {
      const errorMessage = 'Validation failed'
      authService.updateProfile.mockResolvedValueOnce({
        success: false,
        error: errorMessage
      })

      const { result } = renderHook(() => useAuth())

      const updates = {
        email: 'invalid-email'
      }

      await act(async () => {
        await result.current.updateProfile(updates)
      })

      expect(result.current.error).toBe(errorMessage)
      expect(result.current.user).toEqual(mockUser) // Should remain unchanged
    })
  })

  describe('Error Handling', () => {
    it('clears errors when new operations start', async () => {
      // Set initial error
      authService.login.mockResolvedValueOnce({
        success: false,
        error: 'Initial error'
      })

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        await result.current.login({
          email: 'test@example.com',
          password: 'wrong'
        })
      })

      expect(result.current.error).toBe('Initial error')

      // Start new operation
      authService.login.mockResolvedValueOnce({
        success: true,
        user: mockUser
      })

      await act(async () => {
        await result.current.login({
          email: 'test@example.com',
          password: 'correct'
        })
      })

      expect(result.current.error).toBeNull()
    })

    it('handles network errors', async () => {
      authService.login.mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        await result.current.login({
          email: 'test@example.com',
          password: 'password123'
        })
      })

      expect(result.current.error).toContain('Network error')
      expect(result.current.isAuthenticated).toBe(false)
    })
  })

  describe('Token Refresh', () => {
    it('automatically refreshes expired tokens', async () => {
      vi.useFakeTimers()

      authService.refreshToken.mockResolvedValue({
        success: true
      })

      const { result } = renderHook(() => useAuth())

      // Simulate token expiration
      act(() => {
        vi.advanceTimersByTime(3600000) // 1 hour
      })

      await waitFor(() => {
        expect(authService.refreshToken).toHaveBeenCalled()
      })

      vi.useRealTimers()
    })

    it('logs out when token refresh fails', async () => {
      authService.refreshToken.mockResolvedValueOnce({
        success: false,
        error: 'Invalid refresh token'
      })

      authService.logout.mockResolvedValueOnce({
        success: true
      })

      const { result } = renderHook(() => useAuth())

      // Trigger token refresh failure
      await act(async () => {
        await result.current.refreshToken()
      })

      expect(authService.logout).toHaveBeenCalled()
      expect(result.current.isAuthenticated).toBe(false)
    })
  })

  describe('Concurrent Operations', () => {
    it('handles concurrent login attempts', async () => {
      authService.login.mockResolvedValue({
        success: true,
        user: mockUser
      })

      const { result } = renderHook(() => useAuth())

      const credentials = {
        email: 'test@example.com',
        password: 'password123'
      }

      // Start multiple login attempts simultaneously
      const promises = [
        result.current.login(credentials),
        result.current.login(credentials),
        result.current.login(credentials)
      ]

      await act(async () => {
        await Promise.all(promises)
      })

      // Should only call login once due to deduplication
      expect(authService.login).toHaveBeenCalledTimes(1)
    })

    it('prevents operations while loading', async () => {
      let resolveLogin
      const loginPromise = new Promise(resolve => {
        resolveLogin = resolve
      })

      authService.login.mockReturnValueOnce(loginPromise)

      const { result } = renderHook(() => useAuth())

      // Start login
      act(() => {
        result.current.login({
          email: 'test@example.com',
          password: 'password123'
        })
      })

      // Try to start another operation while loading
      await act(async () => {
        await result.current.register({
          email: 'test@example.com',
          password: 'password123',
          name: 'Test User'
        })
      })

      // Register should not be called while login is in progress
      expect(authService.register).not.toHaveBeenCalled()

      // Complete login
      await act(async () => {
        resolveLogin({ success: true, user: mockUser })
        await loginPromise
      })
    })
  })
})
