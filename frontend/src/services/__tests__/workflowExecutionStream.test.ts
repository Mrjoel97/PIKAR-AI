// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { subscribeToExecution } from '../workflowExecutionStream';

describe('subscribeToExecution', () => {
    let originalEventSource: typeof EventSource;

    beforeEach(() => {
        originalEventSource = (global as any).EventSource;
    });

    afterEach(() => {
        (global as any).EventSource = originalEventSource;
    });

    it('opens an EventSource at the right URL and delivers events', async () => {
        const events: any[] = [];
        let messageHandler: any = null;
        const fakeEventSource: any = {
            addEventListener: vi.fn((type: string, cb: any) => {
                if (type === 'message') messageHandler = cb;
            }),
            close: vi.fn(),
        };
        // eslint-disable-next-line prefer-arrow-callback
        const ctor = vi.fn().mockImplementation(function () { return fakeEventSource; });
        (global as any).EventSource = ctor;

        const unsubscribe = subscribeToExecution('exec-1', (evt) => events.push(evt));

        expect(ctor).toHaveBeenCalledWith('/workflows/executions/exec-1/stream');
        // Simulate an incoming event
        messageHandler({ data: JSON.stringify({ type: 'workflow.step.completed', step_id: 's1' }) });
        expect(events[0]).toEqual({ type: 'workflow.step.completed', step_id: 's1' });

        unsubscribe();
        expect(fakeEventSource.close).toHaveBeenCalled();
    });

    it('ignores malformed JSON gracefully', () => {
        let messageHandler: any = null;
        const fakeEventSource: any = {
            addEventListener: vi.fn((type, cb) => {
                if (type === 'message') messageHandler = cb;
            }),
            close: vi.fn(),
        };
        // eslint-disable-next-line prefer-arrow-callback
        (global as any).EventSource = vi.fn().mockImplementation(function () { return fakeEventSource; });

        const events: any[] = [];
        const unsubscribe = subscribeToExecution('exec-2', (evt) => events.push(evt));
        // Should not throw
        messageHandler({ data: 'not json' });
        expect(events).toHaveLength(0);
        unsubscribe();
    });
});
