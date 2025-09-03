/**
 * Test Utilities
 * Helper functions and components for testing
 */

import React from 'react'
import { render } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi } from 'vitest'

/**
 * Custom render function with providers
 * @param {React.Component} ui - Component to render
 * @param {Object} options - Render options
 * @returns {Object} Render result with utilities
 */
export function renderWithProviders(ui, options = {}) {
  const {
    initialEntries = ['/'],
    queryClient = createTestQueryClient(),
    ...renderOptions
  } = options

  function Wrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </QueryClientProvider>
    )
  }

  const result = render(ui, { wrapper: Wrapper, ...renderOptions })

  return {
    ...result,
    queryClient,
  }
}

/**
 * Create test query client
 * @returns {QueryClient} Test query client
 */
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    },
  })
}

/**
 * Mock React Router hooks
 */
export const mockRouterHooks = {
  useNavigate: vi.fn(),
  useLocation: vi.fn(() => ({
    pathname: '/',
    search: '',
    hash: '',
    state: null,
  })),
  useParams: vi.fn(() => ({})),
  useSearchParams: vi.fn(() => [new URLSearchParams(), vi.fn()]),
}

/**
 * Mock authentication context
 */
export const mockAuthContext = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  updateProfile: vi.fn(),
}

/**
 * Mock API client
 */
export const mockApiClient = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
  request: vi.fn(),
}

/**
 * Mock Base44 client
 */
export const mockBase44Client = {
  auth: {
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    refreshToken: vi.fn(),
  },
  entities: {
    campaigns: {
      create: vi.fn(),
      get: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      list: vi.fn(),
    },
    users: {
      create: vi.fn(),
      get: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      list: vi.fn(),
    },
    agents: {
      create: vi.fn(),
      get: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      list: vi.fn(),
    },
  },
  integrations: {
    invokeLLM: vi.fn(),
    sendEmail: vi.fn(),
    uploadFile: vi.fn(),
  },
  analytics: {
    query: vi.fn(),
    track: vi.fn(),
  },
}

/**
 * Mock services
 */
export const mockServices = {
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    updateProfile: vi.fn(),
  },
  campaignService: {
    createCampaign: vi.fn(),
    getCampaigns: vi.fn(),
    updateCampaign: vi.fn(),
    deleteCampaign: vi.fn(),
  },
  agentService: {
    getAgents: vi.fn(),
    executeAgent: vi.fn(),
    getAgentHistory: vi.fn(),
  },
  analyticsService: {
    getMetrics: vi.fn(),
    trackEvent: vi.fn(),
    generateReport: vi.fn(),
  },
}

/**
 * Mock hooks
 */
export const mockHooks = {
  useAuth: vi.fn(() => mockAuthContext),
  useApi: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
    mutate: vi.fn(),
  })),
  useForm: vi.fn(() => ({
    values: {},
    errors: {},
    touched: {},
    handleChange: vi.fn(),
    handleBlur: vi.fn(),
    handleSubmit: vi.fn(),
    setFieldValue: vi.fn(),
    setFieldError: vi.fn(),
    resetForm: vi.fn(),
  })),
}

/**
 * Test data factories
 */
export const testDataFactories = {
  user: (overrides = {}) => ({
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

  campaign: (overrides = {}) => ({
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

  agent: (overrides = {}) => ({
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

  analytics: (overrides = {}) => ({
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

  apiResponse: (data, status = 200) => ({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
    headers: new Map([['content-type', 'application/json']]),
  }),

  apiError: (message = 'Test error', status = 400) => {
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

/**
 * Test assertions helpers
 */
export const testAssertions = {
  /**
   * Assert element has accessible name
   * @param {HTMLElement} element - Element to check
   * @param {string} expectedName - Expected accessible name
   */
  toHaveAccessibleName: (element, expectedName) => {
    const accessibleName = element.getAttribute('aria-label') || 
                          element.getAttribute('aria-labelledby') || 
                          element.textContent?.trim()
    expect(accessibleName).toBe(expectedName)
  },

  /**
   * Assert element is keyboard accessible
   * @param {HTMLElement} element - Element to check
   */
  toBeKeyboardAccessible: (element) => {
    expect(element).toHaveAttribute('tabindex')
    expect(element.getAttribute('tabindex')).not.toBe('-1')
  },

  /**
   * Assert form field has proper labeling
   * @param {HTMLElement} field - Form field element
   */
  toHaveProperLabeling: (field) => {
    const id = field.getAttribute('id')
    const ariaLabel = field.getAttribute('aria-label')
    const ariaLabelledBy = field.getAttribute('aria-labelledby')
    const label = id ? document.querySelector(`label[for="${id}"]`) : null

    expect(ariaLabel || ariaLabelledBy || label).toBeTruthy()
  },

  /**
   * Assert API call was made with correct parameters
   * @param {Function} mockFn - Mock function
   * @param {string} endpoint - Expected endpoint
   * @param {Object} expectedData - Expected data
   */
  toHaveBeenCalledWithEndpoint: (mockFn, endpoint, expectedData) => {
    expect(mockFn).toHaveBeenCalledWith(
      expect.stringContaining(endpoint),
      expect.objectContaining(expectedData)
    )
  },
}

/**
 * Performance testing utilities
 */
export const performanceUtils = {
  /**
   * Measure component render time
   * @param {Function} renderFn - Function that renders component
   * @returns {number} Render time in milliseconds
   */
  measureRenderTime: async (renderFn) => {
    const start = performance.now()
    await renderFn()
    const end = performance.now()
    return end - start
  },

  /**
   * Measure memory usage
   * @returns {Object} Memory usage information
   */
  measureMemoryUsage: () => {
    if (performance.memory) {
      return {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit,
      }
    }
    return null
  },

  /**
   * Assert render time is within acceptable range
   * @param {number} renderTime - Render time in milliseconds
   * @param {number} maxTime - Maximum acceptable time
   */
  assertRenderTimeWithinRange: (renderTime, maxTime = 100) => {
    expect(renderTime).toBeLessThan(maxTime)
  },
}

/**
 * Accessibility testing utilities
 */
export const a11yUtils = {
  /**
   * Check if element has proper ARIA attributes
   * @param {HTMLElement} element - Element to check
   * @returns {Object} ARIA validation result
   */
  validateAriaAttributes: (element) => {
    const ariaAttributes = {}
    for (const attr of element.attributes) {
      if (attr.name.startsWith('aria-')) {
        ariaAttributes[attr.name] = attr.value
      }
    }
    return ariaAttributes
  },

  /**
   * Check color contrast ratio
   * @param {HTMLElement} element - Element to check
   * @returns {number} Contrast ratio
   */
  checkColorContrast: (element) => {
    // This would integrate with a color contrast checking library
    // For now, return a mock value
    return 4.5
  },

  /**
   * Simulate keyboard navigation
   * @param {HTMLElement} element - Starting element
   * @param {string} key - Key to press
   */
  simulateKeyboardNavigation: (element, key) => {
    element.focus()
    element.dispatchEvent(new KeyboardEvent('keydown', { key }))
  },
}

export default {
  renderWithProviders,
  createTestQueryClient,
  mockRouterHooks,
  mockAuthContext,
  mockApiClient,
  mockBase44Client,
  mockServices,
  mockHooks,
  testDataFactories,
  testAssertions,
  performanceUtils,
  a11yUtils,
}
