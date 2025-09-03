/**
 * Tier Pricing Cards Component
 * PIKAR AI Blueprint Compliant Pricing Display
 */

import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { 
  Check, 
  Zap, 
  Rocket, 
  Building, 
  Crown,
  ArrowRight,
  Star,
  Users,
  BarChart3,
  Shield,
  Headphones
} from 'lucide-react'
import { useTier } from '@/hooks/useTier'
import { useAuth } from '@/contexts/AuthContext'
import { paymentService } from '@/services/paymentService'
import { toast } from 'sonner'

const TIER_CONFIGS = [
  {
    id: 'solopreneur',
    name: 'Solopreneur',
    icon: Zap,
    price: { monthly: 99, yearly: 990 },
    description: 'Perfect for individual entrepreneurs',
    color: 'from-blue-500 to-cyan-500',
    popular: false,
    trialDays: 7,
    features: [
      { text: '500 agent executions/month', icon: Zap },
      { text: 'Strategic Planning, Customer Support, Content Creation, Sales Intelligence', icon: BarChart3 },
      { text: 'Advanced analytics & reporting', icon: BarChart3 },
      { text: 'Marketing automation & social scheduling', icon: Rocket },
      { text: 'Custom integrations', icon: Shield },
      { text: 'Email support', icon: Headphones },
      { text: '5GB storage', icon: Building },
      { text: '1 team member', icon: Users }
    ],
    limits: {
      executions: 500,
      teamMembers: 1,
      storage: '5GB',
      support: 'Email'
    }
  },
  {
    id: 'startup',
    name: 'Startup',
    icon: Rocket,
    price: { monthly: 297, yearly: 2970 },
    description: 'Ideal for growing teams',
    color: 'from-purple-500 to-pink-500',
    popular: true,
    trialDays: 7,
    features: [
      { text: '2,000 agent executions/month', icon: Zap },
      { text: 'All agent types available', icon: BarChart3 },
      { text: 'A/B testing & advanced analytics', icon: BarChart3 },
      { text: 'Team collaboration (5 members)', icon: Users },
      { text: 'API access & custom integrations', icon: Shield },
      { text: 'Advanced reporting', icon: BarChart3 },
      { text: 'Priority support', icon: Headphones },
      { text: '25GB storage', icon: Building }
    ],
    limits: {
      executions: 2000,
      teamMembers: 5,
      storage: '25GB',
      support: 'Priority'
    }
  },
  {
    id: 'sme',
    name: 'SME',
    icon: Building,
    price: { monthly: 597, yearly: 5970 },
    description: 'For established businesses',
    color: 'from-green-500 to-emerald-500',
    popular: false,
    trialDays: 7,
    features: [
      { text: '5,000 agent executions/month', icon: Zap },
      { text: 'All features + custom agents', icon: BarChart3 },
      { text: 'White-label options', icon: Shield },
      { text: 'Team collaboration (15 members)', icon: Users },
      { text: 'Custom reports & bulk operations', icon: BarChart3 },
      { text: 'Advanced integrations', icon: Shield },
      { text: 'Priority support', icon: Headphones },
      { text: '100GB storage', icon: Building }
    ],
    limits: {
      executions: 5000,
      teamMembers: 15,
      storage: '100GB',
      support: 'Priority'
    }
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    icon: Crown,
    price: { monthly: 'contact', yearly: 'contact' },
    description: 'For large organizations',
    color: 'from-gray-700 to-gray-900',
    popular: false,
    trialDays: 7,
    features: [
      { text: 'Unlimited agent executions', icon: Zap },
      { text: 'Full white-label solution', icon: Shield },
      { text: 'SSO & advanced security', icon: Shield },
      { text: 'Unlimited team members', icon: Users },
      { text: 'On-premise deployment', icon: Building },
      { text: 'Dedicated support manager', icon: Headphones },
      { text: 'Unlimited storage', icon: Building },
      { text: 'Custom SLA', icon: Star }
    ],
    limits: {
      executions: 'Unlimited',
      teamMembers: 'Unlimited',
      storage: 'Unlimited',
      support: 'Dedicated'
    }
  }
]

