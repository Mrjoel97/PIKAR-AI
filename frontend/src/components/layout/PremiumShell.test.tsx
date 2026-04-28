// @vitest-environment jsdom

import type { ComponentProps } from 'react'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PremiumShell } from './PremiumShell'

vi.mock('framer-motion', () => ({
  motion: {
    aside: ({ children, ...props }: ComponentProps<'aside'>) => <aside {...props}>{children}</aside>,
    span: ({ children, ...props }: ComponentProps<'span'>) => <span {...props}>{children}</span>,
  },
}))

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard/reports',
}))

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: ComponentProps<'a'>) => <a href={href} {...props}>{children}</a>,
}))

vi.mock('@/hooks/useSwipeGesture', () => ({
  useSwipeGesture: () => undefined,
}))

vi.mock('@/contexts/PersonaContext', () => ({
  usePersona: () => ({
    persona: 'startup',
  }),
}))

vi.mock('@/contexts/SubscriptionContext', () => ({
  useSubscription: () => ({
    tier: 'startup',
  }),
}))

vi.mock('./personaNavConfig', () => ({
  getPersonaNavItems: () => [
    {
      href: '/dashboard/command-center',
      label: 'Command Center',
      icon: () => null,
    },
  ],
}))

vi.mock('@/components/billing/SubscriptionBadge', () => ({
  SubscriptionBadge: () => <div data-testid="subscription-badge" />,
}))

vi.mock('./UpgradeGateModal', () => ({
  UpgradeGateModal: () => null,
}))

vi.mock('@/components/layout/KpiHeader', () => ({
  KpiHeader: () => <div data-testid="kpi-header">kpi-header</div>,
}))

vi.mock('@/services/auth', () => ({
  signOut: vi.fn(),
}))

describe('PremiumShell', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    })
  })

  it('hides the global KPI header by default', () => {
    render(
      <PremiumShell>
        <div>Workspace body</div>
      </PremiumShell>,
    )

    expect(screen.queryByTestId('kpi-header')).toBeNull()
    expect(screen.getByText('Workspace body')).toBeTruthy()
  })

  it('only renders the global KPI header when explicitly enabled on dashboard surfaces', () => {
    const { rerender } = render(
      <PremiumShell showGlobalKpiHeader>
        <div>Dashboard body</div>
      </PremiumShell>,
    )

    expect(screen.getByTestId('kpi-header')).toBeTruthy()

    rerender(
      <PremiumShell showGlobalKpiHeader surface="workspace">
        <div>Workspace body</div>
      </PremiumShell>,
    )

    expect(screen.queryByTestId('kpi-header')).toBeNull()
  })
})
