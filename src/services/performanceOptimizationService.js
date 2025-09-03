/**
 * Performance Optimization Service
 * Comprehensive performance optimization and monitoring service
 */

import { auditService } from './auditService';
import { errorHandlingService } from './errorHandlingService';
import { environmentConfig } from '@/config/environment';

class PerformanceOptimizationService {
  constructor() {
    this.performanceMetrics = {
      pageLoadTimes: new Map(),
      componentRenderTimes: new Map(),
      apiResponseTimes: new Map(),
      bundleLoadTimes: new Map(),
      memoryUsage: [],
      cacheHitRates: new Map()
    };
    
    this.optimizationConfig = {
      enableCodeSplitting: environmentConfig.getPerformanceConfig().enableCodeSplitting,
      enableServiceWorker: environmentConfig.getPerformanceConfig().enableServiceWorker,
      cacheDuration: environmentConfig.getPerformanceConfig().cacheDuration,
      enableLazyLoading: true,
      enableMemoization: true,
      enableVirtualization: true
    };
    
    this.performanceObserver = null;
    this.memoryMonitor = null;
  }

  /**
   * Initialize performance optimization service
   */
  async initialize() {
    try {
      console.log('⚡ Initializing Performance Optimization Service...');
      
      // Initialize performance monitoring
      await this.initializePerformanceMonitoring();
      
      // Setup code splitting
      if (this.optimizationConfig.enableCodeSplitting) {
        await this.setupCodeSplitting();
      }
      
      // Initialize service worker
      if (this.optimizationConfig.enableServiceWorker) {
        await this.initializeServiceWorker();
      }
      
      // Setup memory monitoring
      await this.initializeMemoryMonitoring();
      
      // Initialize cache optimization
      await this.initializeCacheOptimization();
      
      console.log('✅ Performance Optimization Service initialized');
      auditService.logSystem.configChange(null, 'performance_optimization_initialized', null, 'initialized');
    } catch (error) {
      console.error('Failed to initialize Performance Optimization Service:', error);
      auditService.logSystem.error(error, 'performance_optimization_initialization');
      throw error;
    }
  }

