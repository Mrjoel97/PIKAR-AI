/**
 * Monitoring Service
 * Comprehensive application monitoring, metrics collection, and alerting
 */

import { auditService } from './auditService'
import { performanceOptimizationService } from './performanceOptimizationService'
import { environmentConfig } from '@/config/environment'

class MonitoringService {
  constructor() {
    this.metrics = new Map()
    this.alerts = new Map()
    this.thresholds = new Map()
    this.collectors = new Map()
    this.isInitialized = false
    
    // Monitoring configuration
    this.config = {
      metricsInterval: 30000, // 30 seconds
      alertCheckInterval: 60000, // 1 minute
      retentionPeriod: 86400000, // 24 hours
      batchSize: 100,
      maxMetricsInMemory: 10000
    }
    
    // Default thresholds
    this.defaultThresholds = {
      // Performance thresholds
      responseTime: { warning: 1000, critical: 3000 }, // ms
      errorRate: { warning: 0.05, critical: 0.1 }, // 5% warning, 10% critical
      memoryUsage: { warning: 0.8, critical: 0.9 }, // 80% warning, 90% critical
      cpuUsage: { warning: 0.7, critical: 0.9 }, // 70% warning, 90% critical
      
      // Business metrics thresholds
      activeUsers: { warning: 1000, critical: 5000 },
      agentExecutions: { warning: 100, critical: 500 },
      apiCalls: { warning: 1000, critical: 5000 },
      
      // System health thresholds
      diskUsage: { warning: 0.8, critical: 0.95 },
      networkLatency: { warning: 100, critical: 500 }, // ms
      databaseConnections: { warning: 80, critical: 95 } // percentage
    }
    
    this.setupDefaultThresholds()
  }

  /**
   * Initialize monitoring service
   */
  async initialize() {
    try {
      console.log('🔍 Initializing Monitoring Service...')
      
      // Setup metric collectors
      this.setupMetricCollectors()
      
      // Setup alert system
      this.setupAlertSystem()
      
      // Setup performance monitoring
      this.setupPerformanceMonitoring()
      
      // Setup business metrics monitoring
      this.setupBusinessMetricsMonitoring()
      
      // Setup system health monitoring
      this.setupSystemHealthMonitoring()
      
      // Start monitoring intervals
      this.startMonitoringIntervals()
      
      this.isInitialized = true
      
      console.log('✅ Monitoring Service initialized successfully')
      
      // Log initialization
      await auditService.logSystem.monitoring('monitoring_service_initialized', {
        collectors: this.collectors.size,
        thresholds: this.thresholds.size,
        config: this.config
      })
      
    } catch (error) {
      console.error('❌ Monitoring Service initialization failed:', error)
      throw error
    }
  }

  /**
   * Setup default thresholds
   */
  setupDefaultThresholds() {
    for (const [metric, threshold] of Object.entries(this.defaultThresholds)) {
      this.thresholds.set(metric, threshold)
    }
  }

  /**
   * Setup metric collectors
   */
  setupMetricCollectors() {
    // Performance metrics collector
    this.collectors.set('performance', {
      name: 'Performance Metrics',
      collect: this.collectPerformanceMetrics.bind(this),
      interval: 30000 // 30 seconds
    })
    
    // Business metrics collector
    this.collectors.set('business', {
      name: 'Business Metrics',
      collect: this.collectBusinessMetrics.bind(this),
      interval: 60000 // 1 minute
    })
    
    // System health collector
    this.collectors.set('system', {
      name: 'System Health',
      collect: this.collectSystemHealthMetrics.bind(this),
      interval: 30000 // 30 seconds
    })
    
    // User activity collector
    this.collectors.set('user_activity', {
      name: 'User Activity',
      collect: this.collectUserActivityMetrics.bind(this),
      interval: 60000 // 1 minute
    })
    
    // Agent performance collector
    this.collectors.set('agent_performance', {
      name: 'Agent Performance',
      collect: this.collectAgentPerformanceMetrics.bind(this),
      interval: 30000 // 30 seconds
    })
  }

