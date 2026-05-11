'use client';

import React, { useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Lock, LogOut, ShieldAlert } from 'lucide-react'
import { SessionList } from '../chat/SessionList'
import { RecentWidgets } from './RecentWidgets'
import { MAIN_INTERFACE_ROUTE } from './sidebarNav'
import { usePendingApprovals } from '@/hooks/usePendingApprovals'
import { usePersona } from '@/contexts/PersonaContext'
import { useAdminAccess } from '@/hooks/useAdminAccess'
import { useEffectiveTier } from '@/hooks/useEffectiveTier'
import { getPersonaNavItems } from './personaNavConfig'
import {
  getFeatureKeyForRoute,
  isFeatureAllowed,
  type FeatureKey,
} from '@/config/featureGating'
import { UpgradePrompt } from '@/components/ui/UpgradePrompt'
import { signOut } from '@/services/auth'

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  const router = useRouter();
  const { count: pendingCount } = usePendingApprovals();

  // Persona-aware nav ordering — persona drives the *visual* ordering of
  // items in the sidebar, distinct from tier gating which controls locks.
  let currentPersona: string | null = null;
  try {
    const ctx = usePersona();
    currentPersona = ctx.persona;
  } catch {
    // Fallback to default ordering
  }
  const navItems = useMemo(() => getPersonaNavItems(currentPersona as 'solopreneur' | 'startup' | 'sme' | 'enterprise' | null), [currentPersona]);

  // Effective tier drives the lock-icon / upgrade-popover decisions. Resolved
  // via the centralized hook so this surface agrees with PremiumShell and
  // useFeatureGate (previously this file used persona directly, which could
  // disagree with subscription.tier for free-plan users).
  const { tier: userTier } = useEffectiveTier();

  // Admin role check — separate from tier gating. Renders an "Admin Panel"
  // nav entry only when the backend role check passes.
  const { isAdmin } = useAdminAccess();

  // Track which locked nav item's upgrade popover is open
  const [lockedFeaturePopover, setLockedFeaturePopover] = useState<FeatureKey | null>(null);

  const handleSelectSession = (sessionId: string) => {
    router.push(`${MAIN_INTERFACE_ROUTE}?sessionId=${sessionId}`);
  };

  const handleLockedItemClick = (featureKey: FeatureKey) => {
    setLockedFeaturePopover((prev) => (prev === featureKey ? null : featureKey));
  };

  const handleClosePopover = () => {
    setLockedFeaturePopover(null);
  };

  const handleSignOut = async () => {
    try {
      await signOut({ redirect: true, redirectTo: '/auth/login' });
    } catch (error) {
      console.error('Sign out failed, forcing redirect:', error);
      window.location.assign('/auth/login');
    }
  };

  return (
    <aside
      className={`w-64 bg-white border-r h-full flex flex-col relative ${className ?? 'hidden md:flex'}`}
      aria-label="Sidebar"
    >
      <div className="h-16 flex items-center px-6 border-b">
        <span className="text-xl font-bold text-indigo-600">Pikar AI</span>
      </div>

      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const isApprovals = item.label === 'Approvals';

          // Determine if this nav item is gated. Uses the resolved effective
          // tier (subscription-canonical) rather than persona directly.
          const featureKey = getFeatureKeyForRoute(item.href);
          const isLocked =
            featureKey !== null && !isFeatureAllowed(featureKey, userTier);

          if (isLocked && featureKey !== null) {
            const isPopoverOpen = lockedFeaturePopover === featureKey;
            return (
              <div key={item.href} className="relative">
                <button
                  type="button"
                  onClick={() => handleLockedItemClick(featureKey)}
                  className="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg w-full text-left opacity-60"
                  aria-label={`${item.label} — upgrade required`}
                >
                  <Icon size={20} />
                  <span>{item.label}</span>
                  <Lock size={14} className="text-slate-400 ml-auto" aria-hidden="true" />
                </button>

                {isPopoverOpen && (
                  <>
                    {/* Click-outside overlay */}
                    <div
                      className="fixed inset-0 z-40"
                      onClick={handleClosePopover}
                      aria-hidden="true"
                    />
                    {/* Popover to the right of sidebar */}
                    <div className="absolute left-full top-0 ml-2 z-50 w-72 bg-white shadow-xl rounded-xl border border-slate-200 p-4">
                      <UpgradePrompt featureKey={featureKey} variant="sidebar" />
                    </div>
                  </>
                )}
              </div>
            );
          }

          // Normal ungated nav item
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              <Icon size={20} />
              <span>{item.label}</span>
              {isApprovals && pendingCount > 0 && (
                <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-[10px] font-bold text-white">
                  {pendingCount > 99 ? '99+' : pendingCount}
                </span>
              )}
            </Link>
          )
        })}

        {isAdmin && (
          <Link
            href="/admin"
            className="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            <ShieldAlert size={20} />
            <span>Admin Panel</span>
          </Link>
        )}

        {/* Session History Section */}
        <div className="pt-4 mt-4 border-t border-slate-100">
          <SessionList
            onSelectSession={handleSelectSession}
            className="mt-2"
          />
        </div>

        {/* Recent Widgets Section */}
        <div className="pt-4 mt-4 border-t border-slate-100">
          <RecentWidgets />
        </div>
      </nav>

      <div className="p-4 border-t">
        <button
          type="button"
          onClick={handleSignOut}
          className="flex items-center gap-3 px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg w-full"
        >
          <LogOut size={20} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  )
}
