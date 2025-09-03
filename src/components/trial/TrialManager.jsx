/**
 * Trial Manager Component
 * Handles 7-day trial experience with countdown and upgrade prompts
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Clock, 
  CreditCard, 
  AlertTriangle, 
  CheckCircle, 
  Zap,
  ArrowRight,
  Calendar
} from 'lucide-react'
import { useTier } from '@/hooks/useTier'
import { useAuth } from '@/contexts/AuthContext'
import { paymentService } from '@/services/paymentService'
import { toast } from 'sonner'

export default function TrialManager({ showInline = false, className = '' }) {
  const { user } = useAuth()
  const { currentTier, isUserInTrial, getTrialDaysRemaining } = useTier()
  const [trialInfo, setTrialInfo] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadTrialInfo()
  }, [user?.id])

  const loadTrialInfo = async () => {
    if (!user?.id) return

    try {
      setIsLoading(true)
      
      const inTrial = isUserInTrial(user.id)
      const daysRemaining = getTrialDaysRemaining(user.id)
      
      setTrialInfo({
        isInTrial: inTrial,
        daysRemaining: daysRemaining,
        tier: currentTier,
        trialStarted: inTrial,
        hasPaymentMethod: false // Would check actual payment method
      })
      
    } catch (error) {
      console.error('Failed to load trial info:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleUpgrade = async () => {
    try {
      if (currentTier?.id === 'enterprise') {
        // Redirect to contact sales
        window.open('mailto:sales@pikar-ai.com?subject=Enterprise Upgrade Request', '_blank')
        return
      }

      const session = await paymentService.createCheckoutSession(
        user.id,
        currentTier?.id,
        'monthly'
      )
      
      window.location.href = session.url
      
    } catch (error) {
      console.error('Failed to start upgrade:', error)
      toast.error('Failed to start upgrade process')
    }
  }

  const getTrialStatus = () => {
    if (!trialInfo?.isInTrial) return 'expired'
    if (trialInfo.daysRemaining <= 1) return 'urgent'
    if (trialInfo.daysRemaining <= 3) return 'warning'
    return 'active'
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'expired': return 'text-red-600 bg-red-50 border-red-200'
      case 'urgent': return 'text-red-600 bg-red-50 border-red-200'
      case 'warning': return 'text-orange-600 bg-orange-50 border-orange-200'
      case 'active': return 'text-blue-600 bg-blue-50 border-blue-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getProgressPercentage = () => {
    if (!trialInfo?.isInTrial) return 100
    const totalDays = 7
    const elapsed = totalDays - trialInfo.daysRemaining
    return (elapsed / totalDays) * 100
  }

  if (isLoading) {
    return (
      <div className={`animate-pulse ${className}`}>
        <div className="h-24 bg-gray-200 rounded"></div>
      </div>
    )
  }

  if (!trialInfo?.isInTrial && !showInline) {
    return null // Don't show if not in trial and not forced inline
  }

  const status = getTrialStatus()
  const statusColor = getStatusColor(status)
  const progressPercentage = getProgressPercentage()

  if (showInline) {
    return (
      <Alert className={`${statusColor} ${className}`}>
        <Clock className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {currentTier?.name} Trial
            </Badge>
            <span>
              {trialInfo?.isInTrial 
                ? `${trialInfo.daysRemaining} day${trialInfo.daysRemaining !== 1 ? 's' : ''} remaining`
                : 'Trial expired'
              }
            </span>
          </div>
          <Button size="sm" onClick={handleUpgrade}>
            Upgrade Now
          </Button>
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <Card className={`${statusColor} ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            <CardTitle className="text-lg">
              {currentTier?.name} Trial
            </CardTitle>
          </div>
          <Badge variant={status === 'expired' ? 'destructive' : 'secondary'}>
            {trialInfo?.isInTrial ? 'Active' : 'Expired'}
          </Badge>
        </div>
        <CardDescription>
          {trialInfo?.isInTrial 
            ? `Full access to ${currentTier?.name} features`
            : 'Trial period has ended'
          }
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Trial Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Trial Progress</span>
            <span>
              {trialInfo?.isInTrial 
                ? `Day ${7 - trialInfo.daysRemaining + 1} of 7`
                : 'Completed'
              }
            </span>
          </div>
          <Progress value={progressPercentage} className="h-2" />
        </div>

        {/* Days Remaining */}
        <div className="flex items-center justify-between p-3 bg-white/50 rounded-lg">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            <span className="font-medium">
              {trialInfo?.isInTrial 
                ? `${trialInfo.daysRemaining} day${trialInfo.daysRemaining !== 1 ? 's' : ''} remaining`
                : 'Trial ended'
              }
            </span>
          </div>
          {status === 'urgent' && (
            <AlertTriangle className="h-4 w-4 text-red-500" />
          )}
        </div>

        {/* Feature Access */}
        <div className="space-y-2">
          <h4 className="font-medium text-sm">Current Access:</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center gap-1">
              <CheckCircle className="h-3 w-3 text-green-500" />
              <span>All {currentTier?.name} features</span>
            </div>
            <div className="flex items-center gap-1">
              <CheckCircle className="h-3 w-3 text-green-500" />
              <span>{currentTier?.limits?.monthlyExecutions} executions</span>
            </div>
            <div className="flex items-center gap-1">
              <CheckCircle className="h-3 w-3 text-green-500" />
              <span>{currentTier?.features?.maxTeamMembers} team member{currentTier?.features?.maxTeamMembers !== 1 ? 's' : ''}</span>
            </div>
            <div className="flex items-center gap-1">
              <CheckCircle className="h-3 w-3 text-green-500" />
              <span>{currentTier?.supportLevel} support</span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          <Button 
            onClick={handleUpgrade} 
            className="flex-1"
            variant={status === 'expired' ? 'default' : 'outline'}
          >
            <CreditCard className="h-4 w-4 mr-2" />
            {currentTier?.id === 'enterprise' ? 'Contact Sales' : `Upgrade to ${currentTier?.name}`}
          </Button>
          
          {trialInfo?.isInTrial && (
            <Button variant="ghost" size="sm">
              <Zap className="h-4 w-4 mr-1" />
              Explore Features
              <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          )}
        </div>

        {/* Pricing Info */}
        {currentTier?.price !== 'contact_sales' && (
          <div className="text-center text-xs text-gray-600 pt-2 border-t">
            Starting at ${currentTier?.price}/month after trial
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Trial Status Indicator for Navigation
export function TrialStatusIndicator() {
  const { user } = useAuth()
  const { isUserInTrial, getTrialDaysRemaining } = useTier()
  
  const inTrial = isUserInTrial(user?.id)
  const daysRemaining = getTrialDaysRemaining(user?.id)
  
  if (!inTrial) return null
  
  const isUrgent = daysRemaining <= 1
  
  return (
    <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
      isUrgent ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
    }`}>
      <Clock className="h-3 w-3" />
      <span>{daysRemaining}d left</span>
    </div>
  )
}

// Trial Expired Modal
export function TrialExpiredModal({ isOpen, onClose }) {
  const { currentTier } = useTier()
  
  if (!isOpen) return null
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="w-full max-w-md mx-4">
        <CardHeader className="text-center">
          <div className="mx-auto w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <AlertTriangle className="h-6 w-6 text-red-600" />
          </div>
          <CardTitle>Trial Expired</CardTitle>
          <CardDescription>
            Your 7-day {currentTier?.name} trial has ended. Upgrade now to continue using PIKAR AI.
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          <Button className="w-full" size="lg">
            <CreditCard className="h-4 w-4 mr-2" />
            {currentTier?.id === 'enterprise' ? 'Contact Sales' : `Upgrade to ${currentTier?.name}`}
          </Button>
          
          <Button variant="outline" className="w-full" onClick={onClose}>
            Browse Plans
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
