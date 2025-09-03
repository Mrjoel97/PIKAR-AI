/**
 * A/B Testing Service
 * Comprehensive A/B testing framework with statistical analysis and automated winner selection
 */

import { auditService } from './auditService'
import { loggingService } from './loggingService'
import { tierService } from './tierService'
import { environmentConfig } from '@/config/environment'

class ABTestingService {
  constructor() {
    this.tests = new Map()
    this.variants = new Map()
    this.assignments = new Map()
    this.results = new Map()
    this.isInitialized = false
    
    // Statistical configuration
    this.config = {
      defaultSignificanceLevel: 0.05, // 95% confidence
      defaultPower: 0.8, // 80% power
      defaultMinimumDetectableEffect: 0.05, // 5% minimum effect
      defaultTrafficAllocation: 0.5, // 50% traffic split
      minimumSampleSize: 100,
      maximumTestDuration: 30 * 24 * 60 * 60 * 1000, // 30 days
      checkInterval: 24 * 60 * 60 * 1000, // Daily checks
      autoWinnerThreshold: 0.95 // 95% probability to be best
    }
    
    // Test status types
    this.testStatus = {
      DRAFT: 'draft',
      RUNNING: 'running',
      PAUSED: 'paused',
      COMPLETED: 'completed',
      STOPPED: 'stopped'
    }
    
    // Metric types
    this.metricTypes = {
      CONVERSION_RATE: 'conversion_rate',
      CLICK_THROUGH_RATE: 'click_through_rate',
      REVENUE_PER_VISITOR: 'revenue_per_visitor',
      AVERAGE_ORDER_VALUE: 'average_order_value',
      ENGAGEMENT_RATE: 'engagement_rate',
      BOUNCE_RATE: 'bounce_rate',
      TIME_ON_PAGE: 'time_on_page',
      CUSTOM: 'custom'
    }
    
    this.setupStatisticalEngine()
  }

  /**
   * Initialize A/B testing service
   */
  async initialize() {
    try {
      console.log('🧪 Initializing A/B Testing Service...')
      
      // Load existing tests
      await this.loadTests()
      
      // Setup automated checks
      this.setupAutomatedChecks()
      
      // Initialize statistical engine
      this.initializeStatisticalEngine()
      
      this.isInitialized = true
      
      console.log('✅ A/B Testing Service initialized successfully')
      
      await auditService.logSystem.abTesting('ab_testing_service_initialized', {
        activeTests: this.getActiveTests().length,
        totalTests: this.tests.size
      })
      
    } catch (error) {
      console.error('❌ A/B Testing Service initialization failed:', error)
      throw error
    }
  }

  /**
   * Create new A/B test
   */
  async createTest(userId, testConfig) {
    try {
      // Check tier access
      if (!tierService.hasFeatureAccess(userId, 'abTesting')) {
        throw new Error('A/B testing requires Pro or Enterprise tier')
      }
      
      // Validate test configuration
      this.validateTestConfig(testConfig)
      
      const testId = this.generateTestId()
      const test = {
        id: testId,
        userId,
        name: testConfig.name,
        description: testConfig.description,
        hypothesis: testConfig.hypothesis,
        status: this.testStatus.DRAFT,
        
        // Test configuration
        trafficAllocation: testConfig.trafficAllocation || this.config.defaultTrafficAllocation,
        significanceLevel: testConfig.significanceLevel || this.config.defaultSignificanceLevel,
        power: testConfig.power || this.config.defaultPower,
        minimumDetectableEffect: testConfig.minimumDetectableEffect || this.config.defaultMinimumDetectableEffect,
        
        // Timing
        startDate: testConfig.startDate,
        endDate: testConfig.endDate,
        maxDuration: testConfig.maxDuration || this.config.maximumTestDuration,
        
        // Metrics
        primaryMetric: testConfig.primaryMetric,
        secondaryMetrics: testConfig.secondaryMetrics || [],
        
        // Variants
        variants: testConfig.variants.map((variant, index) => ({
          id: this.generateVariantId(),
          name: variant.name,
          description: variant.description,
          isControl: index === 0,
          trafficWeight: variant.trafficWeight || (1 / testConfig.variants.length),
          configuration: variant.configuration
        })),
        
        // Targeting
        targetingRules: testConfig.targetingRules || {},
        
        // Metadata
        createdAt: Date.now(),
        updatedAt: Date.now(),
        createdBy: userId
      }
      
      // Calculate required sample size
      test.requiredSampleSize = this.calculateSampleSize(
        test.significanceLevel,
        test.power,
        test.minimumDetectableEffect
      )
      
      this.tests.set(testId, test)
      
      // Store variants
      test.variants.forEach(variant => {
        this.variants.set(variant.id, { ...variant, testId })
      })
      
      await auditService.logAccess.abTesting('ab_test_created', {
        userId,
        testId,
        testName: test.name,
        variantCount: test.variants.length
      })
      
      return test
      
    } catch (error) {
      console.error('Failed to create A/B test:', error)
      throw error
    }
  }

