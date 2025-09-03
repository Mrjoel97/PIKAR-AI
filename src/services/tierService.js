/**
 * Tier Service
 * Comprehensive pricing tier management system for PIKAR AI
 */

import { auditService } from './auditService'
import { loggingService } from './loggingService'
import { environmentConfig } from '@/config/environment'

class TierService {
  constructor() {
    this.tiers = new Map()
    this.userTiers = new Map()
    this.usageTracking = new Map()
    this.quotaLimits = new Map()
    this.isInitialized = false
    
    // Tier definitions - PIKAR AI Blueprint Compliant
    this.tierDefinitions = {
      SOLOPRENEUR: {
        id: 'solopreneur',
        name: 'Solopreneur',
        price: 99,
        billingPeriod: 'monthly',
        trialDays: 7,
        features: {
          agentTypes: ['strategic_planning', 'customer_support', 'content_creation', 'sales_intelligence'],
          maxAgentExecutions: 500,
          maxTeamMembers: 1,
          maxProjects: 10,
          maxFileUploads: 50,
          maxStorageGB: 5,
          supportLevel: 'email',
          analyticsRetentionDays: 60,
          customIntegrations: true,
          whiteLabel: false,
          apiAccess: false,
          advancedAnalytics: true,
          prioritySupport: false,
          customAgents: false,
          abTesting: false,
          marketingAutomation: true,
          socialScheduling: true,
          workflowTemplates: true
        },
        limits: {
          dailyExecutions: 25,
          monthlyExecutions: 500,
          concurrentExecutions: 2,
          fileUploadSizeMB: 25,
          apiCallsPerDay: 500,
          workflowsPerMonth: 10
        }
      },
      STARTUP: {
        id: 'startup',
        name: 'Startup',
        price: 297,
        billingPeriod: 'monthly',
        trialDays: 7,
        features: {
          agentTypes: 'all',
          maxAgentExecutions: 2000,
          maxTeamMembers: 5,
          maxProjects: 50,
          maxFileUploads: 200,
          maxStorageGB: 25,
          supportLevel: 'priority',
          analyticsRetentionDays: 120,
          customIntegrations: true,
          whiteLabel: false,
          apiAccess: true,
          advancedAnalytics: true,
          prioritySupport: true,
          customAgents: false,
          abTesting: true,
          marketingAutomation: true,
          socialScheduling: true,
          workflowTemplates: true,
          teamCollaboration: true,
          advancedReporting: true
        },
        limits: {
          dailyExecutions: 100,
          monthlyExecutions: 2000,
          concurrentExecutions: 5,
          fileUploadSizeMB: 100,
          apiCallsPerDay: 2000,
          workflowsPerMonth: 50
        }
      },
      SME: {
        id: 'sme',
        name: 'SME',
        price: 597,
        billingPeriod: 'monthly',
        trialDays: 7,
        features: {
          agentTypes: 'all',
          maxAgentExecutions: 5000,
          maxTeamMembers: 15,
          maxProjects: 'unlimited',
          maxFileUploads: 500,
          maxStorageGB: 100,
          supportLevel: 'priority',
          analyticsRetentionDays: 180,
          customIntegrations: true,
          whiteLabel: true,
          apiAccess: true,
          advancedAnalytics: true,
          prioritySupport: true,
          customAgents: true,
          abTesting: true,
          marketingAutomation: true,
          socialScheduling: true,
          workflowTemplates: true,
          teamCollaboration: true,
          advancedReporting: true,
          customReports: true,
          bulkOperations: true
        },
        limits: {
          dailyExecutions: 250,
          monthlyExecutions: 5000,
          concurrentExecutions: 10,
          fileUploadSizeMB: 250,
          apiCallsPerDay: 5000,
          workflowsPerMonth: 'unlimited'
        }
      },
      ENTERPRISE: {
        id: 'enterprise',
        name: 'Enterprise',
        price: 'contact_sales',
        billingPeriod: 'monthly',
        trialDays: 7,
        features: {
          agentTypes: 'all',
          maxAgentExecutions: 'unlimited',
          maxTeamMembers: 'unlimited',
          maxProjects: 'unlimited',
          maxFileUploads: 'unlimited',
          maxStorageGB: 'unlimited',
          supportLevel: 'dedicated',
          analyticsRetentionDays: 365,
          customIntegrations: true,
          whiteLabel: true,
          apiAccess: true,
          advancedAnalytics: true,
          prioritySupport: true,
          customAgents: true,
          abTesting: true,
          marketingAutomation: true,
          socialScheduling: true,
          workflowTemplates: true,
          teamCollaboration: true,
          advancedReporting: true,
          customReports: true,
          bulkOperations: true,
          customSLA: true,
          dedicatedManager: true,
          onPremiseDeployment: true,
          ssoIntegration: true,
          advancedSecurity: true,
          auditLogs: true,
          dataExport: true
        },
        limits: {
          dailyExecutions: 'unlimited',
          monthlyExecutions: 'unlimited',
          concurrentExecutions: 'unlimited',
          fileUploadSizeMB: 'unlimited',
          apiCallsPerDay: 'unlimited',
          workflowsPerMonth: 'unlimited'
        }
      }
    }
    
    this.setupTiers()
  }

