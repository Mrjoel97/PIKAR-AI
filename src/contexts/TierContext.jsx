/**
 * Tier Context
 * React context for managing user tier state and tier-related operations
 */

import React, { createContext, useContext, useReducer, useEffect } from 'react'
import { tierService } from '@/services/tierService'
import { useAuth } from './AuthContext'
import { toast } from 'sonner'

// Initial state
const initialState = {
  currentTier: null,
  usage: null,
  upgradeOptions: [],
  isLoading: false,
  error: null,
  quotaWarnings: [],
  billingInfo: null
}

// Action types
const TIER_ACTIONS = {
  SET_LOADING: 'SET_LOADING',
  SET_TIER: 'SET_TIER',
  SET_USAGE: 'SET_USAGE',
  SET_UPGRADE_OPTIONS: 'SET_UPGRADE_OPTIONS',
  SET_ERROR: 'SET_ERROR',
  ADD_QUOTA_WARNING: 'ADD_QUOTA_WARNING',
  CLEAR_QUOTA_WARNINGS: 'CLEAR_QUOTA_WARNINGS',
  SET_BILLING_INFO: 'SET_BILLING_INFO',
  RESET_STATE: 'RESET_STATE'
}

// Reducer
function tierReducer(state, action) {
  switch (action.type) {
    case TIER_ACTIONS.SET_LOADING:
      return { ...state, isLoading: action.payload }
    
    case TIER_ACTIONS.SET_TIER:
      return { ...state, currentTier: action.payload, error: null }
    
    case TIER_ACTIONS.SET_USAGE:
      return { ...state, usage: action.payload }
    
    case TIER_ACTIONS.SET_UPGRADE_OPTIONS:
      return { ...state, upgradeOptions: action.payload }
    
    case TIER_ACTIONS.SET_ERROR:
      return { ...state, error: action.payload, isLoading: false }
    
    case TIER_ACTIONS.ADD_QUOTA_WARNING:
      return { 
        ...state, 
        quotaWarnings: [...state.quotaWarnings, action.payload] 
      }
    
    case TIER_ACTIONS.CLEAR_QUOTA_WARNINGS:
      return { ...state, quotaWarnings: [] }
    
    case TIER_ACTIONS.SET_BILLING_INFO:
      return { ...state, billingInfo: action.payload }
    
    case TIER_ACTIONS.RESET_STATE:
      return initialState
    
    default:
      return state
  }
}

// Create context
const TierContext = createContext()

