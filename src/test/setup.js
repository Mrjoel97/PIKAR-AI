/**
 * Test Setup Configuration
 * Global test setup for Vitest and React Testing Library
 */

import { expect, afterEach, beforeAll, afterAll, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'
import { testingService } from '@/services/testingService'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Global test setup
beforeAll(async () => {
  // Initialize testing service
  await testingService.initialize()
  
  // Setup global mocks
  setupGlobalMocks()
  
  // Setup test environment
  setupTestEnvironment()
})

// Cleanup after each test
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  vi.clearAllTimers()
})

// Global cleanup
afterAll(() => {
  vi.restoreAllMocks()
})

/**
 * Setup global mocks
 */
function setupGlobalMocks() {
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

  // Mock window.ResizeObserver
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }))

  // Mock window.IntersectionObserver
  global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }))

  // Mock window.scrollTo
  Object.defineProperty(window, 'scrollTo', {
    writable: true,
    value: vi.fn(),
  })

  // Mock window.location
  Object.defineProperty(window, 'location', {
    writable: true,
    value: {
      href: 'http://localhost:3000',
      origin: 'http://localhost:3000',
      pathname: '/',
      search: '',
      hash: '',
      assign: vi.fn(),
      replace: vi.fn(),
      reload: vi.fn(),
    },
  })

  // Mock localStorage
  const localStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
    length: 0,
    key: vi.fn(),
  }
  Object.defineProperty(window, 'localStorage', {
    writable: true,
    value: localStorageMock,
  })

  // Mock sessionStorage
  const sessionStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
    length: 0,
    key: vi.fn(),
  }
  Object.defineProperty(window, 'sessionStorage', {
    writable: true,
    value: sessionStorageMock,
  })

  // Mock fetch
  global.fetch = vi.fn()

  // Mock console methods for cleaner test output
  global.console = {
    ...console,
    log: vi.fn(),
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }

  // Mock performance API
  Object.defineProperty(window, 'performance', {
    writable: true,
    value: {
      mark: vi.fn(),
      measure: vi.fn(),
      now: vi.fn(() => Date.now()),
      getEntriesByType: vi.fn(() => []),
      getEntriesByName: vi.fn(() => []),
      clearMarks: vi.fn(),
      clearMeasures: vi.fn(),
    },
  })

  // Mock requestAnimationFrame
  global.requestAnimationFrame = vi.fn(cb => setTimeout(cb, 16))
  global.cancelAnimationFrame = vi.fn(id => clearTimeout(id))

  // Mock requestIdleCallback
  global.requestIdleCallback = vi.fn(cb => setTimeout(cb, 1))
  global.cancelIdleCallback = vi.fn(id => clearTimeout(id))
}

/**
 * Setup test environment
 */
function setupTestEnvironment() {
  // Set test environment variables
  process.env.NODE_ENV = 'test'
  process.env.VITE_API_URL = 'http://localhost:3001/api'
  process.env.VITE_BASE44_API_URL = 'http://localhost:3002'

  // Setup global test utilities
  global.testUtils = {
    // Wait for element to appear
    waitForElement: async (selector, timeout = 5000) => {
      const start = Date.now()
      while (Date.now() - start < timeout) {
        const element = document.querySelector(selector)
        if (element) return element
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      throw new Error(`Element ${selector} not found within ${timeout}ms`)
    },

    // Wait for condition to be true
    waitFor: async (condition, timeout = 5000) => {
      const start = Date.now()
      while (Date.now() - start < timeout) {
        if (await condition()) return true
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      throw new Error(`Condition not met within ${timeout}ms`)
    },

    // Sleep utility
    sleep: (ms) => new Promise(resolve => setTimeout(resolve, ms)),

    // Mock API response
    mockApiResponse: (data, status = 200) => ({
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? 'OK' : 'Error',
      json: () => Promise.resolve(data),
      text: () => Promise.resolve(JSON.stringify(data)),
      headers: new Map([['content-type', 'application/json']]),
    }),

    // Create mock user
    createMockUser: (overrides = {}) => ({
      id: 'test-user-1',
      email: 'test@example.com',
      name: 'Test User',
      tier: 'startup',
      company: 'Test Company',
      avatar: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ...overrides,
    }),

    // Create mock campaign
    createMockCampaign: (overrides = {}) => ({
      id: 'test-campaign-1',
      name: 'Test Campaign',
      status: 'active',
      type: 'social',
      description: 'Test campaign description',
      budget: 1000,
      startDate: new Date().toISOString(),
      endDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      createdBy: 'test-user-1',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ...overrides,
    }),

    // Create mock agent
    createMockAgent: (overrides = {}) => ({
      id: 'test-agent-1',
      name: 'Test Agent',
      type: 'content-creation',
      description: 'Test agent description',
      capabilities: ['content-generation', 'social-media'],
      tier: 'startup',
      status: 'active',
      usageCount: 0,
      rating: 4.5,
      ...overrides,
    }),

    // Create mock analytics data
    createMockAnalytics: (overrides = {}) => ({
      metrics: {
        totalUsers: 1000,
        activeUsers: 750,
        totalSessions: 5000,
        avgSessionDuration: 300,
        bounceRate: 0.25,
        conversionRate: 0.05,
      },
      timeRange: '30d',
      data: [
        { date: '2024-01-01', users: 100, sessions: 250 },
        { date: '2024-01-02', users: 120, sessions: 300 },
        { date: '2024-01-03', users: 110, sessions: 275 },
      ],
      loading: false,
      ...overrides,
    }),

    // Mock form validation
    mockFormValidation: (isValid = true, errors = {}) => ({
      isValid,
      errors,
      touched: {},
      values: {},
    }),

    // Mock API error
    createMockError: (message = 'Test error', status = 400) => {
      const error = new Error(message)
      error.status = status
      error.response = {
        status,
        statusText: 'Bad Request',
        data: { error: message },
      }
      return error
    },
  }

  // Setup test data
  global.testData = {
    users: [global.testUtils.createMockUser()],
    campaigns: [global.testUtils.createMockCampaign()],
    agents: [global.testUtils.createMockAgent()],
    analytics: global.testUtils.createMockAnalytics(),
  }
}

// Export test utilities for use in tests
export { testingService }
export const {
  waitForElement,
  waitFor,
  sleep,
  mockApiResponse,
  createMockUser,
  createMockCampaign,
  createMockAgent,
  createMockAnalytics,
  mockFormValidation,
  createMockError,
} = global.testUtils || {}

export const { users, campaigns, agents, analytics } = global.testData || {}
