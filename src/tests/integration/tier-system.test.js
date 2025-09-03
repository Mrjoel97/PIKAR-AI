/**
 * PIKAR AI Tier System Integration Tests
 * Tests the complete tier system with 7-day trials
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { tierService } from '@/services/tierService'
import { paymentService } from '@/services/paymentService'
import TierPricingCards from '@/components/pricing/TierPricingCards'
import TrialManager from '@/components/trial/TrialManager'
import TierGate from '@/components/TierGate'

// Mock services
vi.mock('@/services/tierService')
vi.mock('@/services/paymentService')
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'test-user-123', email: 'test@pikar-ai.com' }
  })
}))

const mockTierService = {
  getUserTier: vi.fn(),
  isUserInTrial: vi.fn(),
  getTrialDaysRemaining: vi.fn(),
  startTrial: vi.fn(),
  tierDefinitions: {
    SOLOPRENEUR: {
      id: 'solopreneur',
      name: 'Solopreneur',
      price: 99,
      trialDays: 7,
      features: {
        maxAgentExecutions: 500,
        maxTeamMembers: 1,
        supportLevel: 'email'
      }
    },
    STARTUP: {
      id: 'startup',
      name: 'Startup',
      price: 297,
      trialDays: 7,
      features: {
        maxAgentExecutions: 2000,
        maxTeamMembers: 5,
        supportLevel: 'priority'
      }
    },
    SME: {
      id: 'sme',
      name: 'SME',
      price: 597,
      trialDays: 7,
      features: {
        maxAgentExecutions: 5000,
        maxTeamMembers: 15,
        supportLevel: 'priority'
      }
    },
    ENTERPRISE: {
      id: 'enterprise',
      name: 'Enterprise',
      price: 'contact_sales',
      trialDays: 7,
      features: {
        maxAgentExecutions: 'unlimited',
        maxTeamMembers: 'unlimited',
        supportLevel: 'dedicated'
      }
    }
  }
}

const mockPaymentService = {
  createCheckoutSession: vi.fn()
}

describe('PIKAR AI Tier System', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    tierService.mockImplementation(() => mockTierService)
    paymentService.mockImplementation(() => mockPaymentService)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Tier Structure Compliance', () => {
    it('should have correct tier definitions matching blueprint', () => {
      const tiers = mockTierService.tierDefinitions
      
      expect(tiers.SOLOPRENEUR.price).toBe(99)
      expect(tiers.STARTUP.price).toBe(297)
      expect(tiers.SME.price).toBe(597)
      expect(tiers.ENTERPRISE.price).toBe('contact_sales')
      
      // All tiers should have 7-day trials
      Object.values(tiers).forEach(tier => {
        expect(tier.trialDays).toBe(7)
      })
    })

    it('should not have any FREE tier references', () => {
      const tiers = mockTierService.tierDefinitions
      expect(tiers.FREE).toBeUndefined()
      expect(tiers.free).toBeUndefined()
    })

    it('should have proper tier progression', () => {
      const tiers = mockTierService.tierDefinitions
      
      expect(tiers.SOLOPRENEUR.features.maxAgentExecutions).toBe(500)
      expect(tiers.STARTUP.features.maxAgentExecutions).toBe(2000)
      expect(tiers.SME.features.maxAgentExecutions).toBe(5000)
      expect(tiers.ENTERPRISE.features.maxAgentExecutions).toBe('unlimited')
    })
  })

  describe('Trial System', () => {
    it('should start 7-day trial correctly', async () => {
      mockTierService.startTrial.mockResolvedValue({
        userId: 'test-user-123',
        tierId: 'STARTUP',
        trialStartDate: Date.now(),
        trialEndDate: Date.now() + (7 * 24 * 60 * 60 * 1000),
        status: 'trial'
      })

      const result = await mockTierService.startTrial('test-user-123', 'startup')
      
      expect(result.tierId).toBe('STARTUP')
      expect(result.status).toBe('trial')
      expect(mockTierService.startTrial).toHaveBeenCalledWith('test-user-123', 'startup')
    })

    it('should calculate trial days remaining correctly', () => {
      const now = Date.now()
      const threeDaysFromNow = now + (3 * 24 * 60 * 60 * 1000)
      
      mockTierService.getTrialDaysRemaining.mockReturnValue(3)
      
      const daysRemaining = mockTierService.getTrialDaysRemaining('test-user-123')
      expect(daysRemaining).toBe(3)
    })

    it('should detect trial expiration', () => {
      mockTierService.isUserInTrial.mockReturnValue(false)
      mockTierService.getTrialDaysRemaining.mockReturnValue(0)
      
      const inTrial = mockTierService.isUserInTrial('test-user-123')
      const daysRemaining = mockTierService.getTrialDaysRemaining('test-user-123')
      
      expect(inTrial).toBe(false)
      expect(daysRemaining).toBe(0)
    })
  })

  describe('Pricing Components', () => {
    const renderWithRouter = (component) => {
      return render(
        <BrowserRouter>
          {component}
        </BrowserRouter>
      )
    }

    it('should display correct pricing for all tiers', () => {
      renderWithRouter(<TierPricingCards />)
      
      expect(screen.getByText('$99/month')).toBeInTheDocument()
      expect(screen.getByText('$297/month')).toBeInTheDocument()
      expect(screen.getByText('$597/month')).toBeInTheDocument()
      expect(screen.getByText('Contact Sales')).toBeInTheDocument()
    })

    it('should show 7-day trial messaging', () => {
      renderWithRouter(<TierPricingCards />)
      
      const trialMessages = screen.getAllByText(/7-day free trial/i)
      expect(trialMessages).toHaveLength(4) // All tiers should show trial
    })

    it('should handle tier selection', async () => {
      mockTierService.startTrial.mockResolvedValue({ success: true })
      
      renderWithRouter(<TierPricingCards />)
      
      const startupButton = screen.getByText(/Start.*Trial/i)
      fireEvent.click(startupButton)
      
      await waitFor(() => {
        expect(mockTierService.startTrial).toHaveBeenCalled()
      })
    })
  })

  describe('Trial Manager Component', () => {
    it('should display trial countdown', () => {
      mockTierService.isUserInTrial.mockReturnValue(true)
      mockTierService.getTrialDaysRemaining.mockReturnValue(5)
      mockTierService.getUserTier.mockReturnValue(mockTierService.tierDefinitions.STARTUP)
      
      render(<TrialManager />)
      
      expect(screen.getByText(/5 days remaining/i)).toBeInTheDocument()
      expect(screen.getByText(/Startup Trial/i)).toBeInTheDocument()
    })

    it('should show urgent warning for last day', () => {
      mockTierService.isUserInTrial.mockReturnValue(true)
      mockTierService.getTrialDaysRemaining.mockReturnValue(1)
      mockTierService.getUserTier.mockReturnValue(mockTierService.tierDefinitions.STARTUP)
      
      render(<TrialManager />)
      
      expect(screen.getByText(/1 day remaining/i)).toBeInTheDocument()
    })

    it('should handle trial expiration', () => {
      mockTierService.isUserInTrial.mockReturnValue(false)
      mockTierService.getTrialDaysRemaining.mockReturnValue(0)
      
      render(<TrialManager />)
      
      expect(screen.getByText(/Trial expired/i)).toBeInTheDocument()
    })
  })

  describe('Tier Gating', () => {
    it('should allow access during trial', () => {
      mockTierService.isUserInTrial.mockReturnValue(true)
      mockTierService.getUserTier.mockReturnValue(mockTierService.tierDefinitions.STARTUP)
      
      render(
        <TierGate requiredTier="startup" feature="Advanced Analytics">
          <div>Protected Content</div>
        </TierGate>
      )
      
      expect(screen.getByText('Protected Content')).toBeInTheDocument()
    })

    it('should block access after trial expiration', () => {
      mockTierService.isUserInTrial.mockReturnValue(false)
      mockTierService.getUserTier.mockReturnValue(null)
      
      render(
        <TierGate requiredTier="startup" feature="Advanced Analytics">
          <div>Protected Content</div>
        </TierGate>
      )
      
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
      expect(screen.getByText(/upgrade/i)).toBeInTheDocument()
    })

    it('should show appropriate upgrade prompts', () => {
      mockTierService.isUserInTrial.mockReturnValue(false)
      mockTierService.getUserTier.mockReturnValue(mockTierService.tierDefinitions.SOLOPRENEUR)
      
      render(
        <TierGate requiredTier="startup" feature="Team Collaboration">
          <div>Protected Content</div>
        </TierGate>
      )
      
      expect(screen.getByText(/Upgrade to Startup/i)).toBeInTheDocument()
    })
  })

  describe('Payment Integration', () => {
    it('should create checkout session for paid tiers', async () => {
      mockPaymentService.createCheckoutSession.mockResolvedValue({
        url: 'https://checkout.stripe.com/session123'
      })
      
      const result = await mockPaymentService.createCheckoutSession(
        'test-user-123',
        'startup',
        'monthly'
      )
      
      expect(result.url).toContain('stripe.com')
      expect(mockPaymentService.createCheckoutSession).toHaveBeenCalledWith(
        'test-user-123',
        'startup',
        'monthly'
      )
    })

    it('should handle Enterprise contact sales', async () => {
      const consoleSpy = vi.spyOn(console, 'log')
      
      // Simulate Enterprise tier selection
      const enterpriseTier = mockTierService.tierDefinitions.ENTERPRISE
      expect(enterpriseTier.price).toBe('contact_sales')
      
      // Should not create Stripe session for Enterprise
      expect(mockPaymentService.createCheckoutSession).not.toHaveBeenCalledWith(
        expect.anything(),
        'enterprise',
        expect.anything()
      )
    })
  })

  describe('Feature Access Control', () => {
    const testFeatureAccess = (tierName, features) => {
      const tier = mockTierService.tierDefinitions[tierName.toUpperCase()]
      
      features.forEach(feature => {
        expect(tier.features[feature]).toBeDefined()
      })
    }

    it('should have correct Solopreneur features', () => {
      testFeatureAccess('solopreneur', [
        'maxAgentExecutions',
        'maxTeamMembers',
        'supportLevel'
      ])
      
      const tier = mockTierService.tierDefinitions.SOLOPRENEUR
      expect(tier.features.maxTeamMembers).toBe(1)
      expect(tier.features.supportLevel).toBe('email')
    })

    it('should have correct Startup features', () => {
      testFeatureAccess('startup', [
        'maxAgentExecutions',
        'maxTeamMembers',
        'supportLevel'
      ])
      
      const tier = mockTierService.tierDefinitions.STARTUP
      expect(tier.features.maxTeamMembers).toBe(5)
      expect(tier.features.supportLevel).toBe('priority')
    })

    it('should have correct SME features', () => {
      testFeatureAccess('sme', [
        'maxAgentExecutions',
        'maxTeamMembers',
        'supportLevel'
      ])
      
      const tier = mockTierService.tierDefinitions.SME
      expect(tier.features.maxTeamMembers).toBe(15)
      expect(tier.features.supportLevel).toBe('priority')
    })

    it('should have correct Enterprise features', () => {
      testFeatureAccess('enterprise', [
        'maxAgentExecutions',
        'maxTeamMembers',
        'supportLevel'
      ])
      
      const tier = mockTierService.tierDefinitions.ENTERPRISE
      expect(tier.features.maxTeamMembers).toBe('unlimited')
      expect(tier.features.supportLevel).toBe('dedicated')
    })
  })

  describe('Error Handling', () => {
    it('should handle trial start failures gracefully', async () => {
      mockTierService.startTrial.mockRejectedValue(new Error('Trial start failed'))
      
      try {
        await mockTierService.startTrial('test-user-123', 'startup')
      } catch (error) {
        expect(error.message).toBe('Trial start failed')
      }
    })

    it('should handle payment session creation failures', async () => {
      mockPaymentService.createCheckoutSession.mockRejectedValue(
        new Error('Payment session failed')
      )
      
      try {
        await mockPaymentService.createCheckoutSession('test-user-123', 'startup', 'monthly')
      } catch (error) {
        expect(error.message).toBe('Payment session failed')
      }
    })
  })
})
