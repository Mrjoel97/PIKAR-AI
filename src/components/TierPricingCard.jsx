/**
 * Tier Pricing Card Component
 * Enhanced pricing card with tier management integration
 */

import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Check, X, Crown, Zap, Star, TrendingUp, Users, Cpu, Database, Mail } from 'lucide-react'
import { motion } from 'framer-motion'
import { useTier } from '@/hooks/useTier'
import { toast } from 'sonner'

const TIER_ICONS = {
  free: Star,
  pro: Zap,
  enterprise: Crown
}

const TIER_GRADIENTS = {
  free: 'from-gray-400 to-gray-600',
  pro: 'from-blue-500 to-blue-700',
  enterprise: 'from-purple-500 to-purple-700'
}

export default function TierPricingCard({
  tier,
  isCurrentTier = false,
  onSelect,
  className = '',
  showUsage = false,
  showComparison = false,
  annual = false
}) {
  const {
    currentTier,
    usage,
    getUsagePercentage,
    upgradeTier,
    downgradeTier,
    isLoading
  } = useTier()

  if (!tier) return null

  const { id, name, price, billingPeriod, features, limits } = tier
  const IconComponent = TIER_ICONS[id] || Star
  const gradient = TIER_GRADIENTS[id] || 'from-gray-400 to-gray-600'

  // Calculate pricing
  const displayPrice = annual && billingPeriod === 'monthly' ? price * 10 : price
  const monthlyPrice = annual ? displayPrice / 12 : price
  const savings = annual && billingPeriod === 'monthly' ? price * 2 : 0

  const handleSelect = async () => {
    if (isCurrentTier || isLoading) return

    try {
      if (onSelect) {
        onSelect(tier)
      } else {
        // Default upgrade/downgrade logic
        if (currentTier && price > currentTier.price) {
          toast.info(`Upgrading to ${name}...`)
          // await upgradeTier(id, billingInfo)
        } else if (currentTier && price < currentTier.price) {
          toast.info(`Downgrading to ${name}...`)
          // await downgradeTier(id)
        }
      }
    } catch (error) {
      toast.error('Failed to change tier. Please try again.')
    }
  }

  const getFeatureList = () => {
    const featureList = []

    // Agent types
    if (features.agentTypes === 'all') {
      featureList.push('All AI agent types')
    } else if (Array.isArray(features.agentTypes)) {
      featureList.push(`${features.agentTypes.length} AI agent types`)
    }

    // Executions
    if (features.maxAgentExecutions === 'unlimited') {
      featureList.push('Unlimited agent executions')
    } else {
      featureList.push(`${features.maxAgentExecutions} monthly executions`)
    }

    // Team members
    if (features.maxTeamMembers === 'unlimited') {
      featureList.push('Unlimited team members')
    } else {
      featureList.push(`${features.maxTeamMembers} team member${features.maxTeamMembers > 1 ? 's' : ''}`)
    }

    // Projects
    if (features.maxProjects === 'unlimited') {
      featureList.push('Unlimited projects')
    } else {
      featureList.push(`${features.maxProjects} projects`)
    }

    // Storage
    if (features.maxStorageGB === 'unlimited') {
      featureList.push('Unlimited storage')
    } else {
      featureList.push(`${features.maxStorageGB}GB storage`)
    }

    // Support
    featureList.push(`${features.supportLevel} support`)

    // Advanced features
    if (features.advancedAnalytics) featureList.push('Advanced analytics')
    if (features.customIntegrations) featureList.push('Custom integrations')
    if (features.apiAccess) featureList.push('API access')
    if (features.abTesting) featureList.push('A/B testing')
    if (features.marketingAutomation) featureList.push('Marketing automation')
    if (features.whiteLabel) featureList.push('White-label options')
    if (features.customAgents) featureList.push('Custom agent development')
    if (features.dedicatedManager) featureList.push('Dedicated account manager')

    return featureList
  }

  const getLimitations = () => {
    const limitations = []

    if (id === 'free') {
      limitations.push('Limited to basic agents only')
      limitations.push('No custom integrations')
      limitations.push('Community support only')
      limitations.push('Basic analytics only')
    }

    if (id === 'pro') {
      limitations.push('No white-label options')
      limitations.push('No custom agent development')
    }

    return limitations
  }

  const getUsageStats = () => {
    if (!showUsage || !usage || !isCurrentTier) return null

    return [
      {
        label: 'Monthly Executions',
        current: usage.monthlyExecutions || 0,
        limit: limits.monthlyExecutions,
        percentage: getUsagePercentage('monthlyExecutions')
      },
      {
        label: 'Storage Used',
        current: usage.fileUploadSizeMB || 0,
        limit: limits.fileUploadSizeMB,
        percentage: getUsagePercentage('fileUploadSizeMB')
      }
    ]
  }

  const featureList = getFeatureList()
  const limitations = getLimitations()
  const usageStats = getUsageStats()

  return (
    <motion.div
      whileHover={{ y: isCurrentTier ? 0 : -8, scale: isCurrentTier ? 1 : 1.02 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className={className}
    >
      <Card className={`relative h-full transition-all duration-200 hover:shadow-lg ${
        isCurrentTier ? 'ring-2 ring-blue-500 shadow-lg' : ''
      } ${id === 'pro' ? 'border-blue-500 shadow-md' : ''}`}>

        {/* Popular badge */}
        {id === 'pro' && (
          <Badge className="absolute -top-2 left-1/2 transform -translate-x-1/2 bg-blue-500">
            Most Popular
          </Badge>
        )}

        {/* Current tier badge */}
        {isCurrentTier && (
          <Badge className="absolute -top-2 right-4 bg-green-500">
            Current Plan
          </Badge>
        )}

        <CardHeader className="text-center pb-4">
          {/* Icon */}
          <div className={`mx-auto w-12 h-12 bg-gradient-to-br ${gradient} rounded-full flex items-center justify-center mb-3`}>
            <IconComponent className="w-6 h-6 text-white" />
          </div>

          {/* Tier name */}
          <CardTitle className="text-2xl font-bold">{name}</CardTitle>

          {/* Pricing */}
          <div className="space-y-1">
            <div className="text-4xl font-bold">
              {price === 0 ? 'Free' : (
                <>
                  ${annual ? Math.round(monthlyPrice) : price}
                  <span className="text-lg font-normal text-gray-500">
                    /{annual ? 'mo' : billingPeriod.slice(0, -2)}
                  </span>
                </>
              )}
            </div>

            {annual && savings > 0 && (
              <div className="text-sm text-green-600 font-medium">
                Save ${savings}/year
              </div>
            )}

            {annual && price > 0 && (
              <div className="text-xs text-gray-500">
                Billed annually (${displayPrice}/year)
              </div>
            )}
          </div>

          <CardDescription className="text-sm">
            {id === 'free' && 'Perfect for getting started'}
            {id === 'pro' && 'Best for growing businesses'}
            {id === 'enterprise' && 'For large organizations'}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Usage statistics for current tier */}
          {usageStats && (
            <div className="space-y-3">
              <h4 className="font-semibold text-sm text-gray-700">Current Usage</h4>
              {usageStats.map((stat, index) => (
                <div key={index} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span>{stat.label}</span>
                    <span>
                      {stat.current} / {stat.limit === 'unlimited' ? '∞' : stat.limit}
                    </span>
                  </div>
                  <Progress
                    value={stat.limit === 'unlimited' ? 0 : stat.percentage}
                    className="h-1.5"
                  />
                </div>
              ))}
            </div>
          )}

          {/* Features */}
          <div className="space-y-3">
            <h4 className="font-semibold text-sm text-green-700 flex items-center">
              <Check className="w-4 h-4 mr-1" />
              What's included:
            </h4>
            <ul className="space-y-2">
              {featureList.map((feature, index) => (
                <li key={index} className="flex items-start text-sm">
                  <Check className="w-4 h-4 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Limitations */}
          {limitations.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-semibold text-sm text-red-700 flex items-center">
                <X className="w-4 h-4 mr-1" />
                Limitations:
              </h4>
              <ul className="space-y-2">
                {limitations.map((limitation, index) => (
                  <li key={index} className="flex items-start text-sm text-gray-600">
                    <X className="w-4 h-4 text-red-500 mr-2 mt-0.5 flex-shrink-0" />
                    <span>{limitation}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Key metrics */}
          <div className="grid grid-cols-3 gap-2 pt-2 border-t">
            <div className="text-center">
              <div className="flex items-center justify-center mb-1">
                <Cpu className="w-4 h-4 text-gray-500" />
              </div>
              <div className="text-xs font-medium">
                {limits.concurrentExecutions === 'unlimited' ? '∞' : limits.concurrentExecutions}
              </div>
              <div className="text-xs text-gray-500">Concurrent</div>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center mb-1">
                <Users className="w-4 h-4 text-gray-500" />
              </div>
              <div className="text-xs font-medium">
                {features.maxTeamMembers === 'unlimited' ? '∞' : features.maxTeamMembers}
              </div>
              <div className="text-xs text-gray-500">Team</div>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center mb-1">
                <Database className="w-4 h-4 text-gray-500" />
              </div>
              <div className="text-xs font-medium">
                {features.maxStorageGB === 'unlimited' ? '∞' : `${features.maxStorageGB}GB`}
              </div>
              <div className="text-xs text-gray-500">Storage</div>
            </div>
          </div>

          {/* Action button */}
          <Button
            onClick={handleSelect}
            className={`w-full ${
              isCurrentTier
                ? 'bg-gray-400 cursor-not-allowed'
                : id === 'pro'
                  ? 'bg-blue-600 hover:bg-blue-700'
                  : id === 'enterprise'
                    ? 'bg-purple-600 hover:bg-purple-700'
                    : 'bg-gray-600 hover:bg-gray-700'
            }`}
            disabled={isCurrentTier || isLoading}
          >
            {isLoading ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Processing...
              </div>
            ) : isCurrentTier ? (
              'Current Plan'
            ) : currentTier && price > currentTier.price ? (
              <>
                <TrendingUp className="w-4 h-4 mr-2" />
                Upgrade to {name}
              </>
            ) : currentTier && price < currentTier.price ? (
              `Downgrade to ${name}`
            ) : id === 'enterprise' ? (
              <>
                <Mail className="w-4 h-4 mr-2" />
                Contact Sales
              </>
            ) : (
              `Choose ${name}`
            )}
          </Button>

          {/* Additional info */}
          {price > 0 && (
            <p className="text-xs text-center text-gray-500">
              {annual ? 'Billed annually' : 'Billed monthly'} • Cancel anytime
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}