/**
 * Performance Optimization Utilities
 * Code splitting, lazy loading, and performance enhancements
 */

import { lazy, memo, useMemo, useCallback, useState, useEffect } from 'react'

/**
 * Enhanced lazy loading with error boundaries and loading states
 */
export const createLazyComponent = (importFn, fallback = null) => {
  const LazyComponent = lazy(importFn)
  
  return memo((props) => (
    <ErrorBoundary fallback={<ComponentError />}>
      <Suspense fallback={fallback || <ComponentLoader />}>
        <LazyComponent {...props} />
      </Suspense>
    </ErrorBoundary>
  ))
}

/**
 * Component loader with skeleton
 */
export const ComponentLoader = memo(({ className = '', height = 'h-32' }) => (
  <div className={`animate-pulse ${className}`}>
    <div className={`bg-gray-200 rounded ${height} w-full`}></div>
  </div>
))

/**
 * Error boundary component
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Component error:', error, errorInfo)
    // Log to error tracking service
    if (window.analytics) {
      window.analytics.track('Component Error', {
        error: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack
      })
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || <ComponentError />
    }

    return this.props.children
  }
}

/**
 * Component error fallback
 */
const ComponentError = memo(() => (
  <div className="p-4 border border-red-200 rounded-lg bg-red-50">
    <div className="flex items-center gap-2 text-red-800">
      <AlertTriangle className="w-4 h-4" />
      <span className="font-medium">Component Error</span>
    </div>
    <p className="text-sm text-red-600 mt-1">
      Something went wrong loading this component. Please refresh the page.
    </p>
  </div>
))

/**
 * Debounced value hook for performance optimization
 */
export const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

/**
 * Throttled callback hook
 */
export const useThrottle = (callback, delay) => {
  const [lastRun, setLastRun] = useState(Date.now())

  return useCallback((...args) => {
    if (Date.now() - lastRun >= delay) {
      callback(...args)
      setLastRun(Date.now())
    }
  }, [callback, delay, lastRun])
}

/**
 * Memoized expensive calculations
 */
export const useMemoizedCalculation = (data, dependencies = []) => {
  return useMemo(() => {
    if (!data || data.length === 0) return null
    
    // Expensive calculations here
    const processed = data.map(item => ({
      ...item,
      calculated: performExpensiveCalculation(item)
    }))
    
    return processed
  }, [data, ...dependencies])
}

/**
 * Virtual scrolling hook for large lists
 */
export const useVirtualScroll = (items, itemHeight, containerHeight) => {
  const [scrollTop, setScrollTop] = useState(0)
  
  const visibleItems = useMemo(() => {
    const startIndex = Math.floor(scrollTop / itemHeight)
    const endIndex = Math.min(
      startIndex + Math.ceil(containerHeight / itemHeight) + 1,
      items.length
    )
    
    return {
      startIndex,
      endIndex,
      items: items.slice(startIndex, endIndex),
      totalHeight: items.length * itemHeight,
      offsetY: startIndex * itemHeight
    }
  }, [items, itemHeight, containerHeight, scrollTop])
  
  const handleScroll = useCallback((e) => {
    setScrollTop(e.target.scrollTop)
  }, [])
  
  return { visibleItems, handleScroll }
}

/**
 * Image lazy loading hook
 */
export const useLazyImage = (src, placeholder = null) => {
  const [imageSrc, setImageSrc] = useState(placeholder)
  const [isLoaded, setIsLoaded] = useState(false)
  const [isError, setIsError] = useState(false)

  useEffect(() => {
    if (!src) return

    const img = new Image()
    
    img.onload = () => {
      setImageSrc(src)
      setIsLoaded(true)
    }
    
    img.onerror = () => {
      setIsError(true)
    }
    
    img.src = src
    
    return () => {
      img.onload = null
      img.onerror = null
    }
  }, [src])

  return { imageSrc, isLoaded, isError }
}

/**
 * Intersection Observer hook for lazy loading
 */
