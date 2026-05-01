'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.
//
// TabStrip — multi-session tab UI for FEATURE-MULTI-SESSION-TABS.
//
// Stateless presentation component: receives all data and callbacks via props
// and emits no internal state. This makes it trivially unit-testable without
// any context wrapping. Plan 88-04 will pass per-tab streaming/unread
// indicator state through props without refactoring this contract.
//
// Visual contract (locked decisions, see Plan 88-03 PLAN.md):
//   - Active pill: teal-50 background + teal-200 border + bold text
//   - Inactive pill: white bg, slate text, hover: slate-100
//   - Close `×` reveals on group-hover (VS Code / Chrome / Firefox tab UX)
//   - Trailing `+` button is disabled at cap (HTML disabled attribute, native
//     click suppression + screen-reader announcement)

import React from 'react'
import { X, Plus } from 'lucide-react'

export interface TabStripTab {
  /** session_id from openTabIds */
  id: string
  /** Display label — session.title with preview fallback, truncated to ~24 chars */
  label: string
  /** Visual selected-state flag (true when id === visibleSessionId) */
  isActive: boolean
}

export interface TabStripProps {
  tabs: TabStripTab[]
  activeId: string | null
  cap: number
  /** Called when user clicks a pill (not the close X). */
  onSwitch: (id: string) => void
  /** Called when user clicks the X on a pill. Implementer guarantees
   *  last-tab fallback. */
  onClose: (id: string) => void
  /** Called when user clicks the trailing + button. Disabled when
   *  tabs.length >= cap. */
  onNew: () => void
  /** Optional className passthrough for layout containers. */
  className?: string
  /**
   * Per-tab activity state (FEATURE-MULTI-SESSION-TABS criterion 9). Keys
   * are session ids; values describe what the tab pill should display when
   * NOT active. The active tab never shows an indicator regardless of this
   * map (by definition the user is watching it).
   *  - 'streaming' → animated pulsing dot (background SSE active)
   *  - 'unread'    → solid dot (recent finish, not yet viewed)
   *  - 'none' or absent → no indicator
   *
   * Plan 88-04 wires this from ChatInterface's useMemo over
   * useSessionMap().activeSessions.
   */
  indicators?: Record<string, 'streaming' | 'unread' | 'none'>
}

export function TabStrip({
  tabs,
  activeId,
  cap,
  onSwitch,
  onClose,
  onNew,
  className,
  indicators,
}: TabStripProps): React.ReactElement {
  const atCap = tabs.length >= cap

  return (
    <div
      role="tablist"
      aria-label="Open chat sessions"
      className={`flex items-center gap-1 px-2 py-1 bg-slate-50/40 overflow-x-auto ${className ?? ''}`}
    >
      {tabs.map((tab) => {
        // `activeId` is the canonical source — `tab.isActive` is honored as a
        // fallback so callers can opt into per-tab override semantics if they
        // ever need to (e.g. visually-active-but-not-currently-visible).
        const isActive = activeId !== null ? tab.id === activeId : tab.isActive
        return (
        <div
          key={tab.id}
          role="tab"
          aria-selected={isActive}
          className={`group flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors max-w-[160px] flex-shrink-0 ${
            isActive
              ? 'bg-teal-50 text-teal-700 font-semibold border border-teal-200'
              : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <button
            type="button"
            data-testid={`tab-pill-${tab.id}`}
            onClick={() => onSwitch(tab.id)}
            className="flex-1 truncate text-left cursor-pointer bg-transparent border-0 p-0 m-0 text-inherit"
            title={tab.label}
          >
            {tab.label}
          </button>
          {(() => {
            // Indicator (FEATURE-MULTI-SESSION-TABS criterion 9). The active
            // tab never shows an indicator — by definition the user is
            // watching it. For non-active tabs, render an animated pulsing
            // dot when streaming, a solid dot when unread, nothing
            // otherwise. The map is sparse — absent ids resolve to 'none'.
            if (isActive) return null
            const state = indicators?.[tab.id] ?? 'none'
            if (state === 'none') return null
            const dotClass =
              state === 'streaming'
                ? 'w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse'
                : 'w-1.5 h-1.5 rounded-full bg-teal-500'
            return (
              <span
                data-testid={`tab-indicator-${tab.id}`}
                className={dotClass}
                aria-label={
                  state === 'streaming' ? 'Streaming' : 'New activity'
                }
                role="status"
              />
            )
          })()}
          <button
            type="button"
            data-testid={`tab-close-${tab.id}`}
            onClick={(e) => {
              // Stop propagation so the parent's tab-pill click handler does
              // NOT also fire and switch to the tab being closed.
              e.stopPropagation()
              onClose(tab.id)
            }}
            className="opacity-0 group-hover:opacity-100 hover:bg-red-100 hover:text-red-600 rounded p-0.5 transition-opacity"
            aria-label={`Close ${tab.label}`}
          >
            <X size={10} />
          </button>
        </div>
        )
      })}

      <button
        type="button"
        data-testid="tab-new"
        onClick={atCap ? undefined : onNew}
        disabled={atCap}
        className={`flex items-center justify-center p-1 rounded-md transition-colors flex-shrink-0 ${
          atCap
            ? 'text-slate-300 cursor-not-allowed'
            : 'text-slate-500 hover:text-teal-600 hover:bg-slate-100'
        }`}
        aria-label={
          atCap ? `Tab cap reached (${cap})` : 'New chat'
        }
        title={
          atCap
            ? `Tab cap reached (${cap}). Close a tab to open a new one.`
            : 'New chat'
        }
      >
        <Plus size={14} />
      </button>
    </div>
  )
}