  /**
   * Setup alert system
   */
  setupAlertSystem() {
    // Define alert rules
    const alertRules = [
      {
        name: 'High Error Rate',
        metric: 'errorRate',
        condition: 'greater_than',
        threshold: 'critical',
        severity: 'critical',
        cooldown: 300000 // 5 minutes
      },
      {
        name: 'High Response Time',
        metric: 'responseTime',
        condition: 'greater_than',
        threshold: 'warning',
        severity: 'warning',
        cooldown: 180000 // 3 minutes
      },
      {
        name: 'High Memory Usage',
        metric: 'memoryUsage',
        condition: 'greater_than',
        threshold: 'critical',
        severity: 'critical',
        cooldown: 300000 // 5 minutes
      },
      {
        name: 'Agent Execution Failures',
        metric: 'agentFailureRate',
        condition: 'greater_than',
        threshold: 'warning',
        severity: 'warning',
        cooldown: 180000 // 3 minutes
      }
    ]
    
    alertRules.forEach(rule => {
      this.alerts.set(rule.name, {
        ...rule,
        lastTriggered: null,
        isActive: false
      })
    })
  }

  /**
   * Setup performance monitoring
   */
  setupPerformanceMonitoring() {
    if (typeof window !== 'undefined') {
      // Web Vitals monitoring
      this.setupWebVitalsMonitoring()
      
      // Resource timing monitoring
      this.setupResourceTimingMonitoring()
      
      // Navigation timing monitoring
      this.setupNavigationTimingMonitoring()
    }
  }