  /**
   * Initialize tier service
   */
  async initialize() {
    try {
      console.log('💰 Initializing Tier Service...')
      
      // Load user tier data
      await this.loadUserTierData()
      
      // Initialize usage tracking
      this.initializeUsageTracking()
      
      // Setup quota monitoring
      this.setupQuotaMonitoring()
      
      this.isInitialized = true
      
      console.log('✅ Tier Service initialized successfully')
      
      await auditService.logSystem.tier('tier_service_initialized', {
        availableTiers: Object.keys(this.tierDefinitions),
        totalUsers: this.userTiers.size
      })
      
    } catch (error) {
      console.error('❌ Tier Service initialization failed:', error)
      throw error
    }
  }

  /**
   * Setup tier configurations
   */
  setupTiers() {
    for (const [key, tier] of Object.entries(this.tierDefinitions)) {
      this.tiers.set(key, {
        ...tier,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        isActive: true
      })
    }
  }

  /**
   * Get user's current tier
   */
  getUserTier(userId) {
    if (!userId) return null // No default tier - users must select during onboarding

    const userTier = this.userTiers.get(userId)
    if (!userTier) {
      return null // New users need to select a tier and start trial
    }

    return this.tierDefinitions[userTier.tierId] || null
  }

  /**
   * Check if user is in trial period
   */
  isUserInTrial(userId) {
    if (!userId) return false

    const userTier = this.userTiers.get(userId)
    if (!userTier) return false

    const now = Date.now()
    return userTier.trialEndDate && now < userTier.trialEndDate
  }

  /**
   * Get trial days remaining
   */
  getTrialDaysRemaining(userId) {
    if (!userId) return 0

    const userTier = this.userTiers.get(userId)
    if (!userTier || !userTier.trialEndDate) return 0

    const now = Date.now()
    const msRemaining = userTier.trialEndDate - now
    const daysRemaining = Math.ceil(msRemaining / (24 * 60 * 60 * 1000))

    return Math.max(0, daysRemaining)
  }

  /**
   * Start trial for user
   */
  async startTrial(userId, tierId) {
    if (!userId || !tierId) {
      throw new Error('User ID and tier ID are required')
    }

    const tier = this.tierDefinitions[tierId.toUpperCase()]
    if (!tier) {
      throw new Error(`Invalid tier ID: ${tierId}`)
    }

    const now = Date.now()
    const trialEndDate = now + (tier.trialDays * 24 * 60 * 60 * 1000)

    const userTier = {
      userId,
      tierId: tierId.toUpperCase(),
      status: 'trial',
      trialStartDate: now,
      trialEndDate: trialEndDate,
      billingInfo: null,
      createdAt: now,
      updatedAt: now
    }

    this.userTiers.set(userId, userTier)

    // Initialize usage tracking
    this.usageTracking.set(userId, {
      monthlyExecutions: 0,
      dailyExecutions: 0,
      fileUploadSizeMB: 0,
      workflowsThisMonth: 0,
      lastReset: now,
      lastUpdated: now
    })

    await auditService.logAccess.tierChange('trial_started', {
      userId,
      tierId: tierId.toUpperCase(),
      trialDays: tier.trialDays,
      trialEndDate
    })

    return userTier
  }

