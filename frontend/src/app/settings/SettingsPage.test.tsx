// @vitest-environment jsdom
import { render, screen, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import SettingsPage from './page'

// Mock the usePersona hook
vi.mock('@/contexts/PersonaContext', () => ({
  usePersona: vi.fn(() => ({ persona: 'solopreneur' }))
}))

import { usePersona } from '@/contexts/PersonaContext'

describe('SettingsPage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders base settings form', () => {
    render(<SettingsPage />)
    
    expect(screen.getByText('User Settings')).toBeTruthy()
    expect(screen.getByText('Profile Information')).toBeTruthy()
    expect(screen.getByLabelText('Full Name')).toBeTruthy()
    expect(screen.getByLabelText('Email Address')).toBeTruthy()
  })

  it('renders solopreneur specific settings when persona is solopreneur', () => {
    vi.mocked(usePersona).mockReturnValue({ persona: 'solopreneur' })
    render(<SettingsPage />)
    
    expect(screen.getByText('Solopreneur Tools')).toBeTruthy()
    expect(screen.getByLabelText('Revenue Target (Monthly)')).toBeTruthy()
  })

  it('renders startup specific settings when persona is startup', () => {
    vi.mocked(usePersona).mockReturnValue({ persona: 'startup' })
    render(<SettingsPage />)
    
    expect(screen.getByText('Startup Settings')).toBeTruthy()
    expect(screen.getByLabelText('Target Burn Rate')).toBeTruthy()
  })

  it('renders sme specific settings when persona is sme', () => {
    vi.mocked(usePersona).mockReturnValue({ persona: 'sme' })
    render(<SettingsPage />)
    
    expect(screen.getByText('SME Operations')).toBeTruthy()
    expect(screen.getByLabelText('Number of Departments')).toBeTruthy()
  })

  it('renders enterprise specific settings when persona is enterprise', () => {
    vi.mocked(usePersona).mockReturnValue({ persona: 'enterprise' })
    render(<SettingsPage />)
    
    expect(screen.getByText('Enterprise Compliance')).toBeTruthy()
    expect(screen.getByLabelText('Enable Detailed Audit Logs')).toBeTruthy()
  })

  it('renders save button', () => {
    render(<SettingsPage />)
    
    expect(screen.getByText('Save Changes')).toBeTruthy()
  })
})
