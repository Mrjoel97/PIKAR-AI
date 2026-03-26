// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

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
    expect(screen.getByText('Ship fast. Stay lean.')).toBeTruthy()
    expect(screen.getByText('Brain Dump')).toBeTruthy()
    expect(screen.getByText('Child')).toBeTruthy()
  })

  it('renders StartupShell correctly', () => {
    render(<StartupShell><div>Child</div></StartupShell>)
    expect(screen.getByText('Startup Workspace')).toBeTruthy()
    expect(screen.getByText('Experiment. Measure. Grow.')).toBeTruthy()
    expect(screen.getByText('Workflow Templates')).toBeTruthy()
    expect(screen.getByText('Child')).toBeTruthy()
  })

  it('renders SmeShell correctly', () => {
    render(<SmeShell><div>Child</div></SmeShell>)
    expect(screen.getByText('SME Workspace')).toBeTruthy()
    expect(screen.getByText('Reliable operations. Clear accountability.')).toBeTruthy()
    expect(screen.getByText('Departments')).toBeTruthy()
    expect(screen.getByText('Child')).toBeTruthy()
  })

  it('renders EnterpriseShell correctly', () => {
    render(<EnterpriseShell><div>Child</div></EnterpriseShell>)
    expect(screen.getByText('Enterprise Workspace')).toBeTruthy()
    expect(screen.getByText('Governed execution. Strategic control.')).toBeTruthy()
    expect(screen.getByText('Approvals')).toBeTruthy()
    expect(screen.getByText('Child')).toBeTruthy()
  })
})
