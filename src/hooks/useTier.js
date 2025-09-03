/**
 * Tier Hook
 * Custom hook for tier-related functionality and utilities
 */

import { useTier as useBaseTier } from '@/contexts/TierContext'
import { useMemo } from 'react'

export function useTier() {
  return useBaseTier()
}

/**
 * Hook for tier-specific feature access
 */
export function useTierFeature(feature) {
  const { hasFeatureAccess, currentTier, isLoading } = useTier()
  
  return useMemo(() => ({
    hasAccess: hasFeatureAccess(feature),
    tier: currentTier,
    isLoading,
    featureValue: currentTier?.features?.[feature]
  }), [hasFeatureAccess, feature, currentTier, isLoading])
}

/**
 * Hook for quota management
 */
export function useQuota(quotaType) {
  const { 
    currentTier, 
    usage, 
    getUsagePercentage, 
    getRemainingQuota,
    canPerformAction,
    trackUsage 
  } = useTier()
  
  return useMemo(() => {
    const limit = currentTier?.limits?.[quotaType]
    const currentUsage = usage?.[quotaType] || 0
    const percentage = getUsagePercentage(quotaType)
    const remaining = getRemainingQuota(quotaType)
    
    return {
      limit,
      currentUsage,
      percentage,
      remaining,
      isUnlimited: limit === 'unlimited',
      isNearLimit: percentage >= 80,
      isAtLimit: percentage >= 100,
      canPerformAction: (amount = 1) => canPerformAction(quotaType, amount),
      trackUsage: (amount = 1) => trackUsage(quotaType, amount)
    }
  }, [currentTier, usage, quotaType, getUsagePercentage, getRemainingQuota, canPerformAction, trackUsage])
}

/**
 * Hook for tier comparison
 */
export function useTierComparison() {
  const { currentTier, upgradeOptions } = useTier()
  
  return useMemo(() => {
    const tiers = [
      {
        id: 'solopreneur',
        name: 'Solopreneur',
        price: 99,
        trialDays: 7,
        features: {
          agentTypes: 4,
          maxAgentExecutions: 500,
          maxTeamMembers: 1,
          maxProjects: 10,
          supportLevel: 'Email',
          advancedAnalytics: true,
          customIntegrations: true,
          apiAccess: false,
          marketingAutomation: true,
          socialScheduling: true
        }
      },
      {
        id: 'startup',
        name: 'Startup',
        price: 297,
        trialDays: 7,
        features: {
          agentTypes: 'All',
          maxAgentExecutions: 2000,
          maxTeamMembers: 5,
          maxProjects: 50,
          supportLevel: 'Priority',
          advancedAnalytics: true,
          customIntegrations: true,
          apiAccess: true,
          abTesting: true,
          teamCollaboration: true
        }
      },
      {
        id: 'sme',
        name: 'SME',
        price: 597,
        trialDays: 7,
        features: {
          agentTypes: 'All',
          maxAgentExecutions: 5000,
          maxTeamMembers: 15,
          maxProjects: 'Unlimited',
          supportLevel: 'Priority',
          advancedAnalytics: true,
          customIntegrations: true,
          apiAccess: true,
          whiteLabel: true,
          customAgents: true,
          bulkOperations: true
        }
      },
      {
        id: 'enterprise',
        name: 'Enterprise',
        price: 'Contact Sales',
        trialDays: 7,
        features: {
          agentTypes: 'All',
          maxAgentExecutions: 'Unlimited',
          maxTeamMembers: 'Unlimited',
          maxProjects: 'Unlimited',
          supportLevel: 'Dedicated',
          advancedAnalytics: true,
          customIntegrations: true,
          apiAccess: true,
          whiteLabel: true,
          customAgents: true,
          ssoIntegration: true,
          advancedSecurity: true,
          onPremiseDeployment: true
        }
      }
    ]
    
    return {
      tiers,
      currentTier,
      upgradeOptions,
      canUpgrade: upgradeOptions.length > 0
    }
  }, [currentTier, upgradeOptions])
}

/**
 * Hook for billing information
 */
export function useBilling() {
  const { 
    currentTier, 
    billingInfo, 
    upgradeTier, 
    downgradeTier, 
    isLoading 
  } = useTier()
  
  const nextBillingDate = useMemo(() => {
    if (!billingInfo?.subscriptionId) return null
    
    // Calculate next billing date based on billing period
    const now = new Date()
    if (currentTier?.billingPeriod === 'monthly') {
      return new Date(now.getFullYear(), now.getMonth() + 1, now.getDate())
    } else if (currentTier?.billingPeriod === 'yearly') {
      return new Date(now.getFullYear() + 1, now.getMonth(), now.getDate())
    }
    
    return null
  }, [billingInfo, currentTier])
  
  const monthlyPrice = useMemo(() => {
    if (!currentTier) return 0
    
    if (currentTier.billingPeriod === 'yearly') {
      return currentTier.price / 12
    }
    
    return currentTier.price
  }, [currentTier])
  
  return {
    currentTier,
    billingInfo,
    nextBillingDate,
    monthlyPrice,
    isLoading,
    upgradeTier,
    downgradeTier,
    hasActiveBilling: !!billingInfo?.subscriptionId
  }
}

