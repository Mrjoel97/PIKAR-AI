'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useEffect, useRef, useState } from 'react';

import {
  type AutopilotEvent,
  type AutopilotStatusResponse,
  getAutopilotStatus,
} from '@/services/app-builder';

const POLL_INTERVAL_MS = 3000;

interface Options {
  /** Stop polling once status is one of these terminal states. */
  stopOn?: Array<AutopilotStatusResponse['autopilot_status']>;
  /** Called once per new event (de-duplicated by ts+message). */
  onEvent?: (event: AutopilotEvent) => void;
}

/**
 * Polls /autopilot-status every 3s while autopilot is active.
 * De-duplicates events; fires `onEvent` once per new one (so chat narration
 * isn't re-posted on every poll cycle).
 */
export function useAppBuilderAutopilot(
  projectId: string | null,
  { stopOn = ['done', 'failed'], onEvent }: Options = {},
) {
  const [status, setStatus] = useState<AutopilotStatusResponse | null>(null);
  const seenKeysRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function tick() {
      if (cancelled || !projectId) return;
      try {
        const next = await getAutopilotStatus(projectId);
        if (cancelled) return;
        setStatus(next);
        for (const ev of next.events) {
          const key = `${ev.ts}:${ev.message}`;
          if (!seenKeysRef.current.has(key)) {
            seenKeysRef.current.add(key);
            onEvent?.(ev);
          }
        }
        if (stopOn.includes(next.autopilot_status)) return;
      } catch {
        // Swallow transient errors; the next tick retries.
      }
      timer = setTimeout(tick, POLL_INTERVAL_MS);
    }

    void tick();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [projectId, stopOn, onEvent]);

  return status;
}
