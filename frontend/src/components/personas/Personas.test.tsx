// @vitest-environment jsdom
import { render, screen, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach } from 'vitest'
import { SolopreneurShell } from './SolopreneurShell'
import { StartupShell } from './StartupShell'
import { SmeShell } from './SmeShell'
import { EnterpriseShell } from './EnterpriseShell'

describe('Persona Shells', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders SolopreneurShell correctly', () => {
    render(<SolopreneurShell><div>Child</div></SolopreneurShell>)
    expect(screen.getByText('Solopreneur Workspace')).toBeTruthy()
    expect(screen.getByText('Child')).toBeTruthy()
  })

  it('renders StartupShell correctly', () => {
    render(<StartupShell><div>Child</div></StartupShell>)
    expect(screen.getByText('Startup Hub')).toBeTruthy()
    expect(screen.getByText('Child')).toBeTruthy()
  })

  it('renders SmeShell correctly', () => {
    render(<SmeShell><div>Child</div></SmeShell>)
    expect(screen.getByText('SME Operations')).toBeTruthy()
    expect(screen.getByText('Child')).toBeTruthy()
  })

  it('renders EnterpriseShell correctly', () => {
    render(<EnterpriseShell><div>Child</div></EnterpriseShell>)
    expect(screen.getByText('Enterprise Command Center')).toBeTruthy()
    expect(screen.getByText('Child')).toBeTruthy()
  })
})
