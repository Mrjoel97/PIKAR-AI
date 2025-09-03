/**
 * Performance Optimization Hooks
 * Custom hooks for React performance optimization
 */

import { useCallback, useMemo, useRef, useEffect, useState } from 'react';
import { performanceOptimizationService } from '@/services/performanceOptimizationService';

/**
 * Enhanced useCallback with performance tracking
 * @param {Function} callback - Callback function
 * @param {Array} deps - Dependencies
 * @param {string} name - Callback name for tracking
 * @returns {Function} Memoized callback
 */
export const useOptimizedCallback = (callback, deps, name = 'anonymous') => {
  const callbackRef = useRef(callback);
  const depsRef = useRef(deps);
  
  // Track callback recreation
  const recreationCount = useRef(0);
  
  const optimizedCallback = useCallback((...args) => {
    // Performance mark for callback execution
    if (typeof window !== 'undefined' && window.markComponentStart) {
      window.markComponentStart(`callback-${name}`);
    }
    
    try {
      const result = callbackRef.current(...args);
      
      if (typeof window !== 'undefined' && window.markComponentEnd) {
        window.markComponentEnd(`callback-${name}`);
      }
      
      return result;
    } catch (error) {
      if (typeof window !== 'undefined' && window.markComponentEnd) {
        window.markComponentEnd(`callback-${name}`);
      }
      throw error;
    }
  }, deps);
  
  // Track recreations in development
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      recreationCount.current++;
      if (recreationCount.current > 10) {
        console.warn(`Callback "${name}" has been recreated ${recreationCount.current} times. Consider optimizing dependencies.`);
      }
    }
    callbackRef.current = callback;
    depsRef.current = deps;
  }, [callback, ...deps, name]);
  
  return optimizedCallback;
};

/**
 * Enhanced useMemo with performance tracking
 * @param {Function} factory - Factory function
 * @param {Array} deps - Dependencies
 * @param {string} name - Memo name for tracking
 * @returns {any} Memoized value
 */
export const useOptimizedMemo = (factory, deps, name = 'anonymous') => {
  const computationCount = useRef(0);
  
  const memoizedValue = useMemo(() => {
    computationCount.current++;
    
    // Performance mark for computation
    if (typeof window !== 'undefined' && window.markComponentStart) {
      window.markComponentStart(`memo-${name}`);
    }
    
    try {
      const result = factory();
      
      if (typeof window !== 'undefined' && window.markComponentEnd) {
        window.markComponentEnd(`memo-${name}`);
      }
      
      // Warn about excessive recomputations in development
      if (process.env.NODE_ENV === 'development' && computationCount.current > 20) {
        console.warn(`Memo "${name}" has been recomputed ${computationCount.current} times. Consider optimizing dependencies.`);
      }
      
      return result;
    } catch (error) {
      if (typeof window !== 'undefined' && window.markComponentEnd) {
        window.markComponentEnd(`memo-${name}`);
      }
      throw error;
    }
  }, deps);
  
  return memoizedValue;
};

/**
 * Hook for debounced values with performance optimization
 * @param {any} value - Value to debounce
 * @param {number} delay - Debounce delay
 * @returns {any} Debounced value
 */
export const useOptimizedDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  const timeoutRef = useRef();
  
  useEffect(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    timeoutRef.current = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [value, delay]);
  
  return debouncedValue;
};

/**
 * Hook for throttled values
 * @param {any} value - Value to throttle
 * @param {number} limit - Throttle limit in ms
 * @returns {any} Throttled value
 */
export const useThrottle = (value, limit) => {
  const [throttledValue, setThrottledValue] = useState(value);
  const lastRan = useRef(Date.now());
  
  useEffect(() => {
    const handler = setTimeout(() => {
      if (Date.now() - lastRan.current >= limit) {
        setThrottledValue(value);
        lastRan.current = Date.now();
      }
    }, limit - (Date.now() - lastRan.current));
    
    return () => {
      clearTimeout(handler);
    };
  }, [value, limit]);
  
  return throttledValue;
};

/**
 * Hook for intersection observer with performance optimization
 * @param {Object} options - Intersection observer options
 * @returns {Array} [ref, isIntersecting, entry]
 */
export const useIntersectionObserver = (options = {}) => {
  const [isIntersecting, setIsIntersecting] = useState(false);
  const [entry, setEntry] = useState(null);
  const elementRef = useRef();
  
  const { threshold = 0, root = null, rootMargin = '0%', ...restOptions } = options;
  
  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;
    
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsIntersecting(entry.isIntersecting);
        setEntry(entry);
      },
      {
        threshold,
        root,
        rootMargin,
        ...restOptions
      }
    );
    
    observer.observe(element);
    
    return () => {
      observer.unobserve(element);
    };
  }, [threshold, root, rootMargin]);
  
  return [elementRef, isIntersecting, entry];
};

/**
 * Hook for lazy loading images
 * @param {string} src - Image source
 * @param {Object} options - Options
 * @returns {Object} Image loading state
 */