  /**
   * Initialize performance monitoring
   */
  async initializePerformanceMonitoring() {
    if (typeof window === 'undefined') return;

    // Performance Observer for navigation and resource timing
    if ('PerformanceObserver' in window) {
      this.performanceObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.recordPerformanceEntry(entry);
        }
      });

      this.performanceObserver.observe({ 
        entryTypes: ['navigation', 'resource', 'measure', 'paint'] 
      });
    }

    // Web Vitals monitoring
    if ('web-vitals' in window) {
      const { getCLS, getFID, getFCP, getLCP, getTTFB } = await import('web-vitals');
      
      getCLS(this.recordWebVital.bind(this));
      getFID(this.recordWebVital.bind(this));
      getFCP(this.recordWebVital.bind(this));
      getLCP(this.recordWebVital.bind(this));
      getTTFB(this.recordWebVital.bind(this));
    }

    // Custom performance marks
    this.setupCustomPerformanceMarks();
  }

  /**
   * Record performance entry
   * @param {PerformanceEntry} entry - Performance entry
   */
  recordPerformanceEntry(entry) {
    switch (entry.entryType) {
      case 'navigation':
        this.performanceMetrics.pageLoadTimes.set('navigation', {
          loadTime: entry.loadEventEnd - entry.loadEventStart,
          domContentLoaded: entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart,
          firstPaint: entry.responseEnd - entry.requestStart,
          timestamp: Date.now()
        });
        break;
        
      case 'resource':
        if (entry.name.includes('chunk') || entry.name.includes('.js')) {
          this.performanceMetrics.bundleLoadTimes.set(entry.name, {
            duration: entry.duration,
            size: entry.transferSize,
            timestamp: Date.now()
          });
        }
        break;
        
      case 'measure':
        if (entry.name.startsWith('component-')) {
          const componentName = entry.name.replace('component-', '');
          this.performanceMetrics.componentRenderTimes.set(componentName, {
            duration: entry.duration,
            timestamp: Date.now()
          });
        }
        break;
    }
  }

  /**
   * Record Web Vital metric
   * @param {Object} metric - Web Vital metric
   */
  recordWebVital(metric) {
    auditService.logSystem.info('web_vital_recorded', {
      name: metric.name,
      value: metric.value,
      rating: metric.rating,
      delta: metric.delta
    });

    // Alert on poor performance
    if (metric.rating === 'poor') {
      console.warn(`⚠️ Poor ${metric.name} performance:`, metric.value);
    }
  }

  /**
   * Setup custom performance marks
   */
  setupCustomPerformanceMarks() {
    // Component render timing
    window.markComponentStart = (componentName) => {
      performance.mark(`component-${componentName}-start`);
    };

    window.markComponentEnd = (componentName) => {
      performance.mark(`component-${componentName}-end`);
      performance.measure(
        `component-${componentName}`,
        `component-${componentName}-start`,
        `component-${componentName}-end`
      );
    };

    // API call timing
    window.markApiStart = (endpoint) => {
      performance.mark(`api-${endpoint}-start`);
    };

    window.markApiEnd = (endpoint) => {
      performance.mark(`api-${endpoint}-end`);
      performance.measure(
        `api-${endpoint}`,
        `api-${endpoint}-start`,
        `api-${endpoint}-end`
      );
    };
  }

  /**
   * Setup code splitting configuration
   */
  async setupCodeSplitting() {
    // This would be handled by the build system (Vite)
    // We'll create route-based code splitting configuration
    const codeSplittingConfig = {
      routes: [
        { path: '/dashboard', chunk: 'dashboard' },
        { path: '/analytics', chunk: 'analytics' },
        { path: '/campaigns', chunk: 'campaigns' },
        { path: '/agents', chunk: 'agents' },
        { path: '/social', chunk: 'social' },
        { path: '/reports', chunk: 'reports' }
      ],
      vendors: [
        { name: 'charts', modules: ['recharts', 'chart.js'] },
        { name: 'ui', modules: ['framer-motion', '@radix-ui'] },
        { name: 'utils', modules: ['lodash', 'date-fns'] }
      ]
    };

    // Store configuration for build system
    if (typeof window !== 'undefined') {
      window.__PIKAR_CODE_SPLITTING_CONFIG__ = codeSplittingConfig;
    }
  }

  /**
   * Initialize service worker
   */
  async initializeServiceWorker() {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    try {
      const registration = await navigator.serviceWorker.register('/sw.js');
      console.log('🔧 Service Worker registered:', registration);
      
      // Handle service worker updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // New content available, notify user
            this.notifyServiceWorkerUpdate();
          }
        });
      });
    } catch (error) {
      console.error('Service Worker registration failed:', error);
    }
  }

  /**
   * Initialize memory monitoring
   */
  async initializeMemoryMonitoring() {
    if (typeof window === 'undefined' || !('memory' in performance)) {
      return;
    }

    this.memoryMonitor = setInterval(() => {
      const memInfo = performance.memory;
      this.performanceMetrics.memoryUsage.push({
        used: memInfo.usedJSHeapSize,
        total: memInfo.totalJSHeapSize,
        limit: memInfo.jsHeapSizeLimit,
        timestamp: Date.now()
      });

      // Keep only last 100 entries
      if (this.performanceMetrics.memoryUsage.length > 100) {
        this.performanceMetrics.memoryUsage.shift();
      }

      // Alert on high memory usage
      const usagePercent = (memInfo.usedJSHeapSize / memInfo.jsHeapSizeLimit) * 100;
      if (usagePercent > 80) {
        console.warn('⚠️ High memory usage:', usagePercent.toFixed(2) + '%');
      }
    }, 30000); // Every 30 seconds
  }

  /**
   * Initialize cache optimization
   */
  async initializeCacheOptimization() {
    // Setup request cache
    this.requestCache = new Map();
    this.cacheConfig = {
      maxSize: 100,
      ttl: this.optimizationConfig.cacheDuration * 1000
    };

    // Setup cache cleanup
    setInterval(() => {
      this.cleanupCache();
    }, 60000); // Every minute
  }

  /**
   * Cache API request
   * @param {string} key - Cache key
   * @param {any} data - Data to cache
   * @param {number} ttl - Time to live (optional)
   */
  cacheRequest(key, data, ttl = null) {
    const expiry = Date.now() + (ttl || this.cacheConfig.ttl);
    this.requestCache.set(key, { data, expiry });

    // Update cache hit rates
    const hitRate = this.performanceMetrics.cacheHitRates.get(key) || { hits: 0, misses: 0 };
    this.performanceMetrics.cacheHitRates.set(key, hitRate);
  }

  /**
   * Get cached request
   * @param {string} key - Cache key
   * @returns {any} Cached data or null
   */
  getCachedRequest(key) {
    const cached = this.requestCache.get(key);
    
    if (!cached) {
      // Cache miss
      const hitRate = this.performanceMetrics.cacheHitRates.get(key) || { hits: 0, misses: 0 };
      hitRate.misses++;
      this.performanceMetrics.cacheHitRates.set(key, hitRate);
      return null;
    }

    if (Date.now() > cached.expiry) {
      // Expired
      this.requestCache.delete(key);
      const hitRate = this.performanceMetrics.cacheHitRates.get(key) || { hits: 0, misses: 0 };
      hitRate.misses++;
      this.performanceMetrics.cacheHitRates.set(key, hitRate);
      return null;
    }

    // Cache hit
    const hitRate = this.performanceMetrics.cacheHitRates.get(key) || { hits: 0, misses: 0 };
    hitRate.hits++;
    this.performanceMetrics.cacheHitRates.set(key, hitRate);
    
    return cached.data;
  }

  /**
   * Cleanup expired cache entries
   */
  cleanupCache() {
    const now = Date.now();
    let cleanedCount = 0;

    for (const [key, value] of this.requestCache.entries()) {
      if (now > value.expiry) {
        this.requestCache.delete(key);
        cleanedCount++;
      }
    }

    // Enforce max size
    if (this.requestCache.size > this.cacheConfig.maxSize) {
      const entries = Array.from(this.requestCache.entries());
      entries.sort((a, b) => a[1].expiry - b[1].expiry);
      
      const toRemove = entries.slice(0, this.requestCache.size - this.cacheConfig.maxSize);
      toRemove.forEach(([key]) => this.requestCache.delete(key));
      cleanedCount += toRemove.length;
    }

    if (cleanedCount > 0) {
      console.log(`🧹 Cleaned ${cleanedCount} cache entries`);
    }
  }

  /**
   * Get performance metrics
   * @returns {Object} Performance metrics
   */
  getPerformanceMetrics() {
    const cacheStats = {};
    for (const [key, stats] of this.performanceMetrics.cacheHitRates.entries()) {
      const total = stats.hits + stats.misses;
      cacheStats[key] = {
        hitRate: total > 0 ? (stats.hits / total) * 100 : 0,
        hits: stats.hits,
        misses: stats.misses
      };
    }

    return {
      pageLoad: Object.fromEntries(this.performanceMetrics.pageLoadTimes),
      componentRender: Object.fromEntries(this.performanceMetrics.componentRenderTimes),
      apiResponse: Object.fromEntries(this.performanceMetrics.apiResponseTimes),
      bundleLoad: Object.fromEntries(this.performanceMetrics.bundleLoadTimes),
      memoryUsage: this.performanceMetrics.memoryUsage.slice(-10), // Last 10 entries
      cacheStats,
      cacheSize: this.requestCache.size,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Notify service worker update
   */
  notifyServiceWorkerUpdate() {
    // This would integrate with your notification system
    console.log('🔄 New app version available. Refresh to update.');
  }

  /**
   * Preload critical resources
   * @param {Array} resources - Resources to preload
   */
  preloadResources(resources) {
    if (typeof window === 'undefined') return;

    resources.forEach(resource => {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.href = resource.url;
      link.as = resource.type;
      if (resource.crossorigin) {
        link.crossOrigin = resource.crossorigin;
      }
      document.head.appendChild(link);
    });
  }

  /**
   * Cleanup service
   */
  cleanup() {
    if (this.performanceObserver) {
      this.performanceObserver.disconnect();
    }
    
    if (this.memoryMonitor) {
      clearInterval(this.memoryMonitor);
    }
    
    this.requestCache.clear();
  }
}

// Create and export singleton instance
export const performanceOptimizationService = new PerformanceOptimizationService();

export default performanceOptimizationService;