export const useIntersectionObserver = (options = {}) => {
  const [isIntersecting, setIsIntersecting] = useState(false)
  const [ref, setRef] = useState(null)

  useEffect(() => {
    if (!ref) return

    const observer = new IntersectionObserver(([entry]) => {
      setIsIntersecting(entry.isIntersecting)
    }, {
      threshold: 0.1,
      rootMargin: '50px',
      ...options
    })

    observer.observe(ref)

    return () => {
      observer.disconnect()
    }
  }, [ref, options])

  return [setRef, isIntersecting]
}

/**
 * Performance monitoring hook
 */
export const usePerformanceMonitor = (componentName) => {
  useEffect(() => {
    const startTime = performance.now()
    
    return () => {
      const endTime = performance.now()
      const renderTime = endTime - startTime
      
      // Log performance metrics
      if (renderTime > 100) { // Log slow renders
        console.warn(`Slow render detected in ${componentName}: ${renderTime.toFixed(2)}ms`)
        
        if (window.analytics) {
          window.analytics.track('Slow Component Render', {
            component: componentName,
            renderTime: renderTime,
            timestamp: Date.now()
          })
        }
      }
    }
  })
}

/**
 * Memory usage monitoring
 */
export const useMemoryMonitor = () => {
  const [memoryInfo, setMemoryInfo] = useState(null)

  useEffect(() => {
    const updateMemoryInfo = () => {
      if (performance.memory) {
        setMemoryInfo({
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize,
          jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
        })
      }
    }

    updateMemoryInfo()
    const interval = setInterval(updateMemoryInfo, 5000) // Update every 5 seconds

    return () => clearInterval(interval)
  }, [])

  return memoryInfo
}

/**
 * Bundle size analyzer
 */
export const analyzeBundleSize = () => {
  if (process.env.NODE_ENV === 'development') {
    import('webpack-bundle-analyzer').then(({ BundleAnalyzerPlugin }) => {
      console.log('Bundle analyzer available in development mode')
    })
  }
}

/**
 * Code splitting utilities
 */
export const createRouteComponent = (importFn) => {
  return createLazyComponent(importFn, <RouteLoader />)
}

const RouteLoader = memo(() => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-gray-600">Loading page...</p>
    </div>
  </div>
))

/**
 * Resource preloading
 */
export const preloadResource = (href, as = 'script') => {
  const link = document.createElement('link')
  link.rel = 'preload'
  link.href = href
  link.as = as
  document.head.appendChild(link)
}

/**
 * Critical CSS inlining
 */
export const inlineCriticalCSS = (css) => {
  const style = document.createElement('style')
  style.textContent = css
  document.head.appendChild(style)
}

/**
 * Service Worker registration for caching
 */
export const registerServiceWorker = async () => {
  if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js')
      console.log('Service Worker registered:', registration)
      
      // Update available
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // New content available
            if (window.confirm('New version available. Refresh to update?')) {
              window.location.reload()
            }
          }
        })
      })
      
      return registration
    } catch (error) {
      console.error('Service Worker registration failed:', error)
    }
  }
}

/**
 * Web Vitals monitoring
 */
export const initWebVitals = () => {
  if (typeof window !== 'undefined') {
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS(console.log)
      getFID(console.log)
      getFCP(console.log)
      getLCP(console.log)
      getTTFB(console.log)
    })
  }
}

/**
 * Performance optimization HOC
 */
export const withPerformanceOptimization = (WrappedComponent, options = {}) => {
  const OptimizedComponent = memo((props) => {
    usePerformanceMonitor(WrappedComponent.displayName || WrappedComponent.name)
    
    return <WrappedComponent {...props} />
  })
  
  OptimizedComponent.displayName = `withPerformanceOptimization(${WrappedComponent.displayName || WrappedComponent.name})`
  
  return OptimizedComponent
}

// Helper functions
function performExpensiveCalculation(item) {
  // Simulate expensive calculation
  return item.value * Math.random()
}

// Export performance utilities
export default {
  createLazyComponent,
  ComponentLoader,
  useDebounce,
  useThrottle,
  useMemoizedCalculation,
  useVirtualScroll,
  useLazyImage,
  useIntersectionObserver,
  usePerformanceMonitor,
  useMemoryMonitor,
  analyzeBundleSize,
  createRouteComponent,
  preloadResource,
  inlineCriticalCSS,
  registerServiceWorker,
  initWebVitals,
  withPerformanceOptimization
}
