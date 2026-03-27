'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import type { SessionStatus } from '@/types/session'

interface SessionStatusBadgeProps {
  status: SessionStatus
  hasUnread: boolean
}

export function SessionStatusBadge({ status, hasUnread }: SessionStatusBadgeProps) {
  if (status === 'streaming') {
    return (
      <span className="relative flex h-2.5 w-2.5">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500" />
      </span>
    )
  }

  if (hasUnread) {
    return <span className="inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
  }

  if (status === 'interrupted') {
    return <span className="inline-flex rounded-full h-2 w-2 bg-zinc-400" />
  }

  return null
}
