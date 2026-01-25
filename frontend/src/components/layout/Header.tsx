import React from 'react'
import { Menu, User } from 'lucide-react'
import { PersonaSwitcher } from '../personas/PersonaSwitcher'

interface HeaderProps {
  onMenuClick?: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
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
        <PersonaSwitcher />
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
            <User size={16} className="text-gray-600" />
          </div>
          <span className="text-sm font-medium hidden sm:block">User</span>
        </div>
      </div>
    </header>
  )
}
