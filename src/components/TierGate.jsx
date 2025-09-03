/**
 * Tier Gate Component
 * Controls access to features based on user's subscription tier
 */

import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Crown, Zap, Star, Lock, TrendingUp } from 'lucide-react'
import { useTier, useTierFeature, useQuota } from '@/hooks/useTier'
import { toast } from 'sonner'

const TIER_CONFIGS = {
  solopreneur: {
    name: 'Solopreneur',
    icon: Star,
    color: 'bg-blue-100 text-blue-800',
    gradient: 'from-blue-500 to-cyan-500',
    price: 99
  },
  startup: {
    name: 'Startup',
    icon: Zap,
    color: 'bg-purple-100 text-purple-800',
    gradient: 'from-purple-500 to-pink-500',
    price: 297
  },
  sme: {
    name: 'SME',
    icon: TrendingUp,
    color: 'bg-green-100 text-green-800',
    gradient: 'from-green-500 to-emerald-500',
    price: 597
  },
  enterprise: {
    name: 'Enterprise',
    icon: Crown,
    color: 'bg-gray-100 text-gray-800',
    gradient: 'from-gray-700 to-gray-900',
    price: 'Contact Sales'
  }
}

export default function TierGate({
  children,
  requiredTier = 'pro',
  feature,
  fallback,
  showUpgrade = true,
  quotaType = null,
  quotaAmount = 1,
  className = ''
}) {
  const {
    currentTier,
    hasFeatureAccess,
    canPerformAction,
    upgradeTier,
    isLoading,
    upgradeOptions
  } = useTier()

  const tierFeature = useTierFeature(feature)
  const quota = useQuota(quotaType)

  // Check feature access
  const hasFeatureAccessCheck = feature ? hasFeatureAccess(feature) : true

  // Check tier hierarchy access
  const hasTierAccess = checkTierAccess(currentTier?.id, requiredTier)

  // Check quota access
  const hasQuotaAccess = quotaType ? !quota.isAtLimit : true

  const hasAccess = hasFeatureAccessCheck && hasTierAccess && hasQuotaAccess

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (hasAccess) {
    return children
  }

  if (fallback) {
    return fallback
  }

  const requiredTierConfig = TIER_CONFIGS[requiredTier]
  const IconComponent = requiredTierConfig?.icon || Lock

  const handleUpgrade = async (tierId) => {
    try {
      // This would open a billing modal in a real implementation
      toast.info(`Upgrade to ${TIER_CONFIGS[tierId]?.name} - Opening billing...`)
      // await upgradeTier(tierId, billingInfo)
    } catch (error) {
      toast.error('Upgrade failed. Please try again.')
    }
  }

  return (
    <Card className={`w-full max-w-md mx-auto ${className}`}>
      <CardHeader className="text-center">
        <div className={`mx-auto w-12 h-12 bg-gradient-to-br ${requiredTierConfig?.gradient} rounded-full flex items-center justify-center mb-4`}>
          <IconComponent className="w-6 h-6 text-white" />
        </div>

        <CardTitle className="flex items-center justify-center gap-2">
          {!hasFeatureAccessCheck && 'Feature Upgrade Required'}
          {!hasTierAccess && 'Tier Upgrade Required'}
          {!hasQuotaAccess && 'Quota Limit Reached'}
        </CardTitle>

        <CardDescription>
          {!hasFeatureAccessCheck && feature && (
            <>This feature requires a {requiredTierConfig?.name} subscription</>
          )}
          {!hasTierAccess && (
            <>Access requires {requiredTierConfig?.name} tier or higher</>
          )}
          {!hasQuotaAccess && quotaType && (
            <>You've reached your {quotaType} limit for this billing period</>
          )}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Current tier info */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="text-sm text-gray-600">Current:</span>
            <Badge className={TIER_CONFIGS[currentTier?.id]?.color}>
              {currentTier?.name || 'Unknown'}
            </Badge>
          </div>

          {!hasQuotaAccess && quota && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Usage</span>
                <span>{quota.currentUsage} / {quota.limit}</span>
              </div>
              <Progress value={quota.percentage} className="h-2" />
              <p className="text-xs text-gray-500">
                Resets on your next billing cycle
              </p>
            </div>
          )}
        </div>

        {/* Feature benefits */}
        {requiredTierConfig && (
          <div className="space-y-2">
            <h4 className="font-medium text-sm">What you'll get:</h4>
            <ul className="space-y-1 text-sm text-gray-600">
              {getFeatureBenefits(requiredTier).map((benefit, index) => (
                <li key={index} className="flex items-center">
                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-2" />
                  {benefit}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Upgrade options */}
        {showUpgrade && upgradeOptions.length > 0 && (
          <div className="space-y-2">
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => toast.info('Opening feature comparison...')}
              >
                Compare Plans
              </Button>
              <Button
                className="flex-1"
                onClick={() => handleUpgrade(upgradeOptions[0]?.tierId)}
              >
                <TrendingUp className="w-4 h-4 mr-1" />
                Upgrade Now
              </Button>
            </div>

            {upgradeOptions[0] && (
              <p className="text-xs text-center text-gray-500">
                Starting at ${upgradeOptions[0].price}/month
              </p>
            )}
          </div>
        )}

        {/* Quota-specific actions */}
        {!hasQuotaAccess && (
          <div className="pt-2 border-t">
            <p className="text-xs text-gray-600 mb-2">
              Need more {quotaType}? Upgrade for higher limits:
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {upgradeOptions.slice(0, 2).map((option) => (
                <div key={option.tierId} className="text-center p-2 bg-gray-50 rounded">
                  <div className="font-medium">{option.name}</div>
                  <div className="text-gray-600">
                    {getQuotaLimit(option.tierId, quotaType)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function checkTierAccess(userTier, requiredTier) {
  const tierHierarchy = ['free', 'pro', 'enterprise']
  const userTierIndex = tierHierarchy.indexOf(userTier)
  const requiredTierIndex = tierHierarchy.indexOf(requiredTier)

  return userTierIndex >= requiredTierIndex
}

function getFeatureBenefits(tierId) {
  const benefits = {
    free: [
      'Basic AI agents',
      '100 monthly executions',
      'Community support'
    ],
    pro: [
      'All AI agent types',
      '1,000 monthly executions',
      'Advanced analytics',
      'Priority support',
      'Custom integrations',
      'A/B testing'
    ],
    enterprise: [
      'Unlimited executions',
      'Custom AI agents',
      'White-label options',
      'Dedicated support',
      'On-premise deployment',
      'Custom SLA'
    ]
  }

  return benefits[tierId] || []
}

function getQuotaLimit(tierId, quotaType) {
  const limits = {
    free: {
      dailyExecutions: '10/day',
      monthlyExecutions: '100/month',
      fileUploadSizeMB: '10MB',
      apiCallsPerDay: '100/day'
    },
    pro: {
      dailyExecutions: '50/day',
      monthlyExecutions: '1K/month',
      fileUploadSizeMB: '50MB',
      apiCallsPerDay: '1K/day'
    },
    enterprise: {
      dailyExecutions: 'Unlimited',
      monthlyExecutions: 'Unlimited',
      fileUploadSizeMB: '500MB',
      apiCallsPerDay: 'Unlimited'
    }
  }

  return limits[tierId]?.[quotaType] || 'Unknown'
}