/**
 * Tier Service Tests
 * Comprehensive unit tests for tier management functionality
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest'
import { tierService } from '@/services/tierService'
import { auditService } from '@/services/auditService'

// Mock dependencies
vi.mock('@/services/auditService', () => ({
  auditService: {
    logSystem: {
      tier: vi.fn()
    },
    logAccess: {
      tierChange: vi.fn(),
      tierUpgrade: vi.fn(),
      tierDowngrade: vi.fn(),
      quotaExceeded: vi.fn(),
      usageTracking: vi.fn()
    }
  }
}))

describe('TierService', () => {
  beforeEach(async () => {
    // Reset service state
    tierService.users = new Map()
    tierService.usageTracking = new Map()
    tierService.isInitialized = false
    
    // Initialize service
    await tierService.initialize()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initialization', () => {
    test('should initialize successfully', async () => {
      expect(tierService.isInitialized).toBe(true)
      expect(tierService.tiers.size).toBeGreaterThan(0)
      expect(auditService.logSystem.tier).toHaveBeenCalledWith(
        'tier_service_initialized',
        expect.any(Object)
      )
    })

    test('should have all tier definitions', () => {
      expect(tierService.tiers.has('FREE')).toBe(true)
      expect(tierService.tiers.has('PRO')).toBe(true)
      expect(tierService.tiers.has('ENTERPRISE')).toBe(true)
    })
  })

  describe('User Tier Management', () => {
    const userId = 'test-user-123'

    test('should return FREE tier for new user', () => {
      const tier = tierService.getUserTier(userId)
      expect(tier.id).toBe('free')
      expect(tier.name).toBe('Free')
      expect(tier.price).toBe(0)
    })

    test('should set user tier successfully', async () => {
      const billingInfo = {
        paymentMethod: 'stripe',
        subscriptionId: 'sub_123'
      }

      const result = await tierService.setUserTier(userId, 'PRO', billingInfo)
      
      expect(result.tierId).toBe('PRO')
      expect(result.billingInfo).toEqual(billingInfo)
      expect(result.status).toBe('active')
      
      expect(auditService.logAccess.tierChange).toHaveBeenCalledWith(
        'user_tier_changed',
        expect.objectContaining({
          userId,
          newTier: 'PRO'
        })
      )
    })

    test('should throw error for invalid tier', async () => {
      await expect(
        tierService.setUserTier(userId, 'INVALID_TIER')
      ).rejects.toThrow('Invalid tier ID: INVALID_TIER')
    })

    test('should reset usage when tier changes', async () => {
      // Set some usage
      tierService.usageTracking.set(userId, {
        monthlyExecutions: 50,
        dailyExecutions: 5
      })

      await tierService.setUserTier(userId, 'PRO')
      
      const usage = tierService.getUserUsage(userId)
      expect(usage.monthlyExecutions).toBe(0)
      expect(usage.dailyExecutions).toBe(0)
    })
  })

  describe('Feature Access Control', () => {
    const userId = 'test-user-123'

    test('should allow basic features for FREE tier', () => {
      tierService.setUserTier(userId, 'FREE')
      
      expect(tierService.hasFeatureAccess(userId, 'agentTypes')).toBeTruthy()
      expect(tierService.hasFeatureAccess(userId, 'customIntegrations')).toBe(false)
      expect(tierService.hasFeatureAccess(userId, 'advancedAnalytics')).toBe(false)
    })

    test('should allow advanced features for PRO tier', async () => {
      await tierService.setUserTier(userId, 'PRO')
      
      expect(tierService.hasFeatureAccess(userId, 'customIntegrations')).toBe(true)
      expect(tierService.hasFeatureAccess(userId, 'advancedAnalytics')).toBe(true)
      expect(tierService.hasFeatureAccess(userId, 'whiteLabel')).toBe(false)
    })

    test('should allow all features for ENTERPRISE tier', async () => {
      await tierService.setUserTier(userId, 'ENTERPRISE')
      
      expect(tierService.hasFeatureAccess(userId, 'customIntegrations')).toBe(true)
      expect(tierService.hasFeatureAccess(userId, 'advancedAnalytics')).toBe(true)
      expect(tierService.hasFeatureAccess(userId, 'whiteLabel')).toBe(true)
      expect(tierService.hasFeatureAccess(userId, 'customAgents')).toBe(true)
    })

    test('should return false for non-existent features', () => {
      expect(tierService.hasFeatureAccess(userId, 'nonExistentFeature')).toBe(false)
    })
  })

  describe('Usage Tracking and Quotas', () => {
    const userId = 'test-user-123'

    beforeEach(async () => {
      await tierService.setUserTier(userId, 'FREE')
    })

    test('should check quota availability correctly', async () => {
      const result = await tierService.canPerformAction(userId, 'monthlyExecutions', 1)
      
      expect(result.allowed).toBe(true)
      expect(result.remaining).toBe(99) // FREE tier has 100 monthly executions
    })

    test('should track usage successfully', async () => {
      const result = await tierService.trackUsage(userId, 'monthlyExecutions', 5)
      
      expect(result.success).toBe(true)
      expect(result.newUsage).toBe(5)
      expect(result.remaining).toBe(95)
      
      expect(auditService.logAccess.usageTracking).toHaveBeenCalledWith(
        'usage_tracked',
        expect.objectContaining({
          userId,
          action: 'monthlyExecutions',
          amount: 5
        })
      )
    })

    test('should prevent usage when quota exceeded', async () => {
      // Set usage to limit
      tierService.usageTracking.set(userId, {
        monthlyExecutions: 100,
        lastUpdated: Date.now()
      })

      await expect(
        tierService.trackUsage(userId, 'monthlyExecutions', 1)
      ).rejects.toThrow('Quota exceeded for monthlyExecutions')
      
      expect(auditService.logAccess.quotaExceeded).toHaveBeenCalled()
    })

    test('should allow unlimited usage for ENTERPRISE tier', async () => {
      await tierService.setUserTier(userId, 'ENTERPRISE')
      
      const result = await tierService.canPerformAction(userId, 'monthlyExecutions', 1000)
      expect(result.allowed).toBe(true)
      expect(result.remaining).toBe('unlimited')
    })

    test('should handle concurrent usage tracking', async () => {
      const promises = Array.from({ length: 10 }, () =>
        tierService.trackUsage(userId, 'monthlyExecutions', 1)
      )
      
      const results = await Promise.all(promises)
      
      expect(results.every(r => r.success)).toBe(true)
      
      const usage = tierService.getUserUsage(userId)
      expect(usage.monthlyExecutions).toBe(10)
    })
  })

  describe('Tier Upgrades and Downgrades', () => {
    const userId = 'test-user-123'
    const billingInfo = {
      paymentMethod: 'stripe',
      subscriptionId: 'sub_123',
      billingAddress: {
        country: 'US',
        postalCode: '12345'
      }
    }

    test('should upgrade tier successfully', async () => {
      await tierService.setUserTier(userId, 'FREE')
      
      const result = await tierService.upgradeTier(userId, 'PRO', billingInfo)
      
      expect(result.success).toBe(true)
      expect(result.newTier.id).toBe('pro')
      
      expect(auditService.logAccess.tierUpgrade).toHaveBeenCalledWith(
        'tier_upgraded',
        expect.objectContaining({
          userId,
          fromTier: 'free',
          toTier: 'PRO'
        })
      )
    })

    test('should prevent downgrade to higher priced tier', async () => {
      await tierService.setUserTier(userId, 'FREE')
      
      await expect(
        tierService.upgradeTier(userId, 'FREE', billingInfo)
      ).rejects.toThrow('Can only upgrade to higher tier')
    })

    test('should require billing info for paid tiers', async () => {
      await expect(
        tierService.upgradeTier(userId, 'PRO', null)
      ).rejects.toThrow('Valid billing information required')
    })

    test('should downgrade tier successfully', async () => {
      await tierService.setUserTier(userId, 'PRO')
      
      const result = await tierService.downgradeTier(userId, 'FREE')
      
      expect(result.success).toBe(true)
      expect(result.newTier.id).toBe('free')
      
      expect(auditService.logAccess.tierDowngrade).toHaveBeenCalled()
    })

    test('should check downgrade feasibility', async () => {
      await tierService.setUserTier(userId, 'PRO')
      
      // Set usage that exceeds FREE tier limits
      tierService.usageTracking.set(userId, {
        monthlyExecutions: 500, // Exceeds FREE tier limit of 100
        lastUpdated: Date.now()
      })
      
      await expect(
        tierService.downgradeTier(userId, 'FREE')
      ).rejects.toThrow('Downgrade not possible')
    })
  })

  describe('Upgrade Options', () => {
    const userId = 'test-user-123'

    test('should return upgrade options for FREE tier', () => {
      tierService.setUserTier(userId, 'FREE')
      
      const options = tierService.getUpgradeOptions(userId)
      
      expect(options).toHaveLength(2)
      expect(options[0].tierId).toBe('PRO')
      expect(options[1].tierId).toBe('ENTERPRISE')
      expect(options[0].price).toBeGreaterThan(0)
    })

    test('should return limited upgrade options for PRO tier', async () => {
      await tierService.setUserTier(userId, 'PRO')
      
      const options = tierService.getUpgradeOptions(userId)
      
      expect(options).toHaveLength(1)
      expect(options[0].tierId).toBe('ENTERPRISE')
    })

    test('should return no upgrade options for ENTERPRISE tier', async () => {
      await tierService.setUserTier(userId, 'ENTERPRISE')
      
      const options = tierService.getUpgradeOptions(userId)
      
      expect(options).toHaveLength(0)
    })

    test('should calculate savings for yearly billing', () => {
      const currentTier = tierService.tierDefinitions.FREE
      const newTier = { ...tierService.tierDefinitions.PRO, billingPeriod: 'yearly' }
      
      const savings = tierService.calculateSavings(currentTier, newTier)
      
      expect(savings).toBeTruthy()
      expect(savings.percentage).toBe(10)
      expect(savings.yearly).toBeGreaterThan(0)
    })
  })

  describe('Statistics and Analytics', () => {
    test('should return tier statistics', async () => {
      const userId1 = 'user-1'
      const userId2 = 'user-2'
      
      await tierService.setUserTier(userId1, 'PRO')
      await tierService.setUserTier(userId2, 'ENTERPRISE')
      
      const stats = tierService.getTierStatistics()
      
      expect(stats.totalUsers).toBe(2)
      expect(stats.tierDistribution.PRO).toBe(1)
      expect(stats.tierDistribution.ENTERPRISE).toBe(1)
      expect(stats.totalRevenue).toBeGreaterThan(0)
      expect(stats.averageRevenuePerUser).toBeGreaterThan(0)
    })

    test('should handle empty statistics', () => {
      const stats = tierService.getTierStatistics()
      
      expect(stats.totalUsers).toBe(0)
      expect(stats.totalRevenue).toBe(0)
      expect(stats.averageRevenuePerUser).toBe(0)
    })
  })

  describe('Quota Reset Functionality', () => {
    const userId = 'test-user-123'

    test('should reset daily quotas', () => {
      tierService.usageTracking.set(userId, {
        dailyExecutions: 10,
        monthlyExecutions: 50,
        lastUpdated: Date.now()
      })
      
      tierService.resetDailyQuotas()
      
      const usage = tierService.getUserUsage(userId)
      expect(usage.dailyExecutions).toBe(0)
      expect(usage.monthlyExecutions).toBe(50) // Should not be reset
    })

    test('should reset monthly quotas', () => {
      tierService.usageTracking.set(userId, {
        dailyExecutions: 10,
        monthlyExecutions: 50,
        lastUpdated: Date.now()
      })
      
      tierService.resetMonthlyQuotas()
      
      const usage = tierService.getUserUsage(userId)
      expect(usage.monthlyExecutions).toBe(0)
      expect(usage.dailyExecutions).toBe(10) // Should not be reset
    })

    test('should get next reset date correctly', () => {
      const nextReset = tierService.getNextResetDate()
      const now = new Date()
      const expectedNext = new Date(now.getFullYear(), now.getMonth() + 1, 1)
      
      expect(nextReset).toBe(expectedNext.getTime())
    })
  })

  describe('Error Handling', () => {
    const userId = 'test-user-123'

    test('should handle invalid user ID gracefully', () => {
      const tier = tierService.getUserTier(null)
      expect(tier.id).toBe('free')
    })

    test('should handle missing usage data', () => {
      const usage = tierService.getUserUsage('non-existent-user')
      expect(usage.monthlyExecutions).toBe(0)
      expect(usage.dailyExecutions).toBe(0)
    })

    test('should validate billing information', () => {
      const validBilling = {
        paymentMethod: 'stripe',
        billingAddress: { country: 'US' }
      }
      
      const invalidBilling = {
        paymentMethod: 'stripe'
        // Missing billingAddress
      }
      
      expect(tierService.validateBillingInfo(validBilling)).toBe(true)
      expect(tierService.validateBillingInfo(invalidBilling)).toBe(false)
    })
  })

  describe('Integration Points', () => {
    test('should integrate with audit service', async () => {
      const userId = 'test-user-123'
      
      await tierService.setUserTier(userId, 'PRO')
      await tierService.trackUsage(userId, 'monthlyExecutions', 1)
      
      expect(auditService.logAccess.tierChange).toHaveBeenCalled()
      expect(auditService.logAccess.usageTracking).toHaveBeenCalled()
    })

    test('should handle audit service failures gracefully', async () => {
      auditService.logAccess.tierChange.mockRejectedValue(new Error('Audit failed'))
      
      const userId = 'test-user-123'
      
      // Should not throw even if audit fails
      await expect(
        tierService.setUserTier(userId, 'PRO')
      ).resolves.toBeTruthy()
    })
  })
})
