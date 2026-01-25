// @vitest-environment jsdom
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import { PersonaSwitcher } from './PersonaSwitcher'
import * as PersonaContextModule from '../../contexts/PersonaContext'

// Mock usePersona
const setPersonaMock = vi.fn()
const usePersonaMock = vi.fn().mockReturnValue({ persona: null, setPersona: setPersonaMock })

vi.mock('../../contexts/PersonaContext', async () => {
  const actual = await vi.importActual('../../contexts/PersonaContext')
  return {
    ...actual,
    usePersona: () => usePersonaMock()
  }
})

describe('PersonaSwitcher', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders switcher options', () => {
    render(<PersonaSwitcher />)
    expect(screen.getByLabelText('Persona Switcher')).toBeTruthy()
    expect(screen.getByText('Solopreneur')).toBeTruthy()
    expect(screen.getByText('Startup')).toBeTruthy()
  })

  it('calls setPersona on change', () => {
    render(<PersonaSwitcher />)
    const select = screen.getByLabelText('Persona Switcher')
    fireEvent.change(select, { target: { value: 'startup' } })
    expect(setPersonaMock).toHaveBeenCalledWith('startup')
  })
})