  /**
   * Start A/B test
   */
  async startTest(userId, testId) {
    const test = this.tests.get(testId)
    if (!test) {
      throw new Error('Test not found')
    }
    
    if (test.userId !== userId) {
      throw new Error('Unauthorized to start this test')
    }
    
    if (test.status !== this.testStatus.DRAFT) {
      throw new Error('Test can only be started from draft status')
    }
    
    // Validate test is ready to start
    this.validateTestReadiness(test)
    
    test.status = this.testStatus.RUNNING
    test.actualStartDate = Date.now()
    test.updatedAt = Date.now()
    
    // Initialize results tracking
    this.initializeTestResults(testId)
    
    await auditService.logAccess.abTesting('ab_test_started', {
      userId,
      testId,
      testName: test.name
    })
    
    return test
  }

  /**
   * Stop A/B test
   */
  async stopTest(userId, testId, reason = 'manual') {
    const test = this.tests.get(testId)
    if (!test) {
      throw new Error('Test not found')
    }
    
    if (test.userId !== userId) {
      throw new Error('Unauthorized to stop this test')
    }
    
    if (test.status !== this.testStatus.RUNNING) {
      throw new Error('Test is not currently running')
    }
    
    test.status = this.testStatus.STOPPED
    test.actualEndDate = Date.now()
    test.stopReason = reason
    test.updatedAt = Date.now()
    
    // Calculate final results
    const finalResults = await this.calculateTestResults(testId)
    test.finalResults = finalResults
    
    await auditService.logAccess.abTesting('ab_test_stopped', {
      userId,
      testId,
      testName: test.name,
      reason,
      duration: test.actualEndDate - test.actualStartDate
    })
    
    return test
  }

  /**
   * Assign user to test variant
   */
  assignUserToVariant(userId, testId) {
    const test = this.tests.get(testId)
    if (!test || test.status !== this.testStatus.RUNNING) {
      return null
    }
    
    // Check if user already assigned
    const existingAssignment = this.assignments.get(`${userId}:${testId}`)
    if (existingAssignment) {
      return existingAssignment
    }
    
    // Check targeting rules
    if (!this.matchesTargetingRules(userId, test.targetingRules)) {
      return null
    }
    
    // Assign to variant based on traffic allocation
    const variant = this.selectVariantForUser(userId, test)
    if (!variant) {
      return null
    }
    
    const assignment = {
      userId,
      testId,
      variantId: variant.id,
      assignedAt: Date.now(),
      exposureCount: 0
    }
    
    this.assignments.set(`${userId}:${testId}`, assignment)
    
    // Track exposure
    this.trackExposure(userId, testId, variant.id)
    
    return assignment
  }