export const useLazyImage = (src, options = {}) => {
  const [imageSrc, setImageSrc] = useState(options.placeholder || '');
  const [isLoaded, setIsLoaded] = useState(false);
  const [isError, setIsError] = useState(false);
  const [ref, isIntersecting] = useIntersectionObserver({
    threshold: 0.1,
    rootMargin: '50px'
  });
  
  useEffect(() => {
    if (isIntersecting && src && !isLoaded && !isError) {
      const img = new Image();
      
      img.onload = () => {
        setImageSrc(src);
        setIsLoaded(true);
      };
      
      img.onerror = () => {
        setIsError(true);
        if (options.fallback) {
          setImageSrc(options.fallback);
        }
      };
      
      img.src = src;
    }
  }, [isIntersecting, src, isLoaded, isError, options.fallback]);
  
  return {
    ref,
    src: imageSrc,
    isLoaded,
    isError,
    isIntersecting
  };
};

/**
 * Hook for virtual scrolling
 * @param {Array} items - Items to virtualize
 * @param {number} itemHeight - Height of each item
 * @param {number} containerHeight - Height of container
 * @param {number} overscan - Number of items to render outside viewport
 * @returns {Object} Virtual scrolling state
 */
export const useVirtualScroll = (items, itemHeight, containerHeight, overscan = 5) => {
  const [scrollTop, setScrollTop] = useState(0);
  const scrollElementRef = useRef();
  
  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIndex = Math.min(items.length - 1, startIndex + visibleCount + overscan * 2);
  
  const visibleItems = useMemo(() => {
    return items.slice(startIndex, endIndex + 1).map((item, index) => ({
      item,
      index: startIndex + index
    }));
  }, [items, startIndex, endIndex]);
  
  const totalHeight = items.length * itemHeight;
  const offsetY = startIndex * itemHeight;
  
  const handleScroll = useOptimizedCallback((e) => {
    setScrollTop(e.target.scrollTop);
  }, [], 'virtualScroll');
  
  return {
    scrollElementRef,
    visibleItems,
    totalHeight,
    offsetY,
    handleScroll
  };
};

/**
 * Hook for request caching
 * @param {string} key - Cache key
 * @param {Function} fetcher - Data fetcher function
 * @param {Object} options - Cache options
 * @returns {Object} Cached request state
 */
export const useCachedRequest = (key, fetcher, options = {}) => {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const { ttl, enabled = true } = options;
  
  const fetchData = useOptimizedCallback(async () => {
    if (!enabled) return;
    
    // Check cache first
    const cached = performanceOptimizationService.getCachedRequest(key);
    if (cached) {
      setData(cached);
      return cached;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await fetcher();
      
      // Cache the result
      performanceOptimizationService.cacheRequest(key, result, ttl);
      
      setData(result);
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [key, fetcher, enabled, ttl], 'cachedRequest');
  
  useEffect(() => {
    fetchData();
  }, [fetchData]);
  
  return {
    data,
    isLoading,
    error,
    refetch: fetchData,
    clearCache: () => performanceOptimizationService.requestCache.delete(key)
  };
};

/**
 * Hook for component performance tracking
 * @param {string} componentName - Component name
 * @returns {Object} Performance tracking utilities
 */
export const usePerformanceTracking = (componentName) => {
  const renderCount = useRef(0);
  const mountTime = useRef(Date.now());
  
  useEffect(() => {
    renderCount.current++;
    
    // Track mount time
    if (typeof window !== 'undefined' && window.markComponentEnd) {
      window.markComponentEnd(`mount-${componentName}`);
    }
    
    return () => {
      // Track unmount
      if (typeof window !== 'undefined' && window.markComponentStart) {
        window.markComponentStart(`unmount-${componentName}`);
      }
    };
  }, [componentName]);
  
  useEffect(() => {
    // Track render
    if (typeof window !== 'undefined' && window.markComponentStart) {
      window.markComponentStart(`render-${componentName}`);
    }
    
    if (typeof window !== 'undefined' && window.markComponentEnd) {
      window.markComponentEnd(`render-${componentName}`);
    }
  });
  
  const trackEvent = useOptimizedCallback((eventName, data = {}) => {
    if (typeof window !== 'undefined' && window.markComponentStart) {
      window.markComponentStart(`event-${componentName}-${eventName}`);
    }
    
    // Log performance event
    console.log(`Performance Event: ${componentName}.${eventName}`, {
      renderCount: renderCount.current,
      mountTime: mountTime.current,
      ...data
    });
    
    if (typeof window !== 'undefined' && window.markComponentEnd) {
      window.markComponentEnd(`event-${componentName}-${eventName}`);
    }
  }, [componentName], 'trackEvent');
  
  return {
    renderCount: renderCount.current,
    mountTime: mountTime.current,
    trackEvent
  };
};

export default {
  useOptimizedCallback,
  useOptimizedMemo,
  useOptimizedDebounce,
  useThrottle,
  useIntersectionObserver,
  useLazyImage,
  useVirtualScroll,
  useCachedRequest,
  usePerformanceTracking
};
