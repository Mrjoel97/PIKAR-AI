// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for NodePropertiesDrawer (Phase 110 Plan 04 + Phase 111 Plan 04).
 *
 * Per Claude's Discretion #2 Option C from 110-CONTEXT.md:
 *   - trigger / agent-action / output: fully editable forms
 *   - condition (Phase 111 Plan 04): full dual-tab ConditionPropertiesEditor
 *   - parallel / merge / human-approval: placeholder body
 *     ("Coming in Phase 4 — node saves but won't execute yet")
 *
 * The drawer uses raw <input> + onChange/onBlur + Zod safeParse — no
 * react-hook-form (per the same decision).
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

// Mock CodeMirror (used transitively by ConditionPropertiesEditor for the
// `condition` branch). Same pattern as ConditionPropertiesEditor.test.tsx.
vi.mock('@uiw/react-codemirror', () => ({
    default: ({
        value,
        onChange,
    }: {
        value: string;
        onChange?: (v: string) => void;
    }) => (
        <textarea
            data-testid="cm-editor"
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
        />
    ),
}));
vi.mock('@codemirror/lang-json', () => ({ json: () => ({}) }));

import { NodePropertiesDrawer } from '@/components/workflows/editor/NodePropertiesDrawer';
import type { GraphNode } from '@/services/workflows';

const noop = () => {};

describe('NodePropertiesDrawer', () => {
    it('shows empty-state copy when no node is selected', () => {
        render(
            <NodePropertiesDrawer node={null} onUpdate={noop} onClose={noop} />,
        );
        expect(screen.getByTestId('properties-drawer')).toBeTruthy();
        expect(
            screen.getByText(/select a node to edit/i),
        ).toBeTruthy();
    });

    it('renders label input + trigger_type dropdown for trigger node', () => {
        const node: GraphNode = {
            id: 't1',
            kind: 'trigger',
            label: 'Start',
            config: { trigger_type: 'manual' },
        };
        render(
            <NodePropertiesDrawer node={node} onUpdate={noop} onClose={noop} />,
        );
        const labelInput = screen.getByTestId('drawer-label-input');
        expect((labelInput as HTMLInputElement).value).toBe('Start');
        expect(screen.getByTestId('drawer-trigger-type-select')).toBeTruthy();
    });

    it('renders label + tool_name input for agent-action', () => {
        const node: GraphNode = {
            id: 'a1',
            kind: 'agent-action',
            label: 'Send email',
            config: { tool_name: 'send_gmail' },
        };
        render(
            <NodePropertiesDrawer node={node} onUpdate={noop} onClose={noop} />,
        );
        const toolInput = screen.getByTestId(
            'drawer-tool-name-input',
        ) as HTMLInputElement;
        expect(toolInput.value).toBe('send_gmail');
    });

    it('renders label input only for output node', () => {
        const node: GraphNode = {
            id: 'o1',
            kind: 'output',
            label: 'Done',
            config: {},
        };
        render(
            <NodePropertiesDrawer node={node} onUpdate={noop} onClose={noop} />,
        );
        expect(screen.getByTestId('drawer-label-input')).toBeTruthy();
        // No trigger/agent-action specific fields
        expect(screen.queryByTestId('drawer-trigger-type-select')).toBeNull();
        expect(screen.queryByTestId('drawer-tool-name-input')).toBeNull();
    });

    it('renders ConditionPropertiesEditor for condition node (Phase 111 Plan 04)', () => {
        const node: GraphNode = {
            id: 'c1',
            kind: 'condition',
            label: 'If',
            config: {},
        };
        render(
            <NodePropertiesDrawer node={node} onUpdate={noop} onClose={noop} />,
        );
        // Phase 111 replaced the "Coming in Phase 3/4" placeholder with the
        // dual-tab editor. Assert the editor is mounted and the placeholder
        // is gone.
        expect(
            screen.getByTestId('condition-properties-editor'),
        ).toBeTruthy();
        expect(screen.getByTestId('cpe-tab-guided')).toBeTruthy();
        expect(screen.getByTestId('cpe-tab-advanced')).toBeTruthy();
        expect(screen.queryByText(/Coming in Phase 3/i)).toBeNull();
    });

    it('shows "Coming in Phase 4" body for parallel / merge / human-approval', () => {
        for (const kind of ['parallel', 'merge', 'human-approval'] as const) {
            const node: GraphNode = {
                id: `${kind}-1`,
                kind,
                label: kind,
                config: {},
            };
            const { unmount } = render(
                <NodePropertiesDrawer
                    node={node}
                    onUpdate={noop}
                    onClose={noop}
                />,
            );
            expect(
                screen.getAllByText(/Coming in Phase/i).length,
            ).toBeGreaterThan(0);
            unmount();
        }
    });

    it('calls onUpdate with new label when label input changes', () => {
        const node: GraphNode = {
            id: 't1',
            kind: 'trigger',
            label: 'Start',
            config: {},
        };
        const onUpdate = vi.fn();
        render(
            <NodePropertiesDrawer
                node={node}
                onUpdate={onUpdate}
                onClose={noop}
            />,
        );
        const labelInput = screen.getByTestId('drawer-label-input');
        fireEvent.change(labelInput, { target: { value: 'Begin' } });
        expect(onUpdate).toHaveBeenCalled();
        const [id, updates] = onUpdate.mock.calls[0];
        expect(id).toBe('t1');
        expect(updates.label).toBe('Begin');
    });

    it('shows inline error when agent-action tool_name is empty (invalid)', () => {
        const node: GraphNode = {
            id: 'a1',
            kind: 'agent-action',
            label: 'A',
            // Missing tool_name; the drawer should surface the error
            config: {},
        };
        render(
            <NodePropertiesDrawer node={node} onUpdate={noop} onClose={noop} />,
        );
        // Drawer renders the validation error somewhere visible.
        expect(screen.getByTestId('drawer-config-error')).toBeTruthy();
    });

    it('calls onUpdate with new config.tool_name when tool_name changes', () => {
        const node: GraphNode = {
            id: 'a1',
            kind: 'agent-action',
            label: 'A',
            config: { tool_name: 'old' },
        };
        const onUpdate = vi.fn();
        render(
            <NodePropertiesDrawer
                node={node}
                onUpdate={onUpdate}
                onClose={noop}
            />,
        );
        const toolInput = screen.getByTestId('drawer-tool-name-input');
        fireEvent.change(toolInput, { target: { value: 'new_tool' } });
        expect(onUpdate).toHaveBeenCalled();
        // Find a call whose updates.config has tool_name === 'new_tool'.
        const matching = onUpdate.mock.calls.find((args) => {
            const updates = args[1] as { config?: { tool_name?: string } };
            return updates.config?.tool_name === 'new_tool';
        });
        expect(matching).toBeDefined();
    });
});