  /**
   * Setup Web Vitals monitoring
   */
  setupWebVitalsMonitoring() {
    if ('PerformanceObserver' in window) {
      // Core Web Vitals observer
      const observer = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          this.recordMetric('web_vitals', entry.name, entry.startTime, {
            value: entry.value,
            rating: this.getWebVitalRating(entry.name, entry.value)
          })
        })
      })

      observer.observe({ 
        entryTypes: ['paint', 'largest-contentful-paint', 'layout-shift', 'first-input'] 
      })
    }
  }

  /**
   * Setup resource timing monitoring
   */
  setupResourceTimingMonitoring() {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          if (entry.duration > 1000) { // Only track slow resources
            this.recordMetric('resource_timing', entry.name, entry.startTime, {
              duration: entry.duration,
              size: entry.transferSize,
              type: entry.initiatorType
            })
          }
        })
      })

      observer.observe({ entryTypes: ['resource'] })
    }
  }

  /**
   * Setup navigation timing monitoring
   */
  setupNavigationTimingMonitoring() {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          this.recordMetric('navigation_timing', 'page_load', entry.startTime, {
            domContentLoaded: entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart,
            loadComplete: entry.loadEventEnd - entry.loadEventStart,
            firstByte: entry.responseStart - entry.requestStart,
            domInteractive: entry.domInteractive - entry.navigationStart
          })
        })
      })

      observer.observe({ entryTypes: ['navigation'] })
    }
  }

  /**
   * Setup business metrics monitoring
   */
  setupBusinessMetricsMonitoring() {
    // Track user engagement metrics
    this.trackUserEngagement()
    
    // Track conversion metrics
    this.trackConversionMetrics()
    
    // Track feature usage metrics
    this.trackFeatureUsage()
  }

  /**
   * Setup system health monitoring
   */
  setupSystemHealthMonitoring() {
    // Memory monitoring
    if (typeof performance !== 'undefined' && performance.memory) {
      setInterval(() => {
        const memInfo = performance.memory
        this.recordMetric('system_health', 'memory_usage', Date.now(), {
          used: memInfo.usedJSHeapSize,
          total: memInfo.totalJSHeapSize,
          limit: memInfo.jsHeapSizeLimit,
          percentage: memInfo.usedJSHeapSize / memInfo.jsHeapSizeLimit
        })
      }, 30000)
    }
  }

  /**
   * Start monitoring intervals
   */
  startMonitoringIntervals() {
    // Start metric collection intervals
    for (const [key, collector] of this.collectors.entries()) {
      setInterval(async () => {
        try {
          await collector.collect()
        } catch (error) {
          console.error(`Error collecting ${collector.name} metrics:`, error)
        }
      }, collector.interval)
    }
    
    // Start alert checking interval
    setInterval(() => {
      this.checkAlerts()
    }, this.config.alertCheckInterval)
    
    // Start cleanup interval
    setInterval(() => {
      this.cleanupOldMetrics()
    }, 3600000) // 1 hour
  }

  /**
   * Record a metric
   */
  recordMetric(category, name, timestamp, data = {}) {
    const metricKey = `${category}.${name}`
    
    if (!this.metrics.has(metricKey)) {
      this.metrics.set(metricKey, [])
    }
    
    const metrics = this.metrics.get(metricKey)
    metrics.push({
      timestamp,
      value: data.value || 1,
      data
    })
    
    // Limit metrics in memory
    if (metrics.length > this.config.maxMetricsInMemory) {
      metrics.shift()
    }
    
    // Check for alerts
    this.checkMetricAlerts(metricKey, data.value || 1)
  }

  /**
   * Collect performance metrics
   */
  async collectPerformanceMetrics() {
    const performanceMetrics = performanceOptimizationService.getPerformanceMetrics()
    
    // API response times
    if (performanceMetrics.apiResponseTimes.size > 0) {
      const avgResponseTime = Array.from(performanceMetrics.apiResponseTimes.values())
        .reduce((sum, times) => sum + times.reduce((a, b) => a + b, 0) / times.length, 0) / performanceMetrics.apiResponseTimes.size
      
      this.recordMetric('performance', 'api_response_time', Date.now(), {
        value: avgResponseTime,
        endpoints: performanceMetrics.apiResponseTimes.size
      })
    }
    
    // Component render times
    if (performanceMetrics.componentRenderTimes.size > 0) {
      const avgRenderTime = Array.from(performanceMetrics.componentRenderTimes.values())
        .reduce((sum, times) => sum + times.reduce((a, b) => a + b, 0) / times.length, 0) / performanceMetrics.componentRenderTimes.size
      
      this.recordMetric('performance', 'component_render_time', Date.now(), {
        value: avgRenderTime,
        components: performanceMetrics.componentRenderTimes.size
      })
    }
    
    // Cache hit rates
    if (performanceMetrics.cacheHitRates.size > 0) {
      const totalHits = Array.from(performanceMetrics.cacheHitRates.values())
        .reduce((sum, rate) => sum + rate.hits, 0)
      const totalRequests = Array.from(performanceMetrics.cacheHitRates.values())
        .reduce((sum, rate) => sum + rate.hits + rate.misses, 0)
      
      const hitRate = totalRequests > 0 ? totalHits / totalRequests : 0
      
      this.recordMetric('performance', 'cache_hit_rate', Date.now(), {
        value: hitRate,
        totalHits,
        totalRequests
      })
    }
  }

  /**
   * Collect business metrics
   */
  async collectBusinessMetrics() {
    // This would typically integrate with your analytics service
    const businessMetrics = {
      activeUsers: this.getActiveUsersCount(),
      agentExecutions: this.getAgentExecutionsCount(),
      apiCalls: this.getAPICallsCount(),
      conversions: this.getConversionsCount()
    }
    
    for (const [metric, value] of Object.entries(businessMetrics)) {
      this.recordMetric('business', metric, Date.now(), { value })
    }
  }

  /**
   * Collect system health metrics
   */
  async collectSystemHealthMetrics() {
    // Network connectivity check
    try {
      const start = Date.now()
      await fetch('/health', { method: 'HEAD' })
      const latency = Date.now() - start
      
      this.recordMetric('system_health', 'network_latency', Date.now(), {
        value: latency
      })
    } catch (error) {
      this.recordMetric('system_health', 'network_error', Date.now(), {
        error: error.message
      })
    }
  }

  /**
   * Collect user activity metrics
   */
  async collectUserActivityMetrics() {
    const userMetrics = {
      pageViews: this.getPageViewsCount(),
      sessionDuration: this.getAverageSessionDuration(),
      bounceRate: this.getBounceRate(),
      userRetention: this.getUserRetentionRate()
    }
    
    for (const [metric, value] of Object.entries(userMetrics)) {
      this.recordMetric('user_activity', metric, Date.now(), { value })
    }
  }

  /**
   * Collect agent performance metrics
   */
  async collectAgentPerformanceMetrics() {
    // This would integrate with your agent execution tracking
    const agentMetrics = {
      executionTime: this.getAverageAgentExecutionTime(),
      successRate: this.getAgentSuccessRate(),
      tokenUsage: this.getAverageTokenUsage(),
      concurrentExecutions: this.getConcurrentAgentExecutions()
    }
    
    for (const [metric, value] of Object.entries(agentMetrics)) {
      this.recordMetric('agent_performance', metric, Date.now(), { value })
    }
  }

  /**
   * Check alerts for all metrics
   */
  checkAlerts() {
    for (const [alertName, alert] of this.alerts.entries()) {
      const metricKey = alert.metric
      const threshold = this.thresholds.get(alert.metric)?.[alert.threshold]
      
      if (!threshold) continue
      
      const recentMetrics = this.getRecentMetrics(metricKey, 300000) // Last 5 minutes
      if (recentMetrics.length === 0) continue
      
      const latestValue = recentMetrics[recentMetrics.length - 1].value
      const shouldTrigger = this.evaluateAlertCondition(latestValue, alert.condition, threshold)
      
      if (shouldTrigger && !alert.isActive) {
        this.triggerAlert(alertName, alert, latestValue, threshold)
      } else if (!shouldTrigger && alert.isActive) {
        this.resolveAlert(alertName, alert)
      }
    }
  }

  /**
   * Check metric alerts
   */
  checkMetricAlerts(metricKey, value) {
    const thresholds = this.thresholds.get(metricKey.split('.')[1])
    if (!thresholds) return
    
    // Check warning threshold
    if (value > thresholds.warning) {
      this.recordMetric('alerts', 'threshold_warning', Date.now(), {
        metric: metricKey,
        value,
        threshold: thresholds.warning
      })
    }
    
    // Check critical threshold
    if (value > thresholds.critical) {
      this.recordMetric('alerts', 'threshold_critical', Date.now(), {
        metric: metricKey,
        value,
        threshold: thresholds.critical
      })
    }
  }

  /**
   * Trigger an alert
   */
  async triggerAlert(alertName, alert, value, threshold) {
    const now = Date.now()
    
    // Check cooldown
    if (alert.lastTriggered && (now - alert.lastTriggered) < alert.cooldown) {
      return
    }
    
    alert.isActive = true
    alert.lastTriggered = now
    
    const alertData = {
      name: alertName,
      metric: alert.metric,
      severity: alert.severity,
      value,
      threshold,
      timestamp: now
    }
    
    // Log alert
    await auditService.logSystem.alert('alert_triggered', alertData)
    
    // Send notification (implement based on your notification system)
    await this.sendAlertNotification(alertData)
    
    console.warn(`🚨 Alert triggered: ${alertName}`, alertData)
  }

  /**
   * Resolve an alert
   */
  async resolveAlert(alertName, alert) {
    alert.isActive = false
    
    const alertData = {
      name: alertName,
      metric: alert.metric,
      resolvedAt: Date.now()
    }
    
    // Log alert resolution
    await auditService.logSystem.alert('alert_resolved', alertData)
    
    console.log(`✅ Alert resolved: ${alertName}`, alertData)
  }

  /**
   * Send alert notification
   */
  async sendAlertNotification(alertData) {
    // Implement notification logic (email, Slack, etc.)
    // This is a placeholder for your notification system
    
    if (environmentConfig.monitoring.webhookUrl) {
      try {
        await fetch(environmentConfig.monitoring.webhookUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: `🚨 PIKAR AI Alert: ${alertData.name}`,
            attachments: [{
              color: alertData.severity === 'critical' ? 'danger' : 'warning',
              fields: [
                { title: 'Metric', value: alertData.metric, short: true },
                { title: 'Value', value: alertData.value.toString(), short: true },
                { title: 'Threshold', value: alertData.threshold.toString(), short: true },
                { title: 'Severity', value: alertData.severity, short: true }
              ]
            }]
          })
        })
      } catch (error) {
        console.error('Failed to send alert notification:', error)
      }
    }
  }

  /**
   * Evaluate alert condition
   */
  evaluateAlertCondition(value, condition, threshold) {
    switch (condition) {
      case 'greater_than':
        return value > threshold
      case 'less_than':
        return value < threshold
      case 'equals':
        return value === threshold
      case 'not_equals':
        return value !== threshold
      default:
        return false
    }
  }

  /**
   * Get recent metrics for a key
   */
  getRecentMetrics(metricKey, timeWindow) {
    const metrics = this.metrics.get(metricKey) || []
    const cutoff = Date.now() - timeWindow
    
    return metrics.filter(metric => metric.timestamp > cutoff)
  }

  /**
   * Get Web Vital rating
   */
  getWebVitalRating(name, value) {
    const thresholds = {
      'first-contentful-paint': { good: 1800, poor: 3000 },
      'largest-contentful-paint': { good: 2500, poor: 4000 },
      'first-input-delay': { good: 100, poor: 300 },
      'cumulative-layout-shift': { good: 0.1, poor: 0.25 }
    }
    
    const threshold = thresholds[name]
    if (!threshold) return 'unknown'
    
    if (value <= threshold.good) return 'good'
    if (value <= threshold.poor) return 'needs-improvement'
    return 'poor'
  }

  /**
   * Track user engagement
   */
  trackUserEngagement() {
    if (typeof window !== 'undefined') {
      // Track page visibility changes
      document.addEventListener('visibilitychange', () => {
        this.recordMetric('user_engagement', 'visibility_change', Date.now(), {
          hidden: document.hidden
        })
      })
      
      // Track user interactions
      ['click', 'scroll', 'keydown'].forEach(eventType => {
        document.addEventListener(eventType, () => {
          this.recordMetric('user_engagement', eventType, Date.now())
        }, { passive: true })
      })
    }
  }

  /**
   * Track conversion metrics
   */
  trackConversionMetrics() {
    // Implement conversion tracking based on your business logic
    // This is a placeholder
  }

  /**
   * Track feature usage
   */
  trackFeatureUsage() {
    // Implement feature usage tracking
    // This is a placeholder
  }

  /**
   * Get metrics data
   */
  getMetrics(category, timeWindow = 3600000) { // Default 1 hour
    const cutoff = Date.now() - timeWindow
    const result = {}
    
    for (const [key, metrics] of this.metrics.entries()) {
      if (category && !key.startsWith(category)) continue
      
      const recentMetrics = metrics.filter(m => m.timestamp > cutoff)
      if (recentMetrics.length > 0) {
        result[key] = recentMetrics
      }
    }
    
    return result
  }

  /**
   * Get alert status
   */
  getAlertStatus() {
    const activeAlerts = Array.from(this.alerts.entries())
      .filter(([_, alert]) => alert.isActive)
      .map(([name, alert]) => ({ name, ...alert }))
    
    return {
      total: this.alerts.size,
      active: activeAlerts.length,
      alerts: activeAlerts
    }
  }

  /**
   * Cleanup old metrics
   */
  cleanupOldMetrics() {
    const cutoff = Date.now() - this.config.retentionPeriod
    
    for (const [key, metrics] of this.metrics.entries()) {
      const filteredMetrics = metrics.filter(m => m.timestamp > cutoff)
      this.metrics.set(key, filteredMetrics)
    }
  }

  // Placeholder methods for business metrics (implement based on your data sources)
  getActiveUsersCount() { return Math.floor(Math.random() * 1000) }
  getAgentExecutionsCount() { return Math.floor(Math.random() * 100) }
  getAPICallsCount() { return Math.floor(Math.random() * 5000) }
  getConversionsCount() { return Math.floor(Math.random() * 50) }
  getPageViewsCount() { return Math.floor(Math.random() * 10000) }
  getAverageSessionDuration() { return Math.floor(Math.random() * 300000) }
  getBounceRate() { return Math.random() * 0.5 }
  getUserRetentionRate() { return Math.random() * 0.8 + 0.2 }
  getAverageAgentExecutionTime() { return Math.floor(Math.random() * 5000) }
  getAgentSuccessRate() { return Math.random() * 0.2 + 0.8 }
  getAverageTokenUsage() { return Math.floor(Math.random() * 1000) }
  getConcurrentAgentExecutions() { return Math.floor(Math.random() * 10) }
}

export const monitoringService = new MonitoringService()