// Provider component
export function TierProvider({ children }) {
  const [state, dispatch] = useReducer(tierReducer, initialState)
  const { user } = useAuth()

  // Load user tier data on mount and user change
  useEffect(() => {
    if (user?.id) {
      loadUserTierData()
    } else {
      dispatch({ type: TIER_ACTIONS.RESET_STATE })
    }
  }, [user?.id])

  // Load user tier data
  const loadUserTierData = async () => {
    try {
      dispatch({ type: TIER_ACTIONS.SET_LOADING, payload: true })
      
      // Get current tier
      const currentTier = tierService.getUserTier(user.id)
      dispatch({ type: TIER_ACTIONS.SET_TIER, payload: currentTier })
      
      // Get usage statistics
      const usage = tierService.getUserUsage(user.id)
      dispatch({ type: TIER_ACTIONS.SET_USAGE, payload: usage })
      
      // Get upgrade options
      const upgradeOptions = tierService.getUpgradeOptions(user.id)
      dispatch({ type: TIER_ACTIONS.SET_UPGRADE_OPTIONS, payload: upgradeOptions })
      
      // Check for quota warnings
      checkQuotaWarnings(currentTier, usage)
      
    } catch (error) {
      console.error('Failed to load tier data:', error)
      dispatch({ type: TIER_ACTIONS.SET_ERROR, payload: error.message })
      toast.error('Failed to load tier information')
    } finally {
      dispatch({ type: TIER_ACTIONS.SET_LOADING, payload: false })
    }
  }

  // Check for quota warnings
  const checkQuotaWarnings = (tier, usage) => {
    const warnings = []
    
    for (const [limit, value] of Object.entries(tier.limits)) {
      if (value !== 'unlimited' && usage[limit]) {
        const usagePercentage = (usage[limit] / value) * 100
        
        if (usagePercentage >= 90) {
          warnings.push({
            type: 'critical',
            limit,
            usage: usage[limit],
            total: value,
            percentage: usagePercentage,
            message: `You've used ${Math.round(usagePercentage)}% of your ${limit} quota`
          })
        } else if (usagePercentage >= 75) {
          warnings.push({
            type: 'warning',
            limit,
            usage: usage[limit],
            total: value,
            percentage: usagePercentage,
            message: `You've used ${Math.round(usagePercentage)}% of your ${limit} quota`
          })
        }
      }
    }
    
    if (warnings.length > 0) {
      warnings.forEach(warning => {
        dispatch({ type: TIER_ACTIONS.ADD_QUOTA_WARNING, payload: warning })
        
        if (warning.type === 'critical') {
          toast.error(warning.message)
        } else {
          toast.warning(warning.message)
        }
      })
    }
  }

  // Check if user has feature access
  const hasFeatureAccess = (feature) => {
    if (!user?.id || !state.currentTier) return false
    return tierService.hasFeatureAccess(user.id, feature)
  }

  // Check if user can perform action
  const canPerformAction = async (action, amount = 1) => {
    if (!user?.id) return { allowed: false, reason: 'Not authenticated' }
    
    try {
      return await tierService.canPerformAction(user.id, action, amount)
    } catch (error) {
      return { allowed: false, reason: error.message }
    }
  }

  // Track usage
  const trackUsage = async (action, amount = 1) => {
    if (!user?.id) throw new Error('Not authenticated')
    
    try {
      const result = await tierService.trackUsage(user.id, action, amount)
      
      // Update usage in state
      const updatedUsage = { ...state.usage }
      updatedUsage[action] = result.newUsage
      updatedUsage.lastUpdated = Date.now()
      dispatch({ type: TIER_ACTIONS.SET_USAGE, payload: updatedUsage })
      
      // Check for new quota warnings
      if (state.currentTier) {
        checkQuotaWarnings(state.currentTier, updatedUsage)
      }
      
      return result
    } catch (error) {
      toast.error(error.message)
      throw error
    }
  }

  // Upgrade tier
  const upgradeTier = async (newTierId, billingInfo) => {
    if (!user?.id) throw new Error('Not authenticated')
    
    try {
      dispatch({ type: TIER_ACTIONS.SET_LOADING, payload: true })
      
      const result = await tierService.upgradeTier(user.id, newTierId, billingInfo)
      
      if (result.success) {
        // Update tier in state
        dispatch({ type: TIER_ACTIONS.SET_TIER, payload: result.newTier })
        
        // Update billing info
        dispatch({ type: TIER_ACTIONS.SET_BILLING_INFO, payload: billingInfo })
        
        // Reload tier data
        await loadUserTierData()
        
        toast.success(`Successfully upgraded to ${result.newTier.name}!`)
        
        return result
      }
    } catch (error) {
      console.error('Tier upgrade failed:', error)
      dispatch({ type: TIER_ACTIONS.SET_ERROR, payload: error.message })
      toast.error(`Upgrade failed: ${error.message}`)
      throw error
    } finally {
      dispatch({ type: TIER_ACTIONS.SET_LOADING, payload: false })
    }
  }

  // Downgrade tier
  const downgradeTier = async (newTierId) => {
    if (!user?.id) throw new Error('Not authenticated')
    
    try {
      dispatch({ type: TIER_ACTIONS.SET_LOADING, payload: true })
      
      const result = await tierService.downgradeTier(user.id, newTierId)
      
      if (result.success) {
        // Update tier in state
        dispatch({ type: TIER_ACTIONS.SET_TIER, payload: result.newTier })
        
        // Reload tier data
        await loadUserTierData()
        
        toast.success(`Successfully downgraded to ${result.newTier.name}`)
        
        if (result.refundAmount > 0) {
          toast.info(`Refund of $${result.refundAmount} will be processed`)
        }
        
        return result
      }
    } catch (error) {
      console.error('Tier downgrade failed:', error)
      dispatch({ type: TIER_ACTIONS.SET_ERROR, payload: error.message })
      toast.error(`Downgrade failed: ${error.message}`)
      throw error
    } finally {
      dispatch({ type: TIER_ACTIONS.SET_LOADING, payload: false })
    }
  }

  // Get usage percentage for a limit
  const getUsagePercentage = (limit) => {
    if (!state.currentTier || !state.usage) return 0
    
    const tierLimit = state.currentTier.limits[limit]
    const currentUsage = state.usage[limit] || 0
    
    if (tierLimit === 'unlimited') return 0
    if (tierLimit === 0) return 100
    
    return Math.min(100, (currentUsage / tierLimit) * 100)
  }

  // Get remaining quota for a limit
  const getRemainingQuota = (limit) => {
    if (!state.currentTier || !state.usage) return 0
    
    const tierLimit = state.currentTier.limits[limit]
    const currentUsage = state.usage[limit] || 0
    
    if (tierLimit === 'unlimited') return 'unlimited'
    
    return Math.max(0, tierLimit - currentUsage)
  }

  // Clear quota warnings
  const clearQuotaWarnings = () => {
    dispatch({ type: TIER_ACTIONS.CLEAR_QUOTA_WARNINGS })
  }

  // Refresh tier data
  const refreshTierData = async () => {
    if (user?.id) {
      await loadUserTierData()
    }
  }

  // Context value
  const value = {
    // State
    currentTier: state.currentTier,
    usage: state.usage,
    upgradeOptions: state.upgradeOptions,
    isLoading: state.isLoading,
    error: state.error,
    quotaWarnings: state.quotaWarnings,
    billingInfo: state.billingInfo,
    
    // Actions
    hasFeatureAccess,
    canPerformAction,
    trackUsage,
    upgradeTier,
    downgradeTier,
    getUsagePercentage,
    getRemainingQuota,
    clearQuotaWarnings,
    refreshTierData,
    
    // Utilities
    isFreeTier: state.currentTier?.id === 'free',
    isProTier: state.currentTier?.id === 'pro',
    isEnterpriseTier: state.currentTier?.id === 'enterprise'
  }

  return (
    <TierContext.Provider value={value}>
      {children}
    </TierContext.Provider>
  )
}

// Hook to use tier context
export function useTier() {
  const context = useContext(TierContext)
  
  if (!context) {
    throw new Error('useTier must be used within a TierProvider')
  }
  
  return context
}

// HOC for tier-gated components
export function withTierAccess(WrappedComponent, requiredFeature) {
  return function TierGatedComponent(props) {
    const { hasFeatureAccess, currentTier, isLoading } = useTier()
    
    if (isLoading) {
      return <div className="flex items-center justify-center p-8">Loading...</div>
    }
    
    if (!hasFeatureAccess(requiredFeature)) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <h3 className="text-lg font-semibold mb-2">Feature Not Available</h3>
          <p className="text-gray-600 mb-4">
            This feature requires a {requiredFeature} subscription.
          </p>
          <p className="text-sm text-gray-500">
            Current tier: {currentTier?.name || 'Unknown'}
          </p>
        </div>
      )
    }
    
    return <WrappedComponent {...props} />
  }
}
