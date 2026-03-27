// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { render, screen, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach } from 'vitest'
import { AgentActivityDashboard } from './AgentActivityDashboard'

describe('AgentActivityDashboard', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders metrics', () => {
    render(<AgentActivityDashboard />)
    
    expect(screen.getByText('Active Agents')).toBeTruthy()
    expect(screen.getByLabelText('Active Agents Count')).toBeTruthy()
    
    expect(screen.getByText('Tasks Completed')).toBeTruthy()
    expect(screen.getByLabelText('Tasks Completed Count')).toBeTruthy()

    expect(screen.getByText('Pending Actions')).toBeTruthy()
    expect(screen.getByLabelText('Pending Actions Count')).toBeTruthy()
  })
})
