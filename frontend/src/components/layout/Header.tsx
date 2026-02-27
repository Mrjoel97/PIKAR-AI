import React from 'react'
import { Menu, User } from 'lucide-react'
import { PersonaSwitcher } from '../personas/PersonaSwitcher'
import { usePersona } from '../../contexts/PersonaContext'

interface HeaderProps {
  onMenuClick?: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  const { persona, isLoading, userEmail } = usePersona()

  const getPersonaColor = (p: string | null) => {
    switch (p) {
      case 'solopreneur': return 'bg-purple-50 text-purple-700 border-purple-100'
      case 'startup': return 'bg-blue-50 text-blue-700 border-blue-100'
      case 'sme': return 'bg-green-50 text-green-700 border-green-100'
      case 'enterprise': return 'bg-orange-50 text-orange-700 border-orange-100'
      default: return 'bg-gray-50 text-gray-700 border-gray-100'
    }
  }

  return (
    <header className="bg-white border-b h-16 flex items-center justify-between px-6" aria-label="Header">
      <button
        className="md:hidden p-2 hover:bg-gray-100 rounded-lg"
        onClick={onMenuClick}
        aria-label="Toggle menu"
      >
        <Menu size={24} />
      </button>

      <div className="flex items-center gap-4 ml-auto">
        {isLoading ? (
          <div className="h-8 w-24 bg-gray-100 animate-pulse rounded-lg" />
        ) : persona && (
          <div className={`flex items-center gap-2 px-3 py-1.5 border rounded-lg transition-colors ${getPersonaColor(persona)}`}>
            <span className="text-xs font-bold uppercase tracking-wider">{persona}</span>
          </div>
        )}

        <PersonaSwitcher />

        <div className="flex items-center gap-3 pl-4 border-l">
          <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center border border-slate-200">
            <User size={16} className="text-slate-600" />
          </div>
          <div className="hidden sm:flex flex-col">
            <span className="text-sm font-semibold text-slate-900 leading-tight">
              {userEmail ? userEmail.split('@')[0] : 'User'}
            </span>
            <span className="text-[10px] text-slate-500 font-medium">
              {userEmail || 'My Account'}
            </span>
          </div>
        </div>
      </div>
    </header>
  )
}
