'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { usePersona } from '../../contexts/PersonaContext'
import { fetchWithAuth } from '@/services/api'
import { Loader2 } from 'lucide-react'

export function PersonaSwitcher() {
  const { persona, setPersona } = usePersona()
  const [isUpdating, setIsUpdating] = useState(false)
  const router = useRouter()

  const personas = ['solopreneur', 'startup', 'sme', 'enterprise'] as const

  const handlePersonaChange = async (newPersona: string) => {
    if (!newPersona || newPersona === persona) return

    setIsUpdating(true)
    try {
      await fetchWithAuth('/onboarding/switch-persona', {
        method: 'POST',
        body: JSON.stringify({ new_persona: newPersona })
      })

      setPersona(newPersona as any)

      // Client-side navigation (no full page reload)
      router.push(`/${newPersona}`)
    } catch (error) {
      console.error('Failed to switch persona:', error)
      alert('Failed to switch persona. Please try again.')
    } finally {
      setIsUpdating(false)
    }
  }

  return (
    <div className="flex items-center gap-2 bg-gray-100 p-1 rounded-lg">
      <span className="text-xs font-medium text-gray-500 px-2">View as:</span>
      <div className="relative flex items-center">
        <select
          value={persona || ''}
          onChange={(e) => handlePersonaChange(e.target.value)}
          disabled={isUpdating}
          className="bg-transparent text-sm border-none focus:ring-0 cursor-pointer disabled:opacity-50 appearance-none pr-8"
          aria-label="Persona Switcher"
        >
          <option value="">Select Persona</option>
          {personas.map((p) => (
            <option key={p} value={p}>
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </option>
          ))}
        </select>
        {isUpdating ? (
          <div className="absolute right-2 pointer-events-none">
            <Loader2 size={14} className="animate-spin text-blue-600" />
          </div>
        ) : (
          <div className="absolute right-2 pointer-events-none">
            <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        )}
      </div>
    </div>
  )
}
