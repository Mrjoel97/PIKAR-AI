'use client';

import React from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Home, LayoutDashboard, Settings, LogOut, MessageSquare } from 'lucide-react'
import { SessionList } from '../chat/SessionList'

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentSessionId = searchParams.get('sessionId') || undefined;

  const handleSelectSession = (sessionId: string) => {
    router.push(`/dashboard?sessionId=${sessionId}`);
  };

  return (
    <aside className={`w-64 bg-white border-r h-full flex flex-col ${className ?? 'hidden md:flex'}`} aria-label="Sidebar">
      <div className="h-16 flex items-center px-6 border-b">
        <span className="text-xl font-bold text-indigo-600">Pikar AI</span>
      </div>

      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        <Link href="/" className="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg">
          <Home size={20} />
          <span>Home</span>
        </Link>
        <Link href="/dashboard" className="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg">
          <LayoutDashboard size={20} />
          <span>Dashboard</span>
        </Link>
        <Link href="/settings" className="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg">
          <Settings size={20} />
          <span>Settings</span>
        </Link>

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