  /**
   * Track conversion event
   */
  async trackConversion(userId, testId, metricType, value = 1, metadata = {}) {
    const assignment = this.assignments.get(`${userId}:${testId}`)
    if (!assignment) {
      return // User not in test
    }
    
    const test = this.tests.get(testId)
    if (!test || test.status !== this.testStatus.RUNNING) {
      return
    }
    
    const conversionEvent = {
      userId,
      testId,
      variantId: assignment.variantId,
      metricType,
      value,
      metadata,
      timestamp: Date.now()
    }
    
    // Store conversion
    const resultKey = `${testId}:${assignment.variantId}:${metricType}`
    if (!this.results.has(resultKey)) {
      this.results.set(resultKey, {
        testId,
        variantId: assignment.variantId,
        metricType,
        conversions: [],
        totalValue: 0,
        uniqueUsers: new Set()
      })
    }
    
    const result = this.results.get(resultKey)
    result.conversions.push(conversionEvent)
    result.totalValue += value
    result.uniqueUsers.add(userId)
    
    await auditService.logAccess.abTesting('ab_test_conversion', {
      userId,
      testId,
      variantId: assignment.variantId,
      metricType,
      value
    })
  }

  /**
   * Calculate test results with statistical significance
   */
  async calculateTestResults(testId) {
    const test = this.tests.get(testId)
    if (!test) {
      throw new Error('Test not found')
    }
    
    const results = {
      testId,
      calculatedAt: Date.now(),
      variants: {},
      comparisons: {},
      winner: null,
      confidence: 0,
      isSignificant: false,
      recommendedAction: 'continue'
    }
    
    // Calculate metrics for each variant
    for (const variant of test.variants) {
      const variantResults = this.calculateVariantResults(testId, variant.id, test.primaryMetric)
      results.variants[variant.id] = {
        ...variant,
        ...variantResults,
        sampleSize: this.getVariantSampleSize(testId, variant.id)
      }
    }
    
    // Perform statistical comparisons
    const controlVariant = test.variants.find(v => v.isControl)
    if (controlVariant) {
      for (const variant of test.variants) {
        if (!variant.isControl) {
          const comparison = this.performStatisticalTest(
            results.variants[controlVariant.id],
            results.variants[variant.id],
            test.primaryMetric
          )
          
          results.comparisons[variant.id] = comparison
          
          // Check for significance
          if (comparison.pValue < test.significanceLevel) {
            results.isSignificant = true
            if (comparison.lift > 0 && comparison.confidence > results.confidence) {
              results.winner = variant.id
              results.confidence = comparison.confidence
            }
          }
        }
      }
    }
    
    // Determine recommended action
    results.recommendedAction = this.determineRecommendedAction(test, results)
    
    return results
  }

  /**
   * Perform statistical test (t-test for continuous, chi-square for categorical)
   */
  performStatisticalTest(controlData, variantData, metricType) {
    const controlMean = controlData.mean || 0
    const variantMean = variantData.mean || 0
    const controlStdDev = controlData.standardDeviation || 0
    const variantStdDev = variantData.standardDeviation || 0
    const controlSize = controlData.sampleSize || 0
    const variantSize = variantData.sampleSize || 0
    
    if (controlSize === 0 || variantSize === 0) {
      return {
        pValue: 1,
        confidence: 0,
        lift: 0,
        liftLowerBound: 0,
        liftUpperBound: 0,
        isSignificant: false
      }
    }
    
    // Calculate lift
    const lift = controlMean > 0 ? (variantMean - controlMean) / controlMean : 0
    
    // Perform t-test
    const pooledStdError = Math.sqrt(
      (controlStdDev * controlStdDev) / controlSize +
      (variantStdDev * variantStdDev) / variantSize
    )
    
    const tStatistic = pooledStdError > 0 ? (variantMean - controlMean) / pooledStdError : 0
    const degreesOfFreedom = controlSize + variantSize - 2
    
    // Calculate p-value (simplified - would use proper t-distribution in production)
    const pValue = this.calculatePValue(tStatistic, degreesOfFreedom)
    
    // Calculate confidence interval
    const marginOfError = this.calculateMarginOfError(pooledStdError, degreesOfFreedom, 0.05)
    const liftLowerBound = lift - marginOfError
    const liftUpperBound = lift + marginOfError
    
    return {
      pValue,
      confidence: 1 - pValue,
      lift,
      liftLowerBound,
      liftUpperBound,
      isSignificant: pValue < 0.05,
      tStatistic,
      degreesOfFreedom
    }
  }