  /**
   * Set user tier
   */
  async setUserTier(userId, tierId, billingInfo = null) {
    if (!this.tierDefinitions[tierId]) {
      throw new Error(`Invalid tier ID: ${tierId}`)
    }
    
    const previousTier = this.userTiers.get(userId)
    const newTier = {
      userId,
      tierId,
      startDate: Date.now(),
      billingInfo,
      status: 'active',
      usageReset: this.getNextResetDate(),
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    
    this.userTiers.set(userId, newTier)
    
    // Reset usage tracking for new tier
    this.resetUserUsage(userId)
    
    // Log tier change
    await auditService.logAccess.tierChange('user_tier_changed', {
      userId,
      previousTier: previousTier?.tierId || 'none',
      newTier: tierId,
      billingInfo: billingInfo ? 'provided' : 'none'
    })
    
    return newTier
  }

  /**
   * Check if user has access to feature
   */
  hasFeatureAccess(userId, feature) {
    const userTier = this.getUserTier(userId)
    
    if (!userTier.features.hasOwnProperty(feature)) {
      return false
    }
    
    const featureValue = userTier.features[feature]
    
    // Boolean features
    if (typeof featureValue === 'boolean') {
      return featureValue
    }
    
    // Array features (like agentTypes)
    if (Array.isArray(featureValue)) {
      return featureValue
    }
    
    // String features
    if (featureValue === 'all' || featureValue === 'unlimited') {
      return true
    }
    
    return featureValue
  }

  /**
   * Check if user can perform action based on limits
   */
  async canPerformAction(userId, action, amount = 1) {
    const userTier = this.getUserTier(userId)
    const usage = this.getUserUsage(userId)
    
    const limit = userTier.limits[action]
    
    if (limit === 'unlimited') {
      return { allowed: true, remaining: 'unlimited' }
    }
    
    if (typeof limit !== 'number') {
      return { allowed: false, reason: 'Invalid limit configuration' }
    }
    
    const currentUsage = usage[action] || 0
    const remaining = limit - currentUsage
    
    if (remaining >= amount) {
      return { allowed: true, remaining: remaining - amount }
    }
    
    return { 
      allowed: false, 
      reason: 'Quota exceeded',
      current: currentUsage,
      limit,
      requested: amount
    }
  }

  /**
   * Track usage for user
   */
  async trackUsage(userId, action, amount = 1) {
    const canPerform = await this.canPerformAction(userId, action, amount)
    
    if (!canPerform.allowed) {
      await auditService.logAccess.quotaExceeded('quota_exceeded', {
        userId,
        action,
        amount,
        reason: canPerform.reason,
        current: canPerform.current,
        limit: canPerform.limit
      })
      
      throw new Error(`Quota exceeded for ${action}: ${canPerform.reason}`)
    }
    
    // Update usage
    const usage = this.getUserUsage(userId)
    usage[action] = (usage[action] || 0) + amount
    usage.lastUpdated = Date.now()
    
    this.usageTracking.set(userId, usage)
    
    // Log usage
    await auditService.logAccess.usageTracking('usage_tracked', {
      userId,
      action,
      amount,
      newTotal: usage[action],
      remaining: canPerform.remaining
    })
    
    return {
      success: true,
      newUsage: usage[action],
      remaining: canPerform.remaining
    }
  }

  /**
   * Get user usage statistics
   */
  getUserUsage(userId) {
    return this.usageTracking.get(userId) || {
      dailyExecutions: 0,
      monthlyExecutions: 0,
      concurrentExecutions: 0,
      fileUploadSizeMB: 0,
      apiCallsPerDay: 0,
      lastReset: Date.now(),
      lastUpdated: Date.now()
    }
  }

  /**
   * Reset user usage (monthly reset)
   */
  resetUserUsage(userId) {
    const resetUsage = {
      dailyExecutions: 0,
      monthlyExecutions: 0,
      concurrentExecutions: 0,
      fileUploadSizeMB: 0,
      apiCallsPerDay: 0,
      lastReset: Date.now(),
      lastUpdated: Date.now()
    }
    
    this.usageTracking.set(userId, resetUsage)
    
    loggingService.info('User usage reset', {
      userId,
      resetDate: new Date().toISOString()
    })
  }

  /**
   * Get tier upgrade options for user
   */
  getUpgradeOptions(userId) {
    const currentTier = this.getUserTier(userId)
    const options = []
    
    for (const [tierId, tier] of Object.entries(this.tierDefinitions)) {
      if (tier.price > currentTier.price) {
        options.push({
          tierId,
          name: tier.name,
          price: tier.price,
          billingPeriod: tier.billingPeriod,
          features: tier.features,
          limits: tier.limits,
          savings: this.calculateSavings(currentTier, tier)
        })
      }
    }
    
    return options.sort((a, b) => a.price - b.price)
  }

  /**
   * Calculate savings for tier upgrade
   */
  calculateSavings(currentTier, newTier) {
    if (newTier.billingPeriod === 'yearly') {
      const monthlyEquivalent = newTier.price / 12
      const monthlySavings = (newTier.price / 10) - monthlyEquivalent // 10% discount for yearly
      return {
        monthly: monthlySavings,
        yearly: monthlySavings * 12,
        percentage: 10
      }
    }
    
    return null
  }

  /**
   * Process tier upgrade
   */
  async upgradeTier(userId, newTierId, billingInfo) {
    const currentTier = this.getUserTier(userId)
    const newTier = this.tierDefinitions[newTierId]
    
    if (!newTier) {
      throw new Error(`Invalid tier: ${newTierId}`)
    }
    
    if (newTier.price <= currentTier.price) {
      throw new Error('Can only upgrade to higher tier')
    }
    
    // Validate billing information
    if (!billingInfo || !this.validateBillingInfo(billingInfo)) {
      throw new Error('Valid billing information required')
    }
    
    try {
      // Process payment (integrate with billing service)
      const paymentResult = await this.processTierPayment(userId, newTier, billingInfo)
      
      if (!paymentResult.success) {
        throw new Error(`Payment failed: ${paymentResult.error}`)
      }
      
      // Update user tier
      await this.setUserTier(userId, newTierId, {
        ...billingInfo,
        paymentId: paymentResult.paymentId,
        subscriptionId: paymentResult.subscriptionId
      })
      
      // Log successful upgrade
      await auditService.logAccess.tierUpgrade('tier_upgraded', {
        userId,
        fromTier: currentTier.id,
        toTier: newTierId,
        price: newTier.price,
        paymentId: paymentResult.paymentId
      })
      
      return {
        success: true,
        newTier: newTier,
        paymentId: paymentResult.paymentId,
        subscriptionId: paymentResult.subscriptionId
      }
      
    } catch (error) {
      await auditService.logSystem.error(error, 'tier_upgrade_failed', {
        userId,
        targetTier: newTierId
      })
      
      throw error
    }
  }

  /**
   * Process tier downgrade
   */
  async downgradeTier(userId, newTierId) {
    const currentTier = this.getUserTier(userId)
    const newTier = this.tierDefinitions[newTierId]
    
    if (!newTier) {
      throw new Error(`Invalid tier: ${newTierId}`)
    }
    
    if (newTier.price >= currentTier.price) {
      throw new Error('Can only downgrade to lower tier')
    }
    
    // Check if downgrade is allowed (no active features that would be lost)
    const downgradeFeasible = await this.checkDowngradeFeasibility(userId, newTier)
    
    if (!downgradeFeasible.allowed) {
      throw new Error(`Downgrade not possible: ${downgradeFeasible.reason}`)
    }
    
    // Process refund if applicable
    const refundResult = await this.processRefund(userId, currentTier, newTier)
    
    // Update user tier
    await this.setUserTier(userId, newTierId)
    
    // Log downgrade
    await auditService.logAccess.tierDowngrade('tier_downgraded', {
      userId,
      fromTier: currentTier.id,
      toTier: newTierId,
      refundAmount: refundResult.amount
    })
    
    return {
      success: true,
      newTier: newTier,
      refundAmount: refundResult.amount
    }
  }

  /**
   * Check if downgrade is feasible
   */
  async checkDowngradeFeasibility(userId, newTier) {
    const usage = this.getUserUsage(userId)
    const issues = []
    
    // Check usage against new limits
    for (const [limit, value] of Object.entries(newTier.limits)) {
      if (value !== 'unlimited' && usage[limit] > value) {
        issues.push(`Current ${limit} usage (${usage[limit]}) exceeds new limit (${value})`)
      }
    }
    
    // Check feature dependencies
    // This would check if user has active features that won't be available in new tier
    
    return {
      allowed: issues.length === 0,
      reason: issues.join('; '),
      issues
    }
  }

  /**
   * Get next billing reset date
   */
  getNextResetDate() {
    const now = new Date()
    const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1)
    return nextMonth.getTime()
  }

