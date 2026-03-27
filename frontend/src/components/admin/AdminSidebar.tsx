'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { ADMIN_NAV_ITEMS } from './adminNav';

/**
 * AdminSidebar renders the dark-themed navigation sidebar for the admin panel.
 * Highlights the active route using Next.js usePathname hook.
 */
interface AdminSidebarProps {
  adminEmail?: string;
}

export function AdminSidebar({ adminEmail }: AdminSidebarProps) {
  const pathname = usePathname();

  const isActive = (href: string): boolean => {
    if (href === '/admin') {
      return pathname === '/admin';
    }
    return pathname.startsWith(href);
  };

  return (
    <aside className="w-64 bg-gray-900 text-gray-100 h-full flex flex-col flex-shrink-0" aria-label="Admin Sidebar">
      {/* Header */}
      <div className="h-16 flex items-center px-6 border-b border-gray-700">
        <span className="text-xl font-bold text-indigo-400">Pikar Admin</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {ADMIN_NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700 space-y-2">
        {adminEmail && (
          <p className="px-4 py-2 text-xs text-gray-400 truncate" title={adminEmail}>
            {adminEmail}
          </p>
        )}
        <Link
          href="/dashboard"
          className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-400 hover:bg-gray-800 hover:text-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft size={18} />
          <span>Back to Dashboard</span>
        </Link>
      </div>
    </aside>
  );
}