  /**
   * Calculate required sample size
   */
  calculateSampleSize(alpha, power, effect) {
    // Simplified sample size calculation
    // In production, would use proper statistical formulas
    const zAlpha = this.getZScore(alpha / 2)
    const zBeta = this.getZScore(1 - power)
    
    const sampleSize = Math.ceil(
      (2 * Math.pow(zAlpha + zBeta, 2)) / Math.pow(effect, 2)
    )
    
    return Math.max(sampleSize, this.config.minimumSampleSize)
  }

  /**
   * Select variant for user based on traffic allocation
   */
  selectVariantForUser(userId, test) {
    // Use consistent hashing to ensure same user always gets same variant
    const hash = this.hashUserId(userId, test.id)
    const hashValue = hash % 100 / 100 // Convert to 0-1 range
    
    // Check if user should be included in test
    if (hashValue > test.trafficAllocation) {
      return null
    }
    
    // Select variant based on traffic weights
    let cumulativeWeight = 0
    const adjustedHashValue = (hashValue / test.trafficAllocation) // Normalize to allocated traffic
    
    for (const variant of test.variants) {
      cumulativeWeight += variant.trafficWeight
      if (adjustedHashValue <= cumulativeWeight) {
        return variant
      }
    }
    
    // Fallback to control
    return test.variants.find(v => v.isControl) || test.variants[0]
  }

  /**
   * Setup automated checks for running tests
   */
  setupAutomatedChecks() {
    setInterval(async () => {
      await this.performAutomatedChecks()
    }, this.config.checkInterval)
  }

  /**
   * Perform automated checks on running tests
   */
  async performAutomatedChecks() {
    const runningTests = this.getActiveTests()
    
    for (const test of runningTests) {
      try {
        // Check if test should be automatically stopped
        const shouldStop = await this.shouldAutoStopTest(test)
        if (shouldStop.stop) {
          await this.stopTest(test.userId, test.id, shouldStop.reason)
          continue
        }
        
        // Check for statistical significance
        const results = await this.calculateTestResults(test.id)
        
        // Auto-declare winner if confidence is high enough
        if (results.isSignificant && results.confidence >= this.config.autoWinnerThreshold) {
          await this.declareWinner(test.id, results.winner, 'automatic')
        }
        
      } catch (error) {
        console.error(`Error in automated check for test ${test.id}:`, error)
      }
    }
  }

  /**
   * Declare test winner
   */
  async declareWinner(testId, winnerVariantId, method = 'manual') {
    const test = this.tests.get(testId)
    if (!test) {
      throw new Error('Test not found')
    }
    
    test.status = this.testStatus.COMPLETED
    test.actualEndDate = Date.now()
    test.winner = winnerVariantId
    test.winnerDeclaredBy = method
    test.updatedAt = Date.now()
    
    const finalResults = await this.calculateTestResults(testId)
    test.finalResults = finalResults
    
    await auditService.logAccess.abTesting('ab_test_winner_declared', {
      testId,
      winnerVariantId,
      method,
      confidence: finalResults.confidence
    })
    
    return test
  }

  // Utility methods
  generateTestId() {
    return `test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  generateVariantId() {
    return `variant_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  hashUserId(userId, testId) {
    // Simple hash function - would use proper hash in production
    let hash = 0
    const str = `${userId}:${testId}`
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash // Convert to 32-bit integer
    }
    return Math.abs(hash)
  }

  getActiveTests() {
    return Array.from(this.tests.values()).filter(test => test.status === this.testStatus.RUNNING)
  }

  validateTestConfig(config) {
    if (!config.name) throw new Error('Test name is required')
    if (!config.variants || config.variants.length < 2) throw new Error('At least 2 variants required')
    if (!config.primaryMetric) throw new Error('Primary metric is required')
  }