  /**
   * Setup quota monitoring
   */
  setupQuotaMonitoring() {
    // Daily reset for daily quotas
    setInterval(() => {
      this.resetDailyQuotas()
    }, 24 * 60 * 60 * 1000) // 24 hours
    
    // Monthly reset for monthly quotas
    setInterval(() => {
      this.resetMonthlyQuotas()
    }, 30 * 24 * 60 * 60 * 1000) // 30 days
  }

  /**
   * Reset daily quotas
   */
  resetDailyQuotas() {
    for (const [userId, usage] of this.usageTracking.entries()) {
      usage.dailyExecutions = 0
      usage.apiCallsPerDay = 0
      usage.lastUpdated = Date.now()
    }
    
    loggingService.info('Daily quotas reset for all users')
  }

  /**
   * Reset monthly quotas
   */
  resetMonthlyQuotas() {
    for (const [userId, usage] of this.usageTracking.entries()) {
      usage.monthlyExecutions = 0
      usage.fileUploadSizeMB = 0
      usage.lastReset = Date.now()
      usage.lastUpdated = Date.now()
    }
    
    loggingService.info('Monthly quotas reset for all users')
  }

  /**
   * Initialize usage tracking
   */
  initializeUsageTracking() {
    // Load existing usage data from storage
    // This would typically load from database
    console.log('Usage tracking initialized')
  }

