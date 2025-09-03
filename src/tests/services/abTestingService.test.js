/**
 * A/B Testing Service Tests
 * Comprehensive unit tests for A/B testing functionality
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest'
import { abTestingService } from '@/services/abTestingService'
import { auditService } from '@/services/auditService'
import { tierService } from '@/services/tierService'

// Mock dependencies
vi.mock('@/services/auditService', () => ({
  auditService: {
    logSystem: {
      abTesting: vi.fn()
    },
    logAccess: {
      abTesting: vi.fn()
    }
  }
}))

vi.mock('@/services/tierService', () => ({
  tierService: {
    hasFeatureAccess: vi.fn().mockReturnValue(true)
  }
}))

describe('ABTestingService', () => {
  beforeEach(async () => {
    // Reset service state
    abTestingService.tests = new Map()
    abTestingService.variants = new Map()
    abTestingService.assignments = new Map()
    abTestingService.results = new Map()
    abTestingService.isInitialized = false
    
    // Initialize service
    await abTestingService.initialize()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initialization', () => {
    test('should initialize successfully', async () => {
      expect(abTestingService.isInitialized).toBe(true)
      expect(auditService.logSystem.abTesting).toHaveBeenCalledWith(
        'ab_testing_service_initialized',
        expect.any(Object)
      )
    })

    test('should have correct configuration', () => {
      expect(abTestingService.config.defaultSignificanceLevel).toBe(0.05)
      expect(abTestingService.config.defaultPower).toBe(0.8)
      expect(abTestingService.config.minimumSampleSize).toBe(100)
    })
  })

  describe('Test Creation', () => {
    const userId = 'test-user-123'
    const testConfig = {
      name: 'Button Color Test',
      description: 'Testing different button colors',
      hypothesis: 'Blue button will increase conversions',
      primaryMetric: 'conversion_rate',
      variants: [
        {
          name: 'Control (Green)',
          description: 'Current green button',
          configuration: { buttonColor: 'green' }
        },
        {
          name: 'Variant (Blue)',
          description: 'New blue button',
          configuration: { buttonColor: 'blue' }
        }
      ]
    }

    test('should create test successfully', async () => {
      const test = await abTestingService.createTest(userId, testConfig)
      
      expect(test.id).toBeTruthy()
      expect(test.name).toBe(testConfig.name)
      expect(test.status).toBe('draft')
      expect(test.variants).toHaveLength(2)
      expect(test.variants[0].isControl).toBe(true)
      expect(test.requiredSampleSize).toBeGreaterThan(0)
      
      expect(auditService.logAccess.abTesting).toHaveBeenCalledWith(
        'ab_test_created',
        expect.objectContaining({
          userId,
          testName: testConfig.name
        })
      )
    })

    test('should validate test configuration', async () => {
      const invalidConfig = { ...testConfig, name: '' }
      
      await expect(
        abTestingService.createTest(userId, invalidConfig)
      ).rejects.toThrow('Test name is required')
    })

    test('should require minimum variants', async () => {
      const invalidConfig = { ...testConfig, variants: [testConfig.variants[0]] }
      
      await expect(
        abTestingService.createTest(userId, invalidConfig)
      ).rejects.toThrow('At least 2 variants required')
    })

    test('should check tier access', async () => {
      tierService.hasFeatureAccess.mockReturnValue(false)
      
      await expect(
        abTestingService.createTest(userId, testConfig)
      ).rejects.toThrow('A/B testing requires Pro or Enterprise tier')
    })

    test('should calculate sample size correctly', () => {
      const sampleSize = abTestingService.calculateSampleSize(0.05, 0.8, 0.05)
      
      expect(sampleSize).toBeGreaterThan(100)
      expect(typeof sampleSize).toBe('number')
    })
  })

  describe('Test Lifecycle Management', () => {
    let testId
    const userId = 'test-user-123'

    beforeEach(async () => {
      const testConfig = {
        name: 'Test Lifecycle',
        description: 'Testing lifecycle management',
        hypothesis: 'Test hypothesis',
        primaryMetric: 'conversion_rate',
        variants: [
          { name: 'Control', configuration: { version: 'A' } },
          { name: 'Variant', configuration: { version: 'B' } }
        ]
      }
      
      const test = await abTestingService.createTest(userId, testConfig)
      testId = test.id
    })

    test('should start test successfully', async () => {
      const test = await abTestingService.startTest(userId, testId)
      
      expect(test.status).toBe('running')
      expect(test.actualStartDate).toBeTruthy()
      
      expect(auditService.logAccess.abTesting).toHaveBeenCalledWith(
        'ab_test_started',
        expect.objectContaining({ userId, testId })
      )
    })

    test('should prevent starting non-draft test', async () => {
      await abTestingService.startTest(userId, testId)
      
      await expect(
        abTestingService.startTest(userId, testId)
      ).rejects.toThrow('Test can only be started from draft status')
    })

    test('should stop test successfully', async () => {
      await abTestingService.startTest(userId, testId)
      
      const test = await abTestingService.stopTest(userId, testId, 'manual')
      
      expect(test.status).toBe('stopped')
      expect(test.actualEndDate).toBeTruthy()
      expect(test.stopReason).toBe('manual')
      expect(test.finalResults).toBeTruthy()
    })

    test('should prevent unauthorized operations', async () => {
      const otherUserId = 'other-user-456'
      
      await expect(
        abTestingService.startTest(otherUserId, testId)
      ).rejects.toThrow('Unauthorized to start this test')
    })
  })

  describe('User Assignment and Tracking', () => {
    let testId
    const userId = 'test-user-123'

    beforeEach(async () => {
      const testConfig = {
        name: 'Assignment Test',
        description: 'Testing user assignment',
        hypothesis: 'Test hypothesis',
        primaryMetric: 'conversion_rate',
        variants: [
          { name: 'Control', configuration: { version: 'A' } },
          { name: 'Variant', configuration: { version: 'B' } }
        ]
      }
      
      const test = await abTestingService.createTest(userId, testConfig)
      testId = test.id
      await abTestingService.startTest(userId, testId)
    })

    test('should assign user to variant', () => {
      const assignment = abTestingService.assignUserToVariant('visitor-123', testId)
      
      expect(assignment).toBeTruthy()
      expect(assignment.userId).toBe('visitor-123')
      expect(assignment.testId).toBe(testId)
      expect(assignment.variantId).toBeTruthy()
      expect(assignment.assignedAt).toBeTruthy()
    })

    test('should return consistent assignment for same user', () => {
      const assignment1 = abTestingService.assignUserToVariant('visitor-123', testId)
      const assignment2 = abTestingService.assignUserToVariant('visitor-123', testId)
      
      expect(assignment1.variantId).toBe(assignment2.variantId)
    })

    test('should not assign to non-running test', () => {
      abTestingService.stopTest(userId, testId)
      
      const assignment = abTestingService.assignUserToVariant('visitor-123', testId)
      
      expect(assignment).toBeNull()
    })

    test('should track conversions', async () => {
      const visitorId = 'visitor-123'
      abTestingService.assignUserToVariant(visitorId, testId)
      
      await abTestingService.trackConversion(visitorId, testId, 'conversion_rate', 1)
      
      expect(auditService.logAccess.abTesting).toHaveBeenCalledWith(
        'ab_test_conversion',
        expect.objectContaining({
          userId: visitorId,
          testId,
          metricType: 'conversion_rate'
        })
      )
    })

    test('should not track conversions for unassigned users', async () => {
      const visitorId = 'unassigned-visitor'
      
      await abTestingService.trackConversion(visitorId, testId, 'conversion_rate', 1)
      
      // Should not throw, but also should not track
      expect(auditService.logAccess.abTesting).not.toHaveBeenCalledWith(
        'ab_test_conversion',
        expect.any(Object)
      )
    })
  })

  describe('Statistical Analysis', () => {
    let testId
    const userId = 'test-user-123'

    beforeEach(async () => {
      const testConfig = {
        name: 'Statistical Test',
        description: 'Testing statistical analysis',
        hypothesis: 'Test hypothesis',
        primaryMetric: 'conversion_rate',
        variants: [
          { name: 'Control', configuration: { version: 'A' } },
          { name: 'Variant', configuration: { version: 'B' } }
        ]
      }
      
      const test = await abTestingService.createTest(userId, testConfig)
      testId = test.id
      await abTestingService.startTest(userId, testId)
      
      // Add some mock data
      const test_obj = abTestingService.tests.get(testId)
      const controlVariant = test_obj.variants[0]
      const variantVariant = test_obj.variants[1]
      
      // Mock results
      abTestingService.results.set(`${testId}:${controlVariant.id}:conversion_rate`, {
        testId,
        variantId: controlVariant.id,
        metricType: 'conversion_rate',
        conversions: Array.from({ length: 100 }, (_, i) => ({ value: 1, userId: `user${i}` })),
        totalValue: 100,
        uniqueUsers: new Set(Array.from({ length: 100 }, (_, i) => `user${i}`))
      })
      
      abTestingService.results.set(`${testId}:${variantVariant.id}:conversion_rate`, {
        testId,
        variantId: variantVariant.id,
        metricType: 'conversion_rate',
        conversions: Array.from({ length: 120 }, (_, i) => ({ value: 1, userId: `user${i + 100}` })),
        totalValue: 120,
        uniqueUsers: new Set(Array.from({ length: 120 }, (_, i) => `user${i + 100}`))
      })
    })

    test('should calculate test results', async () => {
      const results = await abTestingService.calculateTestResults(testId)
      
      expect(results.testId).toBe(testId)
      expect(results.variants).toBeTruthy()
      expect(results.comparisons).toBeTruthy()
      expect(results.calculatedAt).toBeTruthy()
    })

    test('should perform statistical test', () => {
      const controlData = { mean: 0.1, standardDeviation: 0.3, sampleSize: 1000 }
      const variantData = { mean: 0.12, standardDeviation: 0.32, sampleSize: 1000 }
      
      const comparison = abTestingService.performStatisticalTest(
        controlData,
        variantData,
        'conversion_rate'
      )
      
      expect(comparison.lift).toBeCloseTo(0.2, 1)
      expect(comparison.pValue).toBeGreaterThan(0)
      expect(comparison.pValue).toBeLessThan(1)
      expect(comparison.confidence).toBe(1 - comparison.pValue)
    })

    test('should handle zero sample sizes', () => {
      const controlData = { mean: 0, standardDeviation: 0, sampleSize: 0 }
      const variantData = { mean: 0, standardDeviation: 0, sampleSize: 0 }
      
      const comparison = abTestingService.performStatisticalTest(
        controlData,
        variantData,
        'conversion_rate'
      )
      
      expect(comparison.pValue).toBe(1)
      expect(comparison.confidence).toBe(0)
      expect(comparison.lift).toBe(0)
    })

    test('should determine recommended action', async () => {
      const test = abTestingService.tests.get(testId)
      const results = await abTestingService.calculateTestResults(testId)
      
      const action = abTestingService.determineRecommendedAction(test, results)
      
      expect(['continue', 'declare_winner', 'monitor_closely']).toContain(action)
    })
  })

  describe('Automated Checks and Winner Declaration', () => {
    let testId
    const userId = 'test-user-123'

    beforeEach(async () => {
      const testConfig = {
        name: 'Auto Winner Test',
        description: 'Testing automated winner declaration',
        hypothesis: 'Test hypothesis',
        primaryMetric: 'conversion_rate',
        variants: [
          { name: 'Control', configuration: { version: 'A' } },
          { name: 'Variant', configuration: { version: 'B' } }
        ]
      }
      
      const test = await abTestingService.createTest(userId, testConfig)
      testId = test.id
      await abTestingService.startTest(userId, testId)
    })

    test('should declare winner manually', async () => {
      const test_obj = abTestingService.tests.get(testId)
      const winnerVariantId = test_obj.variants[1].id
      
      const test = await abTestingService.declareWinner(testId, winnerVariantId, 'manual')
      
      expect(test.status).toBe('completed')
      expect(test.winner).toBe(winnerVariantId)
      expect(test.winnerDeclaredBy).toBe('manual')
      expect(test.actualEndDate).toBeTruthy()
      
      expect(auditService.logAccess.abTesting).toHaveBeenCalledWith(
        'ab_test_winner_declared',
        expect.objectContaining({
          testId,
          winnerVariantId,
          method: 'manual'
        })
      )
    })

    test('should check if test should auto-stop', async () => {
      const test = abTestingService.tests.get(testId)
      
      // Set test to have started long ago
      test.actualStartDate = Date.now() - (35 * 24 * 60 * 60 * 1000) // 35 days ago
      
      const shouldStop = await abTestingService.shouldAutoStopTest(test)
      
      expect(shouldStop.stop).toBe(true)
      expect(shouldStop.reason).toBe('max_duration_reached')
    })

    test('should get active tests', () => {
      const activeTests = abTestingService.getActiveTests()
      
      expect(activeTests).toHaveLength(1)
      expect(activeTests[0].id).toBe(testId)
      expect(activeTests[0].status).toBe('running')
    })
  })

  describe('Variant Selection and Traffic Allocation', () => {
    let testId
    const userId = 'test-user-123'

    beforeEach(async () => {
      const testConfig = {
        name: 'Traffic Allocation Test',
        description: 'Testing traffic allocation',
        hypothesis: 'Test hypothesis',
        primaryMetric: 'conversion_rate',
        trafficAllocation: 0.5, // 50% of users
        variants: [
          { name: 'Control', configuration: { version: 'A' }, trafficWeight: 0.5 },
          { name: 'Variant', configuration: { version: 'B' }, trafficWeight: 0.5 }
        ]
      }
      
      const test = await abTestingService.createTest(userId, testConfig)
      testId = test.id
      await abTestingService.startTest(userId, testId)
    })

    test('should select variant based on consistent hashing', () => {
      const test = abTestingService.tests.get(testId)
      
      const variant1 = abTestingService.selectVariantForUser('user123', test)
      const variant2 = abTestingService.selectVariantForUser('user123', test)
      
      expect(variant1).toBeTruthy()
      expect(variant1.id).toBe(variant2.id) // Should be consistent
    })

    test('should respect traffic allocation', () => {
      const test = abTestingService.tests.get(testId)
      test.trafficAllocation = 0.1 // Only 10% of users
      
      let includedCount = 0
      const totalUsers = 1000
      
      for (let i = 0; i < totalUsers; i++) {
        const variant = abTestingService.selectVariantForUser(`user${i}`, test)
        if (variant) includedCount++
      }
      
      // Should be approximately 10% (with some variance due to hashing)
      expect(includedCount).toBeGreaterThan(50) // At least 5%
      expect(includedCount).toBeLessThan(200) // At most 20%
    })

    test('should hash user ID consistently', () => {
      const hash1 = abTestingService.hashUserId('user123', testId)
      const hash2 = abTestingService.hashUserId('user123', testId)
      
      expect(hash1).toBe(hash2)
      expect(typeof hash1).toBe('number')
    })
  })

  describe('Error Handling and Edge Cases', () => {
    test('should handle non-existent test gracefully', () => {
      const assignment = abTestingService.assignUserToVariant('user123', 'non-existent-test')
      expect(assignment).toBeNull()
    })

    test('should handle invalid test operations', async () => {
      await expect(
        abTestingService.startTest('user123', 'non-existent-test')
      ).rejects.toThrow('Test not found')
    })

    test('should validate test readiness', () => {
      const invalidTest = {
        variants: [{ name: 'Only One Variant' }],
        primaryMetric: null
      }
      
      expect(() => {
        abTestingService.validateTestReadiness(invalidTest)
      }).toThrow()
    })

    test('should handle missing targeting rules', () => {
      const matches = abTestingService.matchesTargetingRules('user123', {})
      expect(matches).toBe(true) // Should default to true
    })

    test('should generate unique IDs', () => {
      const id1 = abTestingService.generateTestId()
      const id2 = abTestingService.generateTestId()
      
      expect(id1).not.toBe(id2)
      expect(id1).toMatch(/^test_/)
      expect(id2).toMatch(/^test_/)
    })
  })

  describe('Integration Points', () => {
    test('should integrate with tier service', async () => {
      tierService.hasFeatureAccess.mockReturnValue(false)
      
      const testConfig = {
        name: 'Integration Test',
        description: 'Testing integration',
        hypothesis: 'Test hypothesis',
        primaryMetric: 'conversion_rate',
        variants: [
          { name: 'Control', configuration: { version: 'A' } },
          { name: 'Variant', configuration: { version: 'B' } }
        ]
      }
      
      await expect(
        abTestingService.createTest('user123', testConfig)
      ).rejects.toThrow('A/B testing requires Pro or Enterprise tier')
      
      expect(tierService.hasFeatureAccess).toHaveBeenCalledWith('user123', 'abTesting')
    })

    test('should integrate with audit service', async () => {
      const testConfig = {
        name: 'Audit Integration Test',
        description: 'Testing audit integration',
        hypothesis: 'Test hypothesis',
        primaryMetric: 'conversion_rate',
        variants: [
          { name: 'Control', configuration: { version: 'A' } },
          { name: 'Variant', configuration: { version: 'B' } }
        ]
      }
      
      await abTestingService.createTest('user123', testConfig)
      
      expect(auditService.logAccess.abTesting).toHaveBeenCalledWith(
        'ab_test_created',
        expect.any(Object)
      )
    })
  })
})
