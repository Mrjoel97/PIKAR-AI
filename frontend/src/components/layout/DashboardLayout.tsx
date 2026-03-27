'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useState, useEffect } from 'react'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { useSwipeGesture } from '@/hooks/useSwipeGesture'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const media = window.matchMedia('(max-width: 768px)')
    const update = () => setIsMobile(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  useSwipeGesture({
    onSwipeOpen: () => setIsMobileMenuOpen(true),
    onSwipeClose: () => setIsMobileMenuOpen(false),
    isOpen: isMobileMenuOpen,
    enabled: isMobile,
  })

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar - Hidden on mobile by default (controlled by CSS in Sidebar component) */}
      <React.Suspense fallback={<div className="w-64 bg-white border-r h-full hidden md:flex" />}>
        <Sidebar />
      </React.Suspense>

      {/* Mobile Sidebar Overlay (Simplified for now) */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setIsMobileMenuOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0 w-64 bg-white transform transition-transform duration-300 ease-out max-h-[100dvh] overflow-y-auto">
            <React.Suspense fallback={<div className="w-64 bg-white h-full" />}>
              <Sidebar className="flex" />
            </React.Suspense>
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header onMenuClick={() => setIsMobileMenuOpen(true)} />

        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}