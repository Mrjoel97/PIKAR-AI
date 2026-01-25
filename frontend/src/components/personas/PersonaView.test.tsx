// @vitest-environment jsdom
import { render, screen, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import { PersonaView } from './PersonaView'
import * as PersonaContextModule from '../../contexts/PersonaContext'

// Mock usePersona
const usePersonaMock = vi.fn()
vi.mock('../../contexts/PersonaContext', async () => {
  const actual = await vi.importActual('../../contexts/PersonaContext')
  return {
    ...actual,
    usePersona: () => usePersonaMock()
  }
})

describe('PersonaView', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders no persona message when null', () => {
    usePersonaMock.mockReturnValue({ persona: null })
    render(<PersonaView />)
    expect(screen.getByText('No Persona Selected')).toBeTruthy()
  })

  it('renders SolopreneurShell when persona is solopreneur', () => {
    usePersonaMock.mockReturnValue({ persona: 'solopreneur' })
    render(<PersonaView />)
    expect(screen.getByText('Solopreneur Workspace')).toBeTruthy()
    expect(screen.getByText('Solopreneur Dashboard')).toBeTruthy()
  })

  it('renders StartupShell when persona is startup', () => {
    usePersonaMock.mockReturnValue({ persona: 'startup' })
    render(<PersonaView />)
    expect(screen.getByText('Startup Hub')).toBeTruthy()
  })

   it('renders SmeShell when persona is sme', () => {
    usePersonaMock.mockReturnValue({ persona: 'sme' })
    render(<PersonaView />)
    expect(screen.getByText('SME Operations')).toBeTruthy()
  })

   it('renders EnterpriseShell when persona is enterprise', () => {
    usePersonaMock.mockReturnValue({ persona: 'enterprise' })
    render(<PersonaView />)
    expect(screen.getByText('Enterprise Command Center')).toBeTruthy()
  })
})