/**
 * Hook for tier restrictions
 */
export function useTierRestrictions() {
  const { currentTier, hasFeatureAccess } = useTier()
  
  return useMemo(() => {
    const restrictions = []
    
    if (!currentTier) return restrictions
    
    // Check common restrictions
    if (!hasFeatureAccess('customIntegrations')) {
      restrictions.push({
        feature: 'customIntegrations',
        message: 'Custom integrations require Pro or Enterprise tier',
        upgradeRequired: 'pro'
      })
    }
    
    if (!hasFeatureAccess('advancedAnalytics')) {
      restrictions.push({
        feature: 'advancedAnalytics',
        message: 'Advanced analytics require Pro or Enterprise tier',
        upgradeRequired: 'pro'
      })
    }
    
    if (!hasFeatureAccess('apiAccess')) {
      restrictions.push({
        feature: 'apiAccess',
        message: 'API access requires Pro or Enterprise tier',
        upgradeRequired: 'pro'
      })
    }
    
    if (!hasFeatureAccess('whiteLabel')) {
      restrictions.push({
        feature: 'whiteLabel',
        message: 'White-label features require Enterprise tier',
        upgradeRequired: 'enterprise'
      })
    }
    
    if (!hasFeatureAccess('customAgents')) {
      restrictions.push({
        feature: 'customAgents',
        message: 'Custom agent development requires Enterprise tier',
        upgradeRequired: 'enterprise'
      })
    }
    
    return restrictions
  }, [currentTier, hasFeatureAccess])
}

/**
 * Hook for usage analytics
 */
export function useUsageAnalytics() {
  const { usage, currentTier } = useTier()
  
  return useMemo(() => {
    if (!usage || !currentTier) {
      return {
        totalUsage: 0,
        usageByCategory: {},
        efficiency: 0,
        trends: []
      }
    }
    
    const usageByCategory = {
      executions: usage.monthlyExecutions || 0,
      storage: usage.fileUploadSizeMB || 0,
      apiCalls: usage.apiCallsPerDay || 0
    }
    
    const totalPossibleUsage = Object.entries(currentTier.limits)
      .filter(([_, limit]) => limit !== 'unlimited')
      .reduce((sum, [key, limit]) => sum + (usage[key] || 0), 0)
    
    const totalLimits = Object.entries(currentTier.limits)
      .filter(([_, limit]) => limit !== 'unlimited')
      .reduce((sum, [_, limit]) => sum + limit, 0)
    
    const efficiency = totalLimits > 0 ? (totalPossibleUsage / totalLimits) * 100 : 0
    
    return {
      totalUsage: totalPossibleUsage,
      usageByCategory,
      efficiency: Math.round(efficiency),
      trends: [] // Would be populated with historical data
    }
  }, [usage, currentTier])
}

/**
 * Hook for tier recommendations
 */
export function useTierRecommendations() {
  const { currentTier, usage, upgradeOptions } = useTier()
  const { efficiency } = useUsageAnalytics()
  
  return useMemo(() => {
    const recommendations = []
    
    if (!currentTier || !usage) return recommendations
    
    // High usage recommendation
    if (efficiency > 80) {
      const nextTier = upgradeOptions[0]
      if (nextTier) {
        recommendations.push({
          type: 'upgrade',
          reason: 'high_usage',
          message: `You're using ${efficiency}% of your current limits. Consider upgrading to ${nextTier.name} for more capacity.`,
          tier: nextTier,
          priority: 'high'
        })
      }
    }
    
    // Feature-based recommendations
    if (currentTier.id === 'free') {
      recommendations.push({
        type: 'upgrade',
        reason: 'features',
        message: 'Unlock advanced analytics, custom integrations, and priority support with Pro.',
        tier: upgradeOptions.find(t => t.tierId === 'pro'),
        priority: 'medium'
      })
    }
    
    // Low usage recommendation (for paid tiers)
    if (currentTier.id !== 'free' && efficiency < 20) {
      recommendations.push({
        type: 'optimize',
        reason: 'low_usage',
        message: `You're only using ${efficiency}% of your current tier. Consider optimizing your usage or downgrading.`,
        priority: 'low'
      })
    }
    
    return recommendations
  }, [currentTier, usage, upgradeOptions, efficiency])
}
