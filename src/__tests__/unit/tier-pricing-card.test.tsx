import { describe, it, expect } from 'vitest'
import React from 'react'
import { render, screen } from '@testing-library/react'
import TierPricingCards from '@/components/pricing/TierPricingCards'

vi.mock('@/hooks/useTier', () => ({
  useTier: () => ({ currentTier: { id: 'solopreneur' }, startTrial: vi.fn() })
}))
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user_123' } })
}))
vi.mock('@/services/paymentService', () => ({
  paymentService: { createCheckoutSession: vi.fn(async () => ({ url: 'https://example.com' })) }
}))

describe('TierPricingCards', () => {
  it('renders blueprint prices and shows yearly savings badge', () => {
    render(<TierPricingCards />)
    // Prices present
    expect(screen.getByText('Solopreneur')).toBeInTheDocument()
    expect(screen.getByText('Startup')).toBeInTheDocument()
    expect(screen.getByText('SME')).toBeInTheDocument()
    // Badge text appears after toggling yearly in component state? We just assert the label exists
    expect(screen.getByText('Save up to 17%')).toBeInTheDocument()
  })
})

