// @vitest-environment jsdom
import { render, screen, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import { DashboardLayout } from './DashboardLayout'

// Mock usePersona
vi.mock('../../contexts/PersonaContext', () => ({
  usePersona: () => ({
    persona: 'solopreneur',
    setPersona: vi.fn()
  }),
  PersonaProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>
}))

describe('DashboardLayout', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders children correctly', () => {
    render(
      <DashboardLayout>
        <div data-testid="child-content">Child Content</div>
      </DashboardLayout>
    )
    
    expect(screen.getByTestId('child-content')).toBeTruthy()
  })

  it('renders sidebar and header', () => {
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    )
    
    expect(screen.getByLabelText('Sidebar')).toBeTruthy()
    expect(screen.getByLabelText('Header')).toBeTruthy()
  })

  // Add more tests for responsiveness if needed (e.g., hidden sidebar on mobile)
  it('hides sidebar on mobile initially', () => {
     // This usually requires checking classes or computed styles
     render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    )
    const sidebar = screen.getByLabelText('Sidebar')
    expect(sidebar.className).toContain('hidden')
    expect(sidebar.className).toContain('md:flex')
  })
})
