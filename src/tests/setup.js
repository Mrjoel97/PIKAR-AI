/**
 * Test Setup Configuration
 * Global test setup for all test suites
 */

import { expect, afterEach, beforeAll, afterAll, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom'

// Extend expect with custom matchers
expect.extend({
  toBeWithinRange(received, floor, ceiling) {
    const pass = received >= floor && received <= ceiling
    if (pass) {
      return {
        message: () => `expected ${received} not to be within range ${floor} - ${ceiling}`,
        pass: true,
      }
    } else {
      return {
        message: () => `expected ${received} to be within range ${floor} - ${ceiling}`,
        pass: false,
      }
    }
  },
})

// Global test setup
beforeAll(() => {
  // Mock console methods to reduce noise in tests
  global.console = {
    ...console,
    log: vi.fn(),
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }

  // Mock window.matchMedia
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(), // deprecated
      removeListener: vi.fn(), // deprecated
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })

  // Mock ResizeObserver
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }))

  // Mock IntersectionObserver
  global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }))

  // Mock fetch
  global.fetch = vi.fn()

  // Mock localStorage
  const localStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  }
  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock
  })

  // Mock sessionStorage
  const sessionStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  }
  Object.defineProperty(window, 'sessionStorage', {
    value: sessionStorageMock
  })

  // Mock window.location
  delete window.location
  window.location = {
    href: 'http://localhost:3000',
    origin: 'http://localhost:3000',
    protocol: 'http:',
    host: 'localhost:3000',
    hostname: 'localhost',
    port: '3000',
    pathname: '/',
    search: '',
    hash: '',
    assign: vi.fn(),
    replace: vi.fn(),
    reload: vi.fn(),
  }

  // Mock window.history
  Object.defineProperty(window, 'history', {
    value: {
      pushState: vi.fn(),
      replaceState: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      go: vi.fn(),
    },
    writable: true,
  })

  // Mock environment variables
  process.env.NODE_ENV = 'test'
  process.env.VITE_API_URL = 'http://localhost:3001'
  process.env.VITE_BASE_URL = 'http://localhost:3000'
})

// Cleanup after each test
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  
  // Clear localStorage and sessionStorage
  window.localStorage.clear()
  window.sessionStorage.clear()
  
  // Reset fetch mock
  global.fetch.mockClear()
})

// Global teardown
afterAll(() => {
  vi.restoreAllMocks()
})

// Mock implementations for common services
vi.mock('@/services/auditService', () => ({
  auditService: {
    logSystem: {
      tier: vi.fn(),
      notification: vi.fn(),
      abTesting: vi.fn(),
      payment: vi.fn(),
      userManagement: vi.fn(),
      error: vi.fn(),
    },
    logAccess: {
      tierChange: vi.fn(),
      tierUpgrade: vi.fn(),
      tierDowngrade: vi.fn(),
      quotaExceeded: vi.fn(),
      usageTracking: vi.fn(),
      abTesting: vi.fn(),
      payment: vi.fn(),
      userManagement: vi.fn(),
      preferences: vi.fn(),
    }
  }
}))

vi.mock('@/services/loggingService', () => ({
  loggingService: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }
}))

// Mock React Router
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useLocation: () => ({
      pathname: '/',
      search: '',
      hash: '',
      state: null,
    }),
    useParams: () => ({}),
  }
})

// Mock Sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  }
}))

// Mock date-fns
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn(() => '2 minutes ago'),
  format: vi.fn(() => '2023-12-01'),
  isAfter: vi.fn(() => false),
  isBefore: vi.fn(() => true),
  addDays: vi.fn(() => new Date()),
  subDays: vi.fn(() => new Date()),
}))

// Test utilities
export const createMockUser = (overrides = {}) => ({
  id: 'test-user-123',
  email: 'test@example.com',
  firstName: 'Test',
  lastName: 'User',
  displayName: 'Test User',
  status: 'active',
  roleId: 'member',
  ...overrides
})

export const createMockTier = (overrides = {}) => ({
  id: 'free',
  name: 'Free',
  price: 0,
  billingPeriod: 'monthly',
  features: {
    maxAgentExecutions: 100,
    maxTeamMembers: 1,
    maxProjects: 3,
    maxStorageGB: 1,
    supportLevel: 'community',
    advancedAnalytics: false,
    customIntegrations: false,
    apiAccess: false,
  },
  limits: {
    monthlyExecutions: 100,
    dailyExecutions: 10,
    concurrentExecutions: 1,
    fileUploadSizeMB: 10,
  },
  ...overrides
})

export const createMockUsage = (overrides = {}) => ({
  monthlyExecutions: 25,
  dailyExecutions: 2,
  fileUploadSizeMB: 5,
  lastUpdated: Date.now(),
  ...overrides
})

export const createMockNotification = (overrides = {}) => ({
  id: 'notif-123',
  type: 'info',
  title: 'Test Notification',
  message: 'This is a test notification',
  timestamp: Date.now(),
  read: false,
  ...overrides
})

export const createMockABTest = (overrides = {}) => ({
  id: 'test-123',
  name: 'Test A/B Test',
  description: 'Testing something',
  status: 'running',
  variants: [
    { id: 'control', name: 'Control', isControl: true },
    { id: 'variant', name: 'Variant', isControl: false }
  ],
  ...overrides
})

// Custom render function for React components
export { render, screen, fireEvent, waitFor } from '@testing-library/react'
export { userEvent } from '@testing-library/user-event'

// Re-export testing utilities
export { vi, expect, describe, test, it, beforeEach, afterEach, beforeAll, afterAll }
