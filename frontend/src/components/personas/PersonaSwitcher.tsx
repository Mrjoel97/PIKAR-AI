'use client'

import React from 'react'
import { usePersona } from '../../contexts/PersonaContext'

export function PersonaSwitcher() {
  const { persona, setPersona } = usePersona()

  const personas = ['solopreneur', 'startup', 'sme', 'enterprise'] as const

  return (
    <div className="flex items-center gap-2 bg-gray-100 p-1 rounded-lg">
      <span className="text-xs font-medium text-gray-500 px-2">View as:</span>
      <select 
        value={persona || ''} 
        onChange={(e) => setPersona(e.target.value as any)}
        className="bg-transparent text-sm border-none focus:ring-0 cursor-pointer"
        aria-label="Persona Switcher"
      >
        <option value="">Select Persona</option>
        {personas.map((p) => (
          <option key={p} value={p}>
            {p.charAt(0).toUpperCase() + p.slice(1)}
          </option>
        ))}
      </select>
    </div>
  )
}
