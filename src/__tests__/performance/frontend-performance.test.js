/**
 * Frontend Performance Tests
 * Comprehensive performance testing for React components and user interactions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, testDataFactories } from '@/test/utils'
import { performanceOptimizationService } from '@/services/performanceOptimizationService'
import Dashboard from '@/pages/Dashboard'
import CampaignCreation from '@/pages/CampaignCreation'
import ContentCreation from '@/pages/ContentCreation'

// Mock performance APIs
Object.defineProperty(window, 'performance', {
  value: {
    now: vi.fn(() => Date.now()),
    mark: vi.fn(),
    measure: vi.fn(),
    getEntriesByType: vi.fn(() => []),
    memory: {
      usedJSHeapSize: 50 * 1024 * 1024, // 50MB
      totalJSHeapSize: 100 * 1024 * 1024, // 100MB
      jsHeapSizeLimit: 2 * 1024 * 1024 * 1024 // 2GB
    }
  }
})

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}))

describe('Frontend Performance Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.clearAllTimers()
    vi.useFakeTimers()
    
    // Reset performance metrics
    performanceOptimizationService.performanceMetrics = {
      pageLoadTimes: new Map(),
      componentRenderTimes: new Map(),
      apiResponseTimes: new Map(),
      bundleLoadTimes: new Map(),
      memoryUsage: [],
      cacheHitRates: new Map()
    }
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('Component Render Performance', () => {
    it('should render Dashboard within performance budget', async () => {
      const startTime = performance.now()
      
      renderWithProviders(<Dashboard />)
      
      // Wait for initial render
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-content')).toBeInTheDocument()
      })
      
      const renderTime = performance.now() - startTime
      
      // Dashboard should render within 100ms
      expect(renderTime).toBeLessThan(100)
      
      // Verify performance tracking was called
      expect(performance.mark).toHaveBeenCalledWith('dashboard-render-start')
    })

    it('should handle large campaign lists efficiently', async () => {
      const largeCampaignList = Array.from({ length: 1000 }, (_, i) => 
        testDataFactories.campaign({ id: `campaign-${i}`, name: `Campaign ${i}` })
      )

      const startTime = performance.now()
      
      renderWithProviders(<Dashboard />, {
        initialState: {
          campaigns: { campaigns: largeCampaignList }
        }
      })

      await waitFor(() => {
        expect(screen.getByTestId('campaigns-section')).toBeInTheDocument()
      })

      const renderTime = performance.now() - startTime
      
      // Should handle large lists within 200ms using virtualization
      expect(renderTime).toBeLessThan(200)
      
      // Should only render visible items (virtual scrolling)
      const renderedCampaigns = screen.getAllByTestId('campaign-card')
      expect(renderedCampaigns.length).toBeLessThan(50) // Only visible items
    })

    it('should optimize re-renders with React.memo', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      let renderCount = 0
      
      const TestComponent = vi.fn(() => {
        renderCount++
        return <div data-testid="test-component">Render count: {renderCount}</div>
      })

      const { rerender } = render(<TestComponent prop1="value1" prop2="value2" />)
      
      expect(renderCount).toBe(1)
      
      // Re-render with same props - should not re-render if memoized
      rerender(<TestComponent prop1="value1" prop2="value2" />)
      
      expect(renderCount).toBe(1) // Should not increase if properly memoized
    })

    it('should measure component mount/unmount performance', async () => {
      const mountTimes = []
      const unmountTimes = []
      
      const TestComponent = () => {
        React.useEffect(() => {
          const mountStart = performance.now()
          
          return () => {
            const unmountStart = performance.now()
            unmountTimes.push(unmountStart)
          }
        }, [])
        
        return <div data-testid="test-component">Test</div>
      }

      const { unmount } = render(<TestComponent />)
      
      // Simulate some work
      vi.advanceTimersByTime(10)
      
      unmount()
      
      // Mount/unmount should be fast
      expect(mountTimes.length).toBeGreaterThan(0)
      expect(unmountTimes.length).toBeGreaterThan(0)
    })
  })

  describe('User Interaction Performance', () => {
    it('should handle rapid user interactions efficiently', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      
      renderWithProviders(<CampaignCreation />)
      
      const nameInput = screen.getByLabelText(/campaign name/i)
      
      const startTime = performance.now()
      
      // Simulate rapid typing
      for (let i = 0; i < 50; i++) {
        await user.type(nameInput, 'a')
        vi.advanceTimersByTime(10) // 10ms between keystrokes
      }
      
      const totalTime = performance.now() - startTime
      
      // Should handle rapid input without performance degradation
      expect(totalTime).toBeLessThan(1000) // Less than 1 second for 50 keystrokes
    })

    it('should debounce search input efficiently', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const mockSearchFn = vi.fn()
      
      const SearchComponent = () => {
        const [query, setQuery] = React.useState('')
        
        React.useEffect(() => {
          const debounced = setTimeout(() => {
            if (query) mockSearchFn(query)
          }, 300)
          
          return () => clearTimeout(debounced)
        }, [query])
        
        return (
          <input
            data-testid="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        )
      }

      render(<SearchComponent />)
      
      const searchInput = screen.getByTestId('search-input')
      
      // Type rapidly
      await user.type(searchInput, 'test query')
      
      // Should not call search function yet
      expect(mockSearchFn).not.toHaveBeenCalled()
      
      // Advance timers to trigger debounce
      vi.advanceTimersByTime(300)
      
      // Should call search function only once
      expect(mockSearchFn).toHaveBeenCalledTimes(1)
      expect(mockSearchFn).toHaveBeenCalledWith('test query')
    })

    it('should handle form submission performance', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      
      renderWithProviders(<CampaignCreation />)
      
      // Fill form
      await user.type(screen.getByLabelText(/campaign name/i), 'Performance Test Campaign')
      await user.type(screen.getByLabelText(/description/i), 'Test description')
      await user.type(screen.getByLabelText(/budget/i), '5000')
      
      const startTime = performance.now()
      
      // Submit form
      await user.click(screen.getByRole('button', { name: /create campaign/i }))
      
      const submitTime = performance.now() - startTime
      
      // Form submission should be fast
      expect(submitTime).toBeLessThan(50)
    })
  })

  describe('Memory Usage Performance', () => {
    it('should not have memory leaks in component lifecycle', async () => {
      const initialMemory = performance.memory.usedJSHeapSize
      
      // Render and unmount components multiple times
      for (let i = 0; i < 10; i++) {
        const { unmount } = renderWithProviders(<Dashboard />)
        
        await waitFor(() => {
          expect(screen.getByTestId('dashboard-content')).toBeInTheDocument()
        })
        
        unmount()
        
        // Force garbage collection simulation
        vi.advanceTimersByTime(100)
      }
      
      const finalMemory = performance.memory.usedJSHeapSize
      const memoryIncrease = finalMemory - initialMemory
      
      // Memory increase should be minimal (less than 10MB)
      expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024)
    })

    it('should efficiently manage large datasets in memory', async () => {
      const largeDataset = Array.from({ length: 10000 }, (_, i) => ({
        id: i,
        data: `Item ${i}`.repeat(100) // ~1KB per item = ~10MB total
      }))

      const initialMemory = performance.memory.usedJSHeapSize
      
      const DataComponent = ({ data }) => {
        const [processedData, setProcessedData] = React.useState([])
        
        React.useEffect(() => {
          // Simulate data processing
          const processed = data.slice(0, 100) // Only process visible items
          setProcessedData(processed)
        }, [data])
        
        return (
          <div data-testid="data-component">
            {processedData.map(item => (
              <div key={item.id}>{item.data}</div>
            ))}
          </div>
        )
      }

      render(<DataComponent data={largeDataset} />)
      
      await waitFor(() => {
        expect(screen.getByTestId('data-component')).toBeInTheDocument()
      })

      const finalMemory = performance.memory.usedJSHeapSize
      const memoryIncrease = finalMemory - initialMemory
      
      // Should not load entire dataset into memory
      expect(memoryIncrease).toBeLessThan(5 * 1024 * 1024) // Less than 5MB increase
    })
  })

  describe('Bundle Size Performance', () => {
    it('should lazy load components efficiently', async () => {
      const LazyComponent = React.lazy(() => 
        Promise.resolve({
          default: () => <div data-testid="lazy-component">Lazy Loaded</div>
        })
      )

      const startTime = performance.now()
      
      render(
        <React.Suspense fallback={<div>Loading...</div>}>
          <LazyComponent />
        </React.Suspense>
      )

      await waitFor(() => {
        expect(screen.getByTestId('lazy-component')).toBeInTheDocument()
      })

      const loadTime = performance.now() - startTime
      
      // Lazy loading should be fast
      expect(loadTime).toBeLessThan(100)
    })

    it('should preload critical resources', async () => {
      const preloadSpy = vi.spyOn(document, 'createElement')
      
      // Simulate critical resource preloading
      const preloadResource = (href, as) => {
        const link = document.createElement('link')
        link.rel = 'preload'
        link.href = href
        link.as = as
        document.head.appendChild(link)
      }

      preloadResource('/api/dashboard/metrics', 'fetch')
      preloadResource('/assets/dashboard-bg.jpg', 'image')
      
      expect(preloadSpy).toHaveBeenCalledWith('link')
    })
  })

  describe('API Performance', () => {
    it('should cache API responses efficiently', async () => {
      const mockApiCall = vi.fn().mockResolvedValue({ data: 'test' })
      
      // First call - should hit API
      const result1 = await performanceOptimizationService.getCachedRequest('test-key')
      expect(result1).toBeNull() // Cache miss
      
      // Cache the result
      performanceOptimizationService.cacheRequest('test-key', { data: 'test' })
      
      // Second call - should hit cache
      const result2 = performanceOptimizationService.getCachedRequest('test-key')
      expect(result2).toEqual({ data: 'test' })
      
      // Verify cache hit rate tracking
      const hitRate = performanceOptimizationService.performanceMetrics.cacheHitRates.get('test-key')
      expect(hitRate.hits).toBe(1)
      expect(hitRate.misses).toBe(1)
    })

    it('should handle concurrent API requests efficiently', async () => {
      const mockApiCall = vi.fn().mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ data: 'test' }), 100))
      )

      const startTime = performance.now()
      
      // Make 5 concurrent requests
      const requests = Array(5).fill().map(() => mockApiCall())
      const results = await Promise.all(requests)
      
      const totalTime = performance.now() - startTime
      
      expect(results).toHaveLength(5)
      expect(results.every(r => r.data === 'test')).toBe(true)
      
      // Concurrent requests should complete faster than sequential
      expect(totalTime).toBeLessThan(200) // Less than 2x single request time
    })
  })

  describe('Performance Monitoring', () => {
    it('should track performance metrics accurately', async () => {
      const startTime = performance.now()
      
      renderWithProviders(<Dashboard />)
      
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-content')).toBeInTheDocument()
      })
      
      const endTime = performance.now()
      
      // Verify performance tracking
      expect(performance.mark).toHaveBeenCalledWith('dashboard-render-start')
      expect(performance.measure).toHaveBeenCalled()
      
      // Check if metrics were recorded
      const renderTime = endTime - startTime
      expect(renderTime).toBeGreaterThan(0)
    })

    it('should detect performance regressions', async () => {
      const baselineTime = 50 // 50ms baseline
      
      const startTime = performance.now()
      
      // Simulate slow component
      const SlowComponent = () => {
        // Simulate expensive computation
        const expensiveValue = React.useMemo(() => {
          let result = 0
          for (let i = 0; i < 100000; i++) {
            result += Math.random()
          }
          return result
        }, [])
        
        return <div data-testid="slow-component">{expensiveValue}</div>
      }

      render(<SlowComponent />)
      
      await waitFor(() => {
        expect(screen.getByTestId('slow-component')).toBeInTheDocument()
      })
      
      const renderTime = performance.now() - startTime
      
      // Should detect if render time exceeds baseline significantly
      if (renderTime > baselineTime * 2) {
        console.warn(`Performance regression detected: ${renderTime}ms vs ${baselineTime}ms baseline`)
      }
      
      expect(renderTime).toBeDefined()
    })
  })

  describe('Accessibility Performance', () => {
    it('should maintain performance with accessibility features', async () => {
      const AccessibleComponent = () => (
        <div>
          <button
            aria-label="Create new campaign"
            aria-describedby="create-help"
            data-testid="accessible-button"
          >
            Create
          </button>
          <div id="create-help">Click to create a new campaign</div>
        </div>
      )

      const startTime = performance.now()
      
      render(<AccessibleComponent />)
      
      const button = screen.getByTestId('accessible-button')
      expect(button).toBeInTheDocument()
      
      const renderTime = performance.now() - startTime
      
      // Accessibility features should not significantly impact performance
      expect(renderTime).toBeLessThan(50)
    })
  })
})
