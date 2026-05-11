// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Subscribes to a workflow execution's server-sent event stream.
 *
 * Returns an unsubscribe function that closes the EventSource. The supplied
 * callback receives each parsed event; malformed JSON is silently dropped.
 */

export interface WorkflowEvent {
    type: string;
    step_id?: string;
    status?: string;
    duration_ms?: number;
    [key: string]: unknown;
}

export function subscribeToExecution(
    executionId: string,
    onEvent: (event: WorkflowEvent) => void,
): () => void {
    const source = new EventSource(`/workflows/executions/${executionId}/stream`);
    const handler = (msg: MessageEvent) => {
        try {
            onEvent(JSON.parse(msg.data));
        } catch {
            // Malformed event — ignore.
        }
    };
    source.addEventListener('message', handler);
    return () => source.close();
}
