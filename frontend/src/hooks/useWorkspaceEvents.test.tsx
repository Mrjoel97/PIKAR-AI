// @vitest-environment jsdom

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWorkspaceEvents } from './useWorkspaceEvents';
import type { WorkspaceEvent } from '@/types/workspace-events';

class FakeEventSource {
    public onmessage: ((evt: MessageEvent) => void) | null = null;
    public onerror: ((evt: Event) => void) | null = null;
    public close = vi.fn();
    constructor(public url: string) {
        FakeEventSource.instances.push(this);
    }
    static instances: FakeEventSource[] = [];
    static reset() {
        FakeEventSource.instances = [];
    }
}

describe('useWorkspaceEvents', () => {
    beforeEach(() => {
        FakeEventSource.reset();
        // @ts-expect-error patch global with our fake
        global.EventSource = FakeEventSource;
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('opens an EventSource against /api/workspace/events', () => {
        renderHook(() => useWorkspaceEvents());
        expect(FakeEventSource.instances).toHaveLength(1);
        expect(FakeEventSource.instances[0].url).toBe('/api/workspace/events');
    });

    it('appends incoming events in order', () => {
        const { result } = renderHook(() => useWorkspaceEvents());
        const source = FakeEventSource.instances[0];

        const a: WorkspaceEvent = {
            kind: 'progress',
            agent_id: 'FIN',
            contract_id: null,
            item: 'step',
            status: 'started',
        };
        const b: WorkspaceEvent = {
            kind: 'artifact',
            agent_id: 'FIN',
            contract_id: null,
            artifact_kind: 'report',
            ref: 'vault://1',
            summary: 's',
            preview_url: null,
        };

        act(() => {
            source.onmessage?.({ data: JSON.stringify(a) } as MessageEvent);
            source.onmessage?.({ data: JSON.stringify(b) } as MessageEvent);
        });

        expect(result.current).toHaveLength(2);
        expect(result.current[0]).toEqual(a);
        expect(result.current[1]).toEqual(b);
    });

    it('closes the EventSource on unmount', () => {
        const { unmount } = renderHook(() => useWorkspaceEvents());
        const source = FakeEventSource.instances[0];
        unmount();
        expect(source.close).toHaveBeenCalledTimes(1);
    });

    it('ignores malformed payloads instead of crashing', () => {
        const { result } = renderHook(() => useWorkspaceEvents());
        const source = FakeEventSource.instances[0];

        const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        act(() => {
            source.onmessage?.({ data: '{not-json' } as MessageEvent);
        });
        expect(result.current).toEqual([]);
        expect(spy).toHaveBeenCalled();
    });

    it('drops events with an unknown kind', () => {
        const { result } = renderHook(() => useWorkspaceEvents());
        const source = FakeEventSource.instances[0];

        const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        act(() => {
            source.onmessage?.({
                data: JSON.stringify({ kind: 'mystery', agent_id: 'X' }),
            } as MessageEvent);
        });
        expect(result.current).toEqual([]);
        expect(spy).toHaveBeenCalled();
    });
});
