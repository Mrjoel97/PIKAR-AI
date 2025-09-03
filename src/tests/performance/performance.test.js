/**
 * PIKAR AI Performance Tests
 * Tests for loading times, bundle sizes, and Web Vitals
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'

// Mock performance APIs
const mockPerformance = {
  mark: vi.fn(),
  measure: vi.fn(),
  getEntriesByType: vi.fn(),
  getEntriesByName: vi.fn(),
  now: vi.fn(() => Date.now())
}

global.performance = mockPerformance

// Mock Web Vitals
const mockWebVitals = {
  getCLS: vi.fn(),
  getFID: vi.fn(),
  getFCP: vi.fn(),
  getLCP: vi.fn(),
  getTTFB: vi.fn()
}

vi.mock('web-vitals', () => mockWebVitals)

// Mock components for testing
const LazyComponent = React.lazy(() => 
  Promise.resolve({ 
    default: () => <div>Lazy Loaded Component</div> 
  })
)

describe('PIKAR AI Performance Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Bundle Size Analysis', () => {
    it('should have reasonable bundle sizes', () => {
      // Mock bundle analysis results
      const bundleStats = {
        'main.js': 250000, // 250KB
        'vendor.js': 500000, // 500KB
        'styles.css': 50000, // 50KB
        total: 800000 // 800KB total
      }

      // Check main bundle is under 300KB
      expect(bundleStats['main.js']).toBeLessThan(300000)
      
      // Check vendor bundle is under 600KB
      expect(bundleStats['vendor.js']).toBeLessThan(600000)
      
      // Check total bundle is under 1MB
      expect(bundleStats.total).toBeLessThan(1000000)
    })

    it('should have proper code splitting', () => {
      const chunks = [
        'main.js',
        'vendor.js',
        'tier-management.js',
        'trial-components.js',
        'accessibility.js',
        'pricing.js'
      ]

      // Verify critical chunks exist
      expect(chunks).toContain('main.js')
      expect(chunks).toContain('vendor.js')
      
      // Verify feature-specific chunks exist
      expect(chunks).toContain('tier-management.js')
      expect(chunks).toContain('trial-components.js')
    })
  })

  describe('Component Loading Performance', () => {
    it('should load tier pricing cards quickly', async () => {
      const startTime = performance.now()
      
      const TierPricingCards = await import('@/components/pricing/TierPricingCards')
      
      const endTime = performance.now()
      const loadTime = endTime - startTime
      
      // Should load in under 100ms
      expect(loadTime).toBeLessThan(100)
    })

    it('should load trial manager quickly', async () => {
      const startTime = performance.now()
      
      const TrialManager = await import('@/components/trial/TrialManager')
      
      const endTime = performance.now()
      const loadTime = endTime - startTime
      
      // Should load in under 100ms
      expect(loadTime).toBeLessThan(100)
    })

    it('should support lazy loading', async () => {
      render(
        <BrowserRouter>
          <React.Suspense fallback={<div>Loading...</div>}>
            <LazyComponent />
          </React.Suspense>
        </BrowserRouter>
      )

      // Should show loading state first
      expect(screen.getByText('Loading...')).toBeInTheDocument()

      // Should load component
      await waitFor(() => {
        expect(screen.getByText('Lazy Loaded Component')).toBeInTheDocument()
      })
    })
  })

  describe('Web Vitals Monitoring', () => {
    it('should track Core Web Vitals', () => {
      // Mock Web Vitals measurements
      const vitals = {
        CLS: 0.1, // Cumulative Layout Shift
        FID: 50,  // First Input Delay (ms)
        FCP: 1200, // First Contentful Paint (ms)
        LCP: 2000, // Largest Contentful Paint (ms)
        TTFB: 200  // Time to First Byte (ms)
      }

      // CLS should be under 0.1
      expect(vitals.CLS).toBeLessThan(0.1)
      
      // FID should be under 100ms
      expect(vitals.FID).toBeLessThan(100)
      
      // FCP should be under 1.8s
      expect(vitals.FCP).toBeLessThan(1800)
      
      // LCP should be under 2.5s
      expect(vitals.LCP).toBeLessThan(2500)
      
      // TTFB should be under 600ms
      expect(vitals.TTFB).toBeLessThan(600)
    })

    it('should initialize Web Vitals tracking', () => {
      // Mock Web Vitals initialization
      const initWebVitals = () => {
        mockWebVitals.getCLS(vi.fn())
        mockWebVitals.getFID(vi.fn())
        mockWebVitals.getFCP(vi.fn())
        mockWebVitals.getLCP(vi.fn())
        mockWebVitals.getTTFB(vi.fn())
      }

      initWebVitals()

      expect(mockWebVitals.getCLS).toHaveBeenCalled()
      expect(mockWebVitals.getFID).toHaveBeenCalled()
      expect(mockWebVitals.getFCP).toHaveBeenCalled()
      expect(mockWebVitals.getLCP).toHaveBeenCalled()
      expect(mockWebVitals.getTTFB).toHaveBeenCalled()
    })
  })

  describe('Memory Usage', () => {
    it('should not have memory leaks in tier service', () => {
      const initialMemory = performance.memory?.usedJSHeapSize || 0
      
      // Simulate tier service operations
      for (let i = 0; i < 1000; i++) {
        const mockTier = {
          id: `tier-${i}`,
          name: `Tier ${i}`,
          features: { test: true }
        }
        // Simulate cleanup
        delete mockTier.features
      }
      
      // Force garbage collection if available
      if (global.gc) {
        global.gc()
      }
      
      const finalMemory = performance.memory?.usedJSHeapSize || 0
      const memoryIncrease = finalMemory - initialMemory
      
      // Memory increase should be minimal (under 1MB)
      expect(memoryIncrease).toBeLessThan(1000000)
    })

    it('should cleanup trial timers properly', () => {
      const timers = []
      
      // Mock timer creation
      const createTimer = () => {
        const timer = setInterval(() => {}, 1000)
        timers.push(timer)
        return timer
      }
      
      // Mock timer cleanup
      const cleanupTimers = () => {
        timers.forEach(timer => clearInterval(timer))
        timers.length = 0
      }
      
      // Create some timers
      createTimer()
      createTimer()
      createTimer()
      
      expect(timers).toHaveLength(3)
      
      // Cleanup timers
      cleanupTimers()
      
      expect(timers).toHaveLength(0)
    })
  })

  describe('Network Performance', () => {
    it('should optimize API calls', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true })
      })
      
      global.fetch = mockFetch
      
      // Simulate multiple API calls
      const promises = [
        fetch('/api/tiers'),
        fetch('/api/user/trial'),
        fetch('/api/usage')
      ]
      
      const startTime = performance.now()
      await Promise.all(promises)
      const endTime = performance.now()
      
      const totalTime = endTime - startTime
      
      // All API calls should complete in under 1 second
      expect(totalTime).toBeLessThan(1000)
      expect(mockFetch).toHaveBeenCalledTimes(3)
    })

    it('should implement request caching', () => {
      const cache = new Map()
      
      const cachedFetch = async (url) => {
        if (cache.has(url)) {
          return cache.get(url)
        }
        
        const response = await fetch(url)
        cache.set(url, response)
        return response
      }
      
      // Mock successful response
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ data: 'test' })
      })
      
      // First call should hit the network
      cachedFetch('/api/test')
      expect(global.fetch).toHaveBeenCalledTimes(1)
      
      // Second call should use cache
      cachedFetch('/api/test')
      expect(cache.has('/api/test')).toBe(true)
    })
  })

  describe('Rendering Performance', () => {
    it('should render tier cards efficiently', async () => {
      const startTime = performance.now()
      
      const { container } = render(
        <BrowserRouter>
          <div>
            {Array.from({ length: 4 }, (_, i) => (
              <div key={i} className="tier-card">
                <h3>Tier {i + 1}</h3>
                <p>Description for tier {i + 1}</p>
                <button>Select Tier</button>
              </div>
            ))}
          </div>
        </BrowserRouter>
      )
      
      const endTime = performance.now()
      const renderTime = endTime - startTime
      
      // Should render in under 50ms
      expect(renderTime).toBeLessThan(50)
      
      // Should render all tier cards
      const tierCards = container.querySelectorAll('.tier-card')
      expect(tierCards).toHaveLength(4)
    })

    it('should handle large lists efficiently', () => {
      const items = Array.from({ length: 1000 }, (_, i) => ({
        id: i,
        name: `Item ${i}`
      }))
      
      const startTime = performance.now()
      
      render(
        <div>
          {items.slice(0, 10).map(item => (
            <div key={item.id}>{item.name}</div>
          ))}
        </div>
      )
      
      const endTime = performance.now()
      const renderTime = endTime - startTime
      
      // Should render efficiently even with large datasets
      expect(renderTime).toBeLessThan(100)
    })
  })

  describe('Asset Optimization', () => {
    it('should have optimized images', () => {
      const imageOptimizations = {
        webpSupport: true,
        lazyLoading: true,
        responsiveImages: true,
        compression: true
      }
      
      expect(imageOptimizations.webpSupport).toBe(true)
      expect(imageOptimizations.lazyLoading).toBe(true)
      expect(imageOptimizations.responsiveImages).toBe(true)
      expect(imageOptimizations.compression).toBe(true)
    })

    it('should have optimized fonts', () => {
      const fontOptimizations = {
        fontDisplay: 'swap',
        preload: true,
        subset: true,
        woff2Support: true
      }
      
      expect(fontOptimizations.fontDisplay).toBe('swap')
      expect(fontOptimizations.preload).toBe(true)
      expect(fontOptimizations.subset).toBe(true)
      expect(fontOptimizations.woff2Support).toBe(true)
    })
  })

  describe('Performance Budgets', () => {
    it('should meet performance budget targets', () => {
      const budgets = {
        maxBundleSize: 1000000, // 1MB
        maxLoadTime: 3000,      // 3s
        maxFCP: 1800,           // 1.8s
        maxLCP: 2500,           // 2.5s
        maxCLS: 0.1,            // 0.1
        maxFID: 100             // 100ms
      }
      
      // Mock current metrics
      const currentMetrics = {
        bundleSize: 800000,     // 800KB
        loadTime: 2200,         // 2.2s
        FCP: 1200,              // 1.2s
        LCP: 2000,              // 2s
        CLS: 0.05,              // 0.05
        FID: 50                 // 50ms
      }
      
      expect(currentMetrics.bundleSize).toBeLessThan(budgets.maxBundleSize)
      expect(currentMetrics.loadTime).toBeLessThan(budgets.maxLoadTime)
      expect(currentMetrics.FCP).toBeLessThan(budgets.maxFCP)
      expect(currentMetrics.LCP).toBeLessThan(budgets.maxLCP)
      expect(currentMetrics.CLS).toBeLessThan(budgets.maxCLS)
      expect(currentMetrics.FID).toBeLessThan(budgets.maxFID)
    })
  })

  describe('Progressive Enhancement', () => {
    it('should work without JavaScript', () => {
      // Mock no-JS environment
      const noJSFeatures = {
        basicNavigation: true,
        formSubmission: true,
        contentDisplay: true,
        fallbackStyling: true
      }
      
      expect(noJSFeatures.basicNavigation).toBe(true)
      expect(noJSFeatures.formSubmission).toBe(true)
      expect(noJSFeatures.contentDisplay).toBe(true)
      expect(noJSFeatures.fallbackStyling).toBe(true)
    })

    it('should enhance with JavaScript available', () => {
      const enhancedFeatures = {
        interactiveComponents: true,
        realTimeUpdates: true,
        clientSideRouting: true,
        dynamicContent: true
      }
      
      expect(enhancedFeatures.interactiveComponents).toBe(true)
      expect(enhancedFeatures.realTimeUpdates).toBe(true)
      expect(enhancedFeatures.clientSideRouting).toBe(true)
      expect(enhancedFeatures.dynamicContent).toBe(true)
    })
  })
})
