'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * SuggestionChips -- Reusable chip strip for persona-aware chat suggestions.
 *
 * Fetches chips from the backend via `fetchSuggestions` and renders them as
 * horizontally scrollable pill buttons. Falls back to hardcoded generic
 * suggestions when the fetch fails.
 */

import { useEffect, useState } from 'react';

import { fetchSuggestions, type SuggestionItem } from '@/services/suggestions';

const FALLBACK_SUGGESTIONS: SuggestionItem[] = [
  { text: 'Review my business', category: 'quick_start' },
  { text: 'Create a strategic plan', category: 'quick_start' },
  { text: 'Start a brain dump session', category: 'quick_start' },
  { text: 'Show available workflows', category: 'quick_start' },
];

interface SuggestionChipsProps {
  /** Called when a chip is clicked with the chip text. */
  onSelect: (text: string) => void;
  /** Current user persona key. */
  persona: string;
  /** When false, the component renders nothing. */
  visible: boolean;
}

export function SuggestionChips({ onSelect, persona, visible }: SuggestionChipsProps) {
  const [chips, setChips] = useState<SuggestionItem[]>([]);

  useEffect(() => {
    if (!visible) return;

    let cancelled = false;

    async function load() {
      try {
        const data = await fetchSuggestions(persona || 'solopreneur');
        if (!cancelled) setChips(data);
      } catch {
        if (!cancelled) setChips(FALLBACK_SUGGESTIONS);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [persona, visible]);

  if (!visible || chips.length === 0) return null;

  return (
    <div
      className="mb-3 flex overflow-x-auto gap-2 pb-1 scrollbar-hide animate-in fade-in duration-300"
      style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
    >
      {chips.map((chip) => (
        <button
          key={chip.text}
          type="button"
          onClick={() => onSelect(chip.text)}
          className="flex-shrink-0 px-3 py-1.5 bg-white border border-slate-200 rounded-lg shadow-sm text-xs font-medium text-slate-600 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-colors"
        >
          {chip.text}
        </button>
      ))}
    </div>
  );
}
