// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for NodePalette (Phase 110 Plan 04).
 *
 * Asserts the left-rail palette renders 7 draggable items grouped into
 * Trigger / Actions / Logic / Output (per Claude's Discretion #1 from
 * 110-CONTEXT.md). Phase-3/4 kinds carry a "Phase 3+" badge but stay
 * draggable per Option C.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import { NodePalette } from '@/components/workflows/editor/NodePalette';

describe('NodePalette', () => {
    it('renders 7 draggable palette items, one per node kind', () => {
        render(<NodePalette />);
        // Trigger
        expect(screen.getByTestId('palette-item-trigger')).toBeTruthy();
        // Action
        expect(screen.getByTestId('palette-item-agent-action')).toBeTruthy();
        // Logic (Phase 3/4)
        expect(screen.getByTestId('palette-item-condition')).toBeTruthy();
        expect(screen.getByTestId('palette-item-parallel')).toBeTruthy();
        expect(screen.getByTestId('palette-item-merge')).toBeTruthy();
        expect(screen.getByTestId('palette-item-human-approval')).toBeTruthy();
        // Output
        expect(screen.getByTestId('palette-item-output')).toBeTruthy();
    });

    it('groups items into Trigger / Actions / Logic / Output categories', () => {
        render(<NodePalette />);
        expect(screen.getByText(/^Trigger$/i)).toBeTruthy();
        expect(screen.getByText(/^Actions$/i)).toBeTruthy();
        expect(screen.getByText(/^Logic$/i)).toBeTruthy();
        expect(screen.getByText(/^Output$/i)).toBeTruthy();
    });

    it('sets draggable=true on every palette item', () => {
        render(<NodePalette />);
        const kinds = [
            'trigger',
            'agent-action',
            'condition',
            'parallel',
            'merge',
            'human-approval',
            'output',
        ];
        for (const kind of kinds) {
            const el = screen.getByTestId(`palette-item-${kind}`);
            expect(el.getAttribute('draggable')).toBe('true');
        }
    });

    it('dragstart calls dataTransfer.setData with application/reactflow + kind payload', () => {
        render(<NodePalette />);
        const triggerItem = screen.getByTestId('palette-item-trigger');
        const setData = vi.fn();
        // Build a synthetic dragStart event with a mock dataTransfer
        const dragEvent = new Event('dragstart', { bubbles: true }) as Event & {
            dataTransfer: { setData: typeof setData; effectAllowed: string };
        };
        // jsdom doesn't auto-populate dataTransfer on synthetic events
        Object.defineProperty(dragEvent, 'dataTransfer', {
            value: { setData, effectAllowed: '' },
            writable: true,
        });
        fireEvent(triggerItem, dragEvent);
        expect(setData).toHaveBeenCalled();
        const callArgs = setData.mock.calls[0];
        expect(callArgs[0]).toBe('application/reactflow');
        const payload = JSON.parse(callArgs[1] as string);
        expect(payload.kind).toBe('trigger');
        expect(typeof payload.label).toBe('string');
    });

    it('Phase 3/4 kinds carry a "Phase 3+" or similar coming-soon badge but stay draggable', () => {
        render(<NodePalette />);
        for (const kind of ['condition', 'parallel', 'merge', 'human-approval']) {
            const item = screen.getByTestId(`palette-item-${kind}`);
            // Draggable=true (per Option C)
            expect(item.getAttribute('draggable')).toBe('true');
            // Has a coming-soon hint somewhere in its subtree
            const text = item.textContent ?? '';
            // Accept any of the variations we may use ("Phase 3+", "Coming soon", "soon")
            expect(
                /phase\s*3|phase\s*4|coming\s*soon|soon/i.test(text),
            ).toBe(true);
        }
    });

    it('renders inside a data-testid="node-palette" container for selection', () => {
        render(<NodePalette />);
        expect(screen.getByTestId('node-palette')).toBeTruthy();
    });
});
