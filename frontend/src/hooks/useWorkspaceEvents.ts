'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useEffect, useState } from 'react';
import type { WorkspaceEvent } from '@/types/workspace-events';

const ENDPOINT = '/api/workspace/events';

/**
 * Subscribe to the per-user workspace SSE channel and accumulate events.
 *
 * Reconnect is delegated to `EventSource`'s native retry loop. Malformed
 * payloads are logged and skipped — a bad frame must never crash the canvas.
 *
 * Cleanup: the underlying `EventSource` is closed when the consumer
 * unmounts so we never leak open connections across route transitions.
 */
export function useWorkspaceEvents(): WorkspaceEvent[] {
    const [events, setEvents] = useState<WorkspaceEvent[]>([]);

    useEffect(() => {
        if (typeof EventSource === 'undefined') {
            // SSR / older runtimes — no-op so the hook is safe to call from
            // any client component without a feature-detection branch in the
            // caller.
            return;
        }

        const source = new EventSource(ENDPOINT);

        source.onmessage = (e: MessageEvent) => {
            try {
                const parsed = JSON.parse(e.data) as WorkspaceEvent;
                if (
                    parsed
                    && (parsed.kind === 'progress' || parsed.kind === 'artifact')
                ) {
                    setEvents((prev) => [...prev, parsed]);
                } else {
                    console.warn(
                        '[useWorkspaceEvents] dropping event with unknown kind',
                        parsed,
                    );
                }
            } catch (err) {
                console.warn(
                    '[useWorkspaceEvents] dropping malformed payload',
                    err,
                );
            }
        };

        source.onerror = (err: Event) => {
            // EventSource auto-reconnects; surface the warning so a long-lived
            // disconnect is observable without flooding the console.
            console.warn('[useWorkspaceEvents] SSE error', err);
        };

        return () => {
            source.close();
        };
    }, []);

    return events;
}
