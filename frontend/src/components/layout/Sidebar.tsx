'use client';

import React from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { LogOut } from 'lucide-react'
import { SessionList } from '../chat/SessionList'
import { MAIN_INTERFACE_NAV_ITEMS, MAIN_INTERFACE_ROUTE } from './sidebarNav'

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentSessionId = searchParams.get('sessionId') || undefined;

  const handleSelectSession = (sessionId: string) => {
    router.push(`${MAIN_INTERFACE_ROUTE}?sessionId=${sessionId}`);
  };

  return (
    <aside className={`w-64 bg-white border-r h-full flex flex-col ${className ?? 'hidden md:flex'}`} aria-label="Sidebar">
      <div className="h-16 flex items-center px-6 border-b">
        <span className="text-xl font-bold text-indigo-600">Pikar AI</span>
      </div>

      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        {MAIN_INTERFACE_NAV_ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </Link>
          )
        })}

        {/* Session History Section */}
        <div className="pt-4 mt-4 border-t border-slate-100">
          <SessionList
            currentSessionId={currentSessionId}
            onSelectSession={handleSelectSession}
            className="mt-2"
          />
        </div>
      </nav>

      <div className="p-4 border-t">
        <button className="flex items-center gap-3 px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg w-full">
          <LogOut size={20} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  )
}