  validateTestReadiness(test) {
    if (!test.variants || test.variants.length < 2) {
      throw new Error('Test must have at least 2 variants')
    }
    if (!test.primaryMetric) {
      throw new Error('Primary metric must be defined')
    }
  }

  initializeTestResults(testId) {
    const test = this.tests.get(testId)
    for (const variant of test.variants) {
      const resultKey = `${testId}:${variant.id}:${test.primaryMetric}`
      this.results.set(resultKey, {
        testId,
        variantId: variant.id,
        metricType: test.primaryMetric,
        conversions: [],
        totalValue: 0,
        uniqueUsers: new Set()
      })
    }
  }

  // Placeholder methods for statistical calculations
  calculatePValue(tStatistic, degreesOfFreedom) {
    // Simplified p-value calculation
    return Math.max(0.001, Math.min(0.999, 1 / (1 + Math.abs(tStatistic))))
  }

  calculateMarginOfError(standardError, degreesOfFreedom, alpha) {
    const tCritical = this.getTCritical(degreesOfFreedom, alpha)
    return tCritical * standardError
  }

  getTCritical(degreesOfFreedom, alpha) {
    // Simplified t-critical value
    return 1.96 // Approximation for large samples
  }

  getZScore(probability) {
    // Simplified z-score calculation
    if (probability <= 0.5) return -1.96
    return 1.96
  }

  // Placeholder methods for database operations
  async loadTests() {
    console.log('Loading A/B tests from database...')
  }

  calculateVariantResults(testId, variantId, metricType) {
    const resultKey = `${testId}:${variantId}:${metricType}`
    const result = this.results.get(resultKey)
    
    if (!result) {
      return { mean: 0, standardDeviation: 0, sampleSize: 0 }
    }
    
    const values = result.conversions.map(c => c.value)
    const mean = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0
    const variance = values.length > 1 ? 
      values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / (values.length - 1) : 0
    const standardDeviation = Math.sqrt(variance)
    
    return {
      mean,
      standardDeviation,
      sampleSize: result.uniqueUsers.size,
      totalConversions: result.conversions.length,
      totalValue: result.totalValue
    }
  }

  getVariantSampleSize(testId, variantId) {
    return Array.from(this.assignments.values())
      .filter(a => a.testId === testId && a.variantId === variantId).length
  }

  matchesTargetingRules(userId, rules) {
    // Simplified targeting - would implement complex rules in production
    return true
  }

  trackExposure(userId, testId, variantId) {
    const assignment = this.assignments.get(`${userId}:${testId}`)
    if (assignment) {
      assignment.exposureCount++
      assignment.lastExposure = Date.now()
    }
  }

  async shouldAutoStopTest(test) {
    // Check maximum duration
    if (Date.now() - test.actualStartDate > test.maxDuration) {
      return { stop: true, reason: 'max_duration_reached' }
    }
    
    // Check if sample size is sufficient and results are conclusive
    const results = await this.calculateTestResults(test.id)
    const hasMinimumSample = Object.values(results.variants)
      .every(v => v.sampleSize >= test.requiredSampleSize)
    
    if (hasMinimumSample && results.isSignificant && results.confidence >= 0.99) {
      return { stop: true, reason: 'conclusive_results' }
    }
    
    return { stop: false }
  }

  determineRecommendedAction(test, results) {
    if (!results.isSignificant) {
      return 'continue'
    }
    
    if (results.winner && results.confidence >= 0.95) {
      return 'declare_winner'
    }
    
    if (results.confidence >= 0.8) {
      return 'monitor_closely'
    }
    
    return 'continue'
  }

  setupStatisticalEngine() {
    // Initialize statistical computation engine
    console.log('Statistical engine initialized')
  }

  initializeStatisticalEngine() {
    // Setup statistical computation libraries
    console.log('Statistical engine ready')
  }
}

export const abTestingService = new ABTestingService()
