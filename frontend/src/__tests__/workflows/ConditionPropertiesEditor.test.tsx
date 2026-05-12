// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for ConditionPropertiesEditor — Phase 111 Plan 04.
 *
 * Dual-tab Guided/Advanced editor for `condition` node config (CONTEXT.md
 * decision 1). Mounts in Guided by default; Advanced uses CodeMirror 6 for
 * JSONLogic syntax highlighting. Round-trip rule: Guided becomes read-only
 * when Advanced JSON can't be decomposed into the {field, operator, value}
 * shape.
 *
 * CodeMirror is mocked with a plain <textarea> so jsdom doesn't choke on
 * the editor's canvas/DOM measurement code — same pattern Phase 110 used
 * for @xyflow/react in NodeCanvas.test.tsx.
 */

import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

// Mock CodeMirror BEFORE importing the component under test.
vi.mock('@uiw/react-codemirror', () => ({
    default: ({
        value,
        onChange,
    }: {
        value: string;
        onChange?: (v: string) => void;
        // CodeMirror passes more args; we only need value + onChange in tests.
    }) => (
        <textarea
            data-testid="cm-editor"
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
        />
    ),
}));
vi.mock('@codemirror/lang-json', () => ({
    json: () => ({}),
}));

import { ConditionPropertiesEditor } from '@/components/workflows/editor/ConditionPropertiesEditor';

interface OnChangeArg {
    label?: string;
    config?: { expression: unknown };
}

function makeNode(expression?: unknown) {
    return {
        id: 'c1',
        kind: 'condition' as const,
        label: 'If?',
        config: expression !== undefined ? { expression } : {},
    };
}

describe('ConditionPropertiesEditor — initial render', () => {
    it('renders_guided_tab_by_default_for_empty_expression', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode()}
                upstreamFields={[]}
                onChange={onChange}
            />,
        );
        const guidedTab = screen.getByTestId('cpe-tab-guided');
        const advancedTab = screen.getByTestId('cpe-tab-advanced');
        expect(guidedTab).toBeTruthy();
        expect(advancedTab).toBeTruthy();
        // Guided panel is visible by default
        expect(screen.getByTestId('cpe-guided-panel')).toBeTruthy();
    });

    it('renders_three_dropdowns: Field selector + Operator + Value input', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode()}
                upstreamFields={['previous_outcomes.a1.outcome_text']}
                onChange={onChange}
            />,
        );
        expect(screen.getByTestId('cpe-guided-field-select')).toBeTruthy();
        expect(screen.getByTestId('cpe-guided-operator-select')).toBeTruthy();
        expect(screen.getByTestId('cpe-guided-value-input')).toBeTruthy();
    });

    it('operator_dropdown_has_nine_options in expected order', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode()}
                upstreamFields={[]}
                onChange={onChange}
            />,
        );
        const select = screen.getByTestId(
            'cpe-guided-operator-select',
        ) as HTMLSelectElement;
        const optionValues = Array.from(select.options).map((o) => o.value);
        expect(optionValues).toEqual([
            '==',
            '!=',
            '<',
            '<=',
            '>',
            '>=',
            'contains',
            'in',
            'not in',
        ]);
    });

    it('field_selector_lists_upstream_fields_plus_custom_option', () => {
        const onChange = vi.fn();
        const fields = [
            'previous_outcomes.a1.outcome_text',
            'user_context.revenue',
        ];
        render(
            <ConditionPropertiesEditor
                node={makeNode()}
                upstreamFields={fields}
                onChange={onChange}
            />,
        );
        const select = screen.getByTestId(
            'cpe-guided-field-select',
        ) as HTMLSelectElement;
        const optionValues = Array.from(select.options).map((o) => o.value);
        // Each upstream field appears
        expect(optionValues).toContain('previous_outcomes.a1.outcome_text');
        expect(optionValues).toContain('user_context.revenue');
        // Custom sentinel option appears
        expect(optionValues).toContain('__custom__');
    });
});

describe('ConditionPropertiesEditor — Guided form interactions', () => {
    it('custom_field_input_propagates_value', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode()}
                upstreamFields={[]}
                onChange={onChange}
            />,
        );
        // Select __custom__ in field dropdown to reveal the custom-field input
        const select = screen.getByTestId('cpe-guided-field-select');
        fireEvent.change(select, { target: { value: '__custom__' } });
        const customInput = screen.getByTestId('cpe-guided-custom-field-input');
        fireEvent.change(customInput, { target: { value: 'revenue' } });
        // onChange should have fired with a JSONLogic containing var=revenue
        expect(onChange).toHaveBeenCalled();
        const lastCall = onChange.mock.calls[
            onChange.mock.calls.length - 1
        ][0] as OnChangeArg;
        const expr = lastCall.config?.expression as Record<string, unknown>;
        const operands = (expr['=='] ?? expr['>'] ?? expr['<']) as unknown[];
        // Default operator is ==, so we expect: {"==": [{"var": "revenue"}, "" or ...]}
        expect(operands?.[0]).toEqual({ var: 'revenue' });
    });

    it('roadmap_criterion_4_revenue_50000: Guided revenue > 50000 produces JSONLogic exactly', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode()}
                upstreamFields={[]}
                onChange={onChange}
            />,
        );
        // Field via custom
        const fieldSelect = screen.getByTestId('cpe-guided-field-select');
        fireEvent.change(fieldSelect, { target: { value: '__custom__' } });
        const customInput = screen.getByTestId('cpe-guided-custom-field-input');
        fireEvent.change(customInput, { target: { value: 'revenue' } });
        // Operator
        const opSelect = screen.getByTestId('cpe-guided-operator-select');
        fireEvent.change(opSelect, { target: { value: '>' } });
        // Value
        const valInput = screen.getByTestId('cpe-guided-value-input');
        fireEvent.change(valInput, { target: { value: '50000' } });

        const lastCall = onChange.mock.calls[
            onChange.mock.calls.length - 1
        ][0] as OnChangeArg;
        // EXACT shape — ROADMAP criterion 4 UAT contract
        expect(lastCall.config?.expression).toEqual({
            '>': [{ var: 'revenue' }, 50000],
        });
    });
});