export default function TierPricingCards({ showTrialInfo = true, onTierSelect = null }) {
  const { user } = useAuth()
  const { currentTier, startTrial } = useTier()
  const [isYearly, setIsYearly] = useState(false)
  const [isLoading, setIsLoading] = useState(null)

  const handleStartTrial = async (tierId) => {
    if (!user?.id) {
      toast.error('Please log in to start a trial')
      return
    }

    try {
      setIsLoading(tierId)
      
      if (onTierSelect) {
        onTierSelect(tierId)
        return
      }

      await startTrial(user.id, tierId)
      toast.success(`${tierId.charAt(0).toUpperCase() + tierId.slice(1)} trial started!`)
      
    } catch (error) {
      console.error('Failed to start trial:', error)
      toast.error('Failed to start trial')
    } finally {
      setIsLoading(null)
    }
  }

  const handleUpgrade = async (tierId) => {
    if (tierId === 'enterprise') {
      window.open('mailto:sales@pikar-ai.com?subject=Enterprise Upgrade Request', '_blank')
      return
    }

    try {
      setIsLoading(tierId)
      
      const session = await paymentService.createCheckoutSession(
        user.id,
        tierId,
        isYearly ? 'yearly' : 'monthly'
      )
      
      window.location.href = session.url
      
    } catch (error) {
      console.error('Failed to start upgrade:', error)
      toast.error('Failed to start upgrade process')
      setIsLoading(null)
    }
  }

  const getPrice = (tier) => {
    if (tier.price.monthly === 'contact') {
      return 'Contact Sales'
    }
    
    const price = isYearly ? tier.price.yearly : tier.price.monthly
    const period = isYearly ? 'year' : 'month'
    
    return `$${price}/${period}`
  }

  const getSavings = (tier) => {
    if (tier.price.monthly === 'contact') return null
    
    const monthlyTotal = tier.price.monthly * 12
    const yearlySavings = monthlyTotal - tier.price.yearly
    const savingsPercent = Math.round((yearlySavings / monthlyTotal) * 100)
    
    return { amount: yearlySavings, percent: savingsPercent }
  }

  return (
    <div className="space-y-8">
      {/* Billing Toggle */}
      <div className="flex items-center justify-center gap-4">
        <span className={`text-sm ${!isYearly ? 'font-medium' : 'text-gray-500'}`}>
          Monthly
        </span>
        <Switch
          checked={isYearly}
          onCheckedChange={setIsYearly}
          className="data-[state=checked]:bg-blue-600"
        />
        <span className={`text-sm ${isYearly ? 'font-medium' : 'text-gray-500'}`}>
          Yearly
        </span>
        {isYearly && (
          <Badge variant="secondary" className="ml-2">
            Save up to 17%
          </Badge>
        )}
      </div>

      {/* Pricing Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {TIER_CONFIGS.map((tier) => {
          const IconComponent = tier.icon
          const isCurrentTier = currentTier?.id === tier.id
          const savings = getSavings(tier)
          
          return (
            <Card 
              key={tier.id}
              className={`relative overflow-hidden transition-all duration-200 hover:shadow-lg ${
                tier.popular ? 'ring-2 ring-blue-500 scale-105' : ''
              } ${isCurrentTier ? 'ring-2 ring-green-500' : ''}`}
            >
              {tier.popular && (
                <div className="absolute top-0 left-0 right-0 bg-gradient-to-r from-blue-500 to-purple-500 text-white text-center py-1 text-xs font-medium">
                  Most Popular
                </div>
              )}
              
              {isCurrentTier && (
                <div className="absolute top-0 left-0 right-0 bg-gradient-to-r from-green-500 to-emerald-500 text-white text-center py-1 text-xs font-medium">
                  Current Plan
                </div>
              )}

              <CardHeader className={`${tier.popular || isCurrentTier ? 'pt-8' : 'pt-6'}`}>
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg bg-gradient-to-r ${tier.color}`}>
                    <IconComponent className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <CardTitle className="text-xl">{tier.name}</CardTitle>
                    <CardDescription className="text-sm">
                      {tier.description}
                    </CardDescription>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-3xl font-bold">
                    {getPrice(tier)}
                  </div>
                  {isYearly && savings && (
                    <div className="text-sm text-green-600 font-medium">
                      Save ${savings.amount}/year ({savings.percent}% off)
                    </div>
                  )}
                  {showTrialInfo && (
                    <div className="text-sm text-blue-600">
                      {tier.trialDays}-day free trial
                    </div>
                  )}
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Key Metrics */}
                <div className="grid grid-cols-2 gap-2 p-3 bg-gray-50 rounded-lg text-xs">
                  <div>
                    <div className="font-medium text-gray-600">Executions</div>
                    <div className="font-semibold">{tier.limits.executions}</div>
                  </div>
                  <div>
                    <div className="font-medium text-gray-600">Team Size</div>
                    <div className="font-semibold">{tier.limits.teamMembers}</div>
                  </div>
                  <div>
                    <div className="font-medium text-gray-600">Storage</div>
                    <div className="font-semibold">{tier.limits.storage}</div>
                  </div>
                  <div>
                    <div className="font-medium text-gray-600">Support</div>
                    <div className="font-semibold">{tier.limits.support}</div>
                  </div>
                </div>

                {/* Features List */}
                <div className="space-y-2">
                  {tier.features.slice(0, 6).map((feature, index) => {
                    const FeatureIcon = feature.icon
                    return (
                      <div key={index} className="flex items-center gap-2 text-sm">
                        <FeatureIcon className="h-4 w-4 text-green-500 flex-shrink-0" />
                        <span>{feature.text}</span>
                      </div>
                    )
                  })}
                  {tier.features.length > 6 && (
                    <div className="text-xs text-gray-500">
                      +{tier.features.length - 6} more features
                    </div>
                  )}
                </div>

                {/* Action Button */}
                <div className="pt-4">
                  {isCurrentTier ? (
                    <Button variant="outline" className="w-full" disabled>
                      <Check className="h-4 w-4 mr-2" />
                      Current Plan
                    </Button>
                  ) : (
                    <Button 
                      className="w-full"
                      onClick={() => handleStartTrial(tier.id)}
                      disabled={isLoading === tier.id}
                      variant={tier.popular ? 'default' : 'outline'}
                    >
                      {isLoading === tier.id ? (
                        'Starting...'
                      ) : (
                        <>
                          Start {tier.trialDays}-Day Trial
                          <ArrowRight className="h-4 w-4 ml-2" />
                        </>
                      )}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Feature Comparison Note */}
      <div className="text-center text-sm text-gray-600 max-w-2xl mx-auto">
        All plans include full access during the 7-day trial period. No credit card required to start your trial.
        Cancel anytime during the trial with no charges.
      </div>
    </div>
  )
}