  /**
   * Load user tier data
   */
  async loadUserTierData() {
    // Load user tier assignments from database
    // This would typically load from database
    console.log('User tier data loaded')
  }

  /**
   * Validate billing information
   */
  validateBillingInfo(billingInfo) {
    return billingInfo && 
           billingInfo.paymentMethod && 
           billingInfo.billingAddress
  }

  /**
   * Process tier payment (placeholder)
   */
  async processTierPayment(userId, tier, billingInfo) {
    // This would integrate with actual payment processor (Stripe, PayPal, etc.)
    return {
      success: true,
      paymentId: `pay_${Date.now()}`,
      subscriptionId: `sub_${Date.now()}`
    }
  }

  /**
   * Process refund (placeholder)
   */
  async processRefund(userId, oldTier, newTier) {
    // Calculate prorated refund
    const refundAmount = Math.max(0, oldTier.price - newTier.price)
    
    return {
      success: true,
      amount: refundAmount
    }
  }

  /**
   * Get tier statistics
   */
  getTierStatistics() {
    const stats = {
      totalUsers: this.userTiers.size,
      tierDistribution: {},
      totalRevenue: 0,
      averageRevenuePerUser: 0
    }
    
    for (const [userId, userTier] of this.userTiers.entries()) {
      const tier = this.tierDefinitions[userTier.tierId]
      stats.tierDistribution[userTier.tierId] = (stats.tierDistribution[userTier.tierId] || 0) + 1
      stats.totalRevenue += tier.price
    }
    
    stats.averageRevenuePerUser = stats.totalUsers > 0 ? stats.totalRevenue / stats.totalUsers : 0
    
    return stats
  }
}

export const tierService = new TierService()
