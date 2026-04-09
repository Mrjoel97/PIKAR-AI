// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Frontend API client for the suggestion chip endpoint.
 *
 * Fetches persona-aware, time-of-day-sensitive suggestion chips
 * from GET /suggestions with a 30-second in-memory cache.
 */

import { fetchWithAuth } from '@/services/api';

export interface SuggestionItem {
  text: string;
  category: string;
}

// ---------------------------------------------------------------------------
// Simple in-memory cache (30 seconds)
// ---------------------------------------------------------------------------

let _cachedResult: SuggestionItem[] | null = null;
let _cachedAt = 0;
let _cachedKey = '';
const CACHE_TTL_MS = 30_000;

/**
 * Fetch personalized suggestion chips from the backend.
 *
 * Results are cached for 30 seconds keyed by persona to avoid
 * refetching on every render cycle.
 */
export async function fetchSuggestions(persona: string): Promise<SuggestionItem[]> {
  const now = Date.now();
  const cacheKey = persona;

  if (_cachedResult && _cachedKey === cacheKey && now - _cachedAt < CACHE_TTL_MS) {
    return _cachedResult;
  }

  const hour = new Date().getHours();
  const response = await fetchWithAuth(`/suggestions?persona=${encodeURIComponent(persona)}&hour=${hour}`);
  const data: SuggestionItem[] = await response.json();

  _cachedResult = data;
  _cachedAt = now;
  _cachedKey = cacheKey;

  return data;
}
