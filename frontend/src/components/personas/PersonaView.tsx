'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React from 'react'
import { usePersona } from '../../contexts/PersonaContext'
import { SolopreneurShell } from './SolopreneurShell'
import { StartupShell } from './StartupShell'
import { SmeShell } from './SmeShell'
import { EnterpriseShell } from './EnterpriseShell'

export function PersonaView() {
  const { persona } = usePersona()

  if (!persona) {
    return (
      <div className="p-8 text-center">
        <h2 className="text-xl font-semibold mb-2">No Persona Selected</h2>
        <p className="text-gray-600">Please select a persona to view your dashboard.</p>
      </div>
    )
  }

  switch (persona) {
    case 'solopreneur':
      return (
        <SolopreneurShell>
          <h2 className="text-xl font-bold mb-4">Solopreneur Dashboard</h2>
          <p>Welcome to your personal workspace.</p>
        </SolopreneurShell>
      )
    case 'startup':
      return (
        <StartupShell>
          <h2 className="text-xl font-bold mb-4">Startup Dashboard</h2>
          <p>Team metrics and growth tracking.</p>
        </StartupShell>
      )
    case 'sme':
      return (
        <SmeShell>
          <h2 className="text-xl font-bold mb-4">SME Dashboard</h2>
          <p>Operations and compliance management.</p>
        </SmeShell>
      )
    case 'enterprise':
      return (
        <EnterpriseShell>
          <h2 className="text-xl font-bold mb-4">Enterprise Dashboard</h2>
          <p>Global portfolio view.</p>
        </EnterpriseShell>
      )
    default:
      return <div>Unknown Persona</div>
  }
}