describe('ConditionPropertiesEditor — tab switching + round-trip', () => {
    it('clicking_advanced_tab_pre_populates_with_translated_json', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode({ '>': [{ var: 'x' }, 5] })}
                upstreamFields={[]}
                onChange={onChange}
            />,
        );
        // Click Advanced tab
        fireEvent.click(screen.getByTestId('cpe-tab-advanced'));
        const editor = screen.getByTestId('cm-editor') as HTMLTextAreaElement;
        // CodeMirror mock surfaces value as the textarea's value
        const parsed = JSON.parse(editor.value);
        expect(parsed).toEqual({ '>': [{ var: 'x' }, 5] });
    });

    it('editing_advanced_json_propagates_to_onchange', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode({ '==': [{ var: 'x' }, 1] })}
                upstreamFields={[]}
                onChange={onChange}
            />,
        );
        // Switch to Advanced
        fireEvent.click(screen.getByTestId('cpe-tab-advanced'));
        const editor = screen.getByTestId('cm-editor');
        const newJson = '{"<":[{"var":"y"},10]}';
        fireEvent.change(editor, { target: { value: newJson } });
        // onChange should be called with parsed JSON
        const lastCall = onChange.mock.calls[
            onChange.mock.calls.length - 1
        ][0] as OnChangeArg;
        expect(lastCall.config?.expression).toEqual({
            '<': [{ var: 'y' }, 10],
        });
    });

    it('switching_back_to_guided_round_trips_when_simple', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode({ '>': [{ var: 'x' }, 5] })}
                upstreamFields={[]}
                onChange={onChange}
            />,
        );
        // Guided -> Advanced -> Guided
        fireEvent.click(screen.getByTestId('cpe-tab-advanced'));
        fireEvent.click(screen.getByTestId('cpe-tab-guided'));
        // No round-trip-failed message
        expect(screen.queryByTestId('cpe-roundtrip-failed')).toBeNull();
        // Value input shows the typed value (5)
        const valInput = screen.getByTestId(
            'cpe-guided-value-input',
        ) as HTMLInputElement;
        expect(valInput.value).toBe('5');
    });

    it('switching_back_to_guided_shows_readonly_when_complex', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode({ '==': [{ var: 'x' }, 1] })}
                upstreamFields={[]}
                onChange={onChange}
            />,
        );
        // Go to Advanced and type nested JSON
        fireEvent.click(screen.getByTestId('cpe-tab-advanced'));
        const editor = screen.getByTestId('cm-editor');
        fireEvent.change(editor, {
            target: {
                value:
                    '{"and":[{">":[{"var":"a"},1]},{"<":[{"var":"b"},10]}]}',
            },
        });
        // Switch back to Guided
        fireEvent.click(screen.getByTestId('cpe-tab-guided'));
        // Round-trip-failed message visible
        expect(screen.getByTestId('cpe-roundtrip-failed')).toBeTruthy();
        // Custom field input should be either disabled or absent (read-only mode)
        const guidedPanel = screen.getByTestId('cpe-guided-panel');
        expect(guidedPanel.textContent).toMatch(/Complex expression/i);
    });

    it('mounts_in_advanced_when_initial_expression_is_complex', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode({
                    and: [
                        { '>': [{ var: 'a' }, 1] },
                        { '<': [{ var: 'b' }, 10] },
                    ],
                })}
                upstreamFields={[]}
                onChange={onChange}
            />,
        );
        // Advanced editor visible
        expect(screen.getByTestId('cm-editor')).toBeTruthy();
        // Click guided -> see round-trip-failed
        fireEvent.click(screen.getByTestId('cpe-tab-guided'));
        expect(screen.getByTestId('cpe-roundtrip-failed')).toBeTruthy();
    });

    it('invalid_json_in_advanced_does_not_corrupt_state', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode({ '==': [{ var: 'x' }, 1] })}
                upstreamFields={[]}
                onChange={onChange}
            />,
        );
        fireEvent.click(screen.getByTestId('cpe-tab-advanced'));
        const editor = screen.getByTestId('cm-editor');
        const callsBefore = onChange.mock.calls.length;
        fireEvent.change(editor, { target: { value: '{' } });
        // onChange should NOT have been called with invalid JSON
        const newCalls = onChange.mock.calls.length - callsBefore;
        expect(newCalls).toBe(0);
        // Inline parse-error message shown
        expect(screen.getByTestId('cpe-advanced-parse-error')).toBeTruthy();
    });

    it('field_select_with_dropdown_value_updates_expression', () => {
        const onChange = vi.fn();
        render(
            <ConditionPropertiesEditor
                node={makeNode()}
                upstreamFields={['user_context.revenue']}
                onChange={onChange}
            />,
        );
        const fieldSelect = screen.getByTestId('cpe-guided-field-select');
        fireEvent.change(fieldSelect, {
            target: { value: 'user_context.revenue' },
        });
        const lastCall = onChange.mock.calls[
            onChange.mock.calls.length - 1
        ][0] as OnChangeArg;
        const expr = lastCall.config?.expression as Record<string, unknown>;
        const operands = expr['=='] as unknown[];
        expect(operands[0]).toEqual({ var: 'user_context.revenue' });
    });
});
