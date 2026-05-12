'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Dual-tab Guided/Advanced editor for `condition` node config
 * — Phase 111 Plan 04 (CONTEXT.md locked decision 1).
 *
 * The Guided tab provides three dropdowns (Field selector, Operator, Value)
 * that translate to JSONLogic JSON on every change. The Advanced tab opens
 * a CodeMirror 6 editor with JSON syntax highlighting for raw JSONLogic.
 *
 * Round-trip rule: switching from Advanced back to Guided attempts to parse
 * the JSONLogic back into the {field, operator, value} triple. If parsing
 * returns null (nested logic, computed operands, unknown ops), the Guided
 * tab stays read-only and shows "Complex expression — edit in Advanced tab".
 *
 * Save behavior: `config.expression` is ALWAYS persisted as JSONLogic JSON
 * (never as the {field, operator, value} triple). The server-side graph
 * executor (Plan 03) reads `config.expression` directly.
 *
 * UAT contract (ROADMAP criterion 4): the Guided form `[revenue] [>] [50000]`
 * produces exactly `{">": [{"var": "revenue"}, 50000]}` — verified by a
 * dedicated test in ConditionPropertiesEditor.test.tsx.
 */

import React, { useState, useMemo, useEffect, useRef } from 'react';

import CodeMirror from '@uiw/react-codemirror';
import { json as jsonLang } from '@codemirror/lang-json';

import {
    OPERATORS,
    translateGuidedToJsonLogic,
    translateJsonLogicToGuided,
    type GuidedExpression,
    type Operator,
} from './conditionExpressionTranslator';

// ---------------------------------------------------------------------------
// Props + types
// ---------------------------------------------------------------------------

export interface ConditionPropertiesEditorProps {
    node: {
        id: string;
        kind: 'condition';
        label: string;
        config: { expression?: unknown };
    };
    /**
     * Upstream agent-action node output keys, formatted as
     * `previous_outcomes.{node_id}.{output_key}`. Computed by the parent
     * (NodePropertiesDrawer) from the upstream subgraph walk + NODE_OUTPUT_KEYS.
     */
    upstreamFields: string[];
    onChange: (next: {
        label?: string;
        config?: { expression: unknown };
    }) => void;
}

type Mode = 'guided' | 'advanced';

/** Sentinel value in the Field dropdown that reveals the custom-field input. */
const CUSTOM_FIELD_SENTINEL = '__custom__';

/** Default Guided state when no expression exists yet. */
const EMPTY_GUIDED: GuidedExpression = {
    field: '',
    operator: '==',
    value: '',
};

// ---------------------------------------------------------------------------
// Coercion helper — Guided value strings come from <input> as strings; the
// translator needs typed primitives so the JSONLogic output is numerically
// correct.
// ---------------------------------------------------------------------------

const NUMBER_LITERAL_RE = /^[-+]?\d+(\.\d+)?$/;

function coerceValueForOp(
    raw: string | number | boolean,
    operator: Operator,
): string | number | boolean {
    // CSV operators keep the raw string — translator splits at translate time.
    if (operator === 'in' || operator === 'not in') return raw;
    if (typeof raw !== 'string') return raw;
    if (raw === 'true') return true;
    if (raw === 'false') return false;
    if (NUMBER_LITERAL_RE.test(raw)) return Number(raw);
    return raw;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ConditionPropertiesEditor({
    node,
    upstreamFields,
    onChange,
}: ConditionPropertiesEditorProps) {
    // Parse the initial expression once on mount.
    const initialGuided = useMemo(
        () =>
            node.config.expression !== undefined &&
            node.config.expression !== null
                ? translateJsonLogicToGuided(node.config.expression)
                : null,
        // We intentionally do not re-derive on every change to node.config;
        // doing so would clobber the user's in-progress edits. The parent
        // re-mounts this editor (by changing `key`) if it needs a hard reset.
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [],
    );

    const hasInitialExpression =
        node.config.expression !== undefined &&
        node.config.expression !== null &&
        // empty object {} counts as "no expression yet"
        !(
            typeof node.config.expression === 'object' &&
            !Array.isArray(node.config.expression) &&
            Object.keys(node.config.expression as object).length === 0
        );

    const initialMode: Mode = initialGuided
        ? 'guided'
        : hasInitialExpression
          ? 'advanced'
          : 'guided';

    const [mode, setMode] = useState<Mode>(initialMode);
    const [guided, setGuided] = useState<GuidedExpression>(
        initialGuided ?? EMPTY_GUIDED,
    );
    const [advancedJson, setAdvancedJson] = useState<string>(() => {
        if (hasInitialExpression) {
            return JSON.stringify(node.config.expression, null, 2);
        }
        return '{}';
    });
    const [roundTripFailed, setRoundTripFailed] = useState<boolean>(
        hasInitialExpression && !initialGuided,
    );
    const [jsonParseError, setJsonParseError] = useState<string | null>(null);
    const [customFieldMode, setCustomFieldMode] = useState<boolean>(() => {
        if (!initialGuided) return false;
        return !upstreamFields.includes(initialGuided.field);
    });
    const [customField, setCustomField] = useState<string>(
        initialGuided && !upstreamFields.includes(initialGuided.field)
            ? initialGuided.field
            : '',
    );

    // ----- Guided change handler -----
    // Push translated JSONLogic to the parent on every Guided edit, BUT only
    // while we're in Guided mode and not in round-trip-failed state. We use
    // an effect tied to (guided, mode, roundTripFailed) so the very first
    // mount doesn't fire an onChange (preserves the "save dirty" semantics
    // of the parent editor page).
    const isFirstMountRef = useRef(true);
    useEffect(() => {
        if (isFirstMountRef.current) {
            isFirstMountRef.current = false;
            return;
        }
        if (mode !== 'guided' || roundTripFailed) return;
        // Don't propagate when field is empty — there's nothing meaningful to save yet.
        if (!guided.field) return;
        const coerced: GuidedExpression = {
            ...guided,
            value: coerceValueForOp(guided.value, guided.operator),
        };
        const jsonDoc = translateGuidedToJsonLogic(coerced);
        onChange({ config: { expression: jsonDoc } });
        // onChange is intentionally omitted from deps — it's expected to be
        // stable across renders, and including it would cause infinite loops
        // if the parent re-creates the callback on every render.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [guided, mode, roundTripFailed]);

    // ----- Tab switching -----
    const switchToAdvanced = () => {
        if (mode === 'advanced') return;
        // Pre-populate CodeMirror with the translated JSONLogic, formatted.
        if (guided.field && !roundTripFailed) {
            const coerced: GuidedExpression = {
                ...guided,
                value: coerceValueForOp(guided.value, guided.operator),
            };
            const json = translateGuidedToJsonLogic(coerced);
            setAdvancedJson(JSON.stringify(json, null, 2));
        }
        setMode('advanced');
        setJsonParseError(null);
    };

    const switchToGuided = () => {
        if (mode === 'guided') return;
        // Attempt to parse the JSONLogic back into Guided shape.
        let parsed: unknown;
        try {
            parsed = JSON.parse(advancedJson);
        } catch {
            setRoundTripFailed(true);
            setMode('guided');
            return;
        }
        const parsedGuided = translateJsonLogicToGuided(parsed);
        if (parsedGuided) {
            // Convert primitive values back to a string for the <input>
            const stringValue: string =
                typeof parsedGuided.value === 'string'
                    ? parsedGuided.value
                    : String(parsedGuided.value);
            setGuided({
                field: parsedGuided.field,
                operator: parsedGuided.operator,
                value: stringValue,
            });
            // Update custom-field mode based on whether the parsed field
            // is in the upstreamFields list.
            if (!upstreamFields.includes(parsedGuided.field)) {
                setCustomFieldMode(true);
                setCustomField(parsedGuided.field);
            } else {
                setCustomFieldMode(false);
            }
            setRoundTripFailed(false);
        } else {
            setRoundTripFailed(true);
        }
        setMode('guided');
    };

    // ----- Advanced editor change handler -----
    const handleAdvancedChange = (text: string) => {
        setAdvancedJson(text);
        try {
            const parsed = JSON.parse(text);
            setJsonParseError(null);
            onChange({ config: { expression: parsed } });
        } catch (err) {
            setJsonParseError(
                err instanceof Error ? err.message : String(err),
            );
            // Do NOT propagate invalid JSON to the parent.
        }
    };

    // ----- Field dropdown change handler -----
    const handleFieldSelectChange = (
        e: React.ChangeEvent<HTMLSelectElement>,
    ) => {
        const v = e.target.value;
        if (v === CUSTOM_FIELD_SENTINEL) {
            setCustomFieldMode(true);
            setGuided({ ...guided, field: customField });
        } else {
            setCustomFieldMode(false);
            setGuided({ ...guided, field: v });
        }
    };

    const handleCustomFieldChange = (
        e: React.ChangeEvent<HTMLInputElement>,
    ) => {
        const v = e.target.value;
        setCustomField(v);
        setGuided({ ...guided, field: v });
    };

    const handleOperatorChange = (
        e: React.ChangeEvent<HTMLSelectElement>,
    ) => {
        setGuided({ ...guided, operator: e.target.value as Operator });
    };

    const handleValueChange = (
        e: React.ChangeEvent<HTMLInputElement>,
    ) => {
        setGuided({ ...guided, value: e.target.value });
    };

    const handleLabelChange = (
        e: React.ChangeEvent<HTMLInputElement>,
    ) => {
        onChange({ label: e.target.value });
    };

    // Compute the selected value in the Field dropdown for display.
    const fieldDropdownValue = customFieldMode
        ? CUSTOM_FIELD_SENTINEL
        : guided.field;

    // ----- Render -----
    return (
        <div
            className="space-y-3"
            data-testid="condition-properties-editor"
        >
            <div>
                <label
                    htmlFor={`cpe-label-${node.id}`}
                    className="mb-1 block text-xs font-medium text-slate-600"
                >
                    Label
                </label>
                <input
                    id={`cpe-label-${node.id}`}
                    type="text"
                    value={node.label}
                    onChange={handleLabelChange}
                    className="w-full rounded-md border border-slate-200 px-2.5 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
                    data-testid="cpe-label-input"
                />
            </div>

            {/* Tab switcher */}
            <div
                className="flex border-b border-slate-200"
                role="tablist"
                aria-label="Expression editor mode"
            >
                <button
                    type="button"
                    role="tab"
                    aria-selected={mode === 'guided'}
                    onClick={switchToGuided}
                    className={
                        'px-3 py-1.5 text-xs font-medium border-b-2 -mb-px transition-colors ' +
                        (mode === 'guided'
                            ? 'border-indigo-500 text-indigo-700'
                            : 'border-transparent text-slate-500 hover:text-slate-700')
                    }
                    data-testid="cpe-tab-guided"
                >
                    Guided
                </button>
                <button
                    type="button"
                    role="tab"
                    aria-selected={mode === 'advanced'}
                    onClick={switchToAdvanced}
                    className={
                        'px-3 py-1.5 text-xs font-medium border-b-2 -mb-px transition-colors ' +
                        (mode === 'advanced'
                            ? 'border-indigo-500 text-indigo-700'
                            : 'border-transparent text-slate-500 hover:text-slate-700')
                    }
                    data-testid="cpe-tab-advanced"
                >
                    Advanced (JSON)
                </button>
            </div>

            {/* Guided panel */}
            {mode === 'guided' && (
                <div
                    className="space-y-2"
                    data-testid="cpe-guided-panel"
                    role="tabpanel"
                    aria-label="Guided expression editor"
                >
                    {roundTripFailed && (
                        <div
                            className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"
                            data-testid="cpe-roundtrip-failed"
                            role="alert"
                        >
                            <p className="font-medium">
                                Complex expression
                            </p>
                            <p className="mt-1 leading-relaxed">
                                Edit in Advanced tab. The current JSONLogic
                                document uses nested logic or computed
                                operands and can&rsquo;t be expressed in the
                                Guided form.
                            </p>
                        </div>
                    )}

                    <div>
                        <label
                            htmlFor={`cpe-field-${node.id}`}
                            className="mb-1 block text-xs font-medium text-slate-600"
                        >
                            Field
                        </label>
                        <select
                            id={`cpe-field-${node.id}`}
                            value={fieldDropdownValue}
                            onChange={handleFieldSelectChange}
                            disabled={roundTripFailed}
                            className="w-full rounded-md border border-slate-200 px-2.5 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300 disabled:bg-slate-100 disabled:text-slate-400"
                            data-testid="cpe-guided-field-select"
                        >
                            <option value="">— select a field —</option>
                            {upstreamFields.map((f) => (
                                <option key={f} value={f}>
                                    {f}
                                </option>
                            ))}
                            <option value={CUSTOM_FIELD_SENTINEL}>
                                Custom field…
                            </option>
                        </select>
                    </div>

                    {customFieldMode && (
                        <div>
                            <label
                                htmlFor={`cpe-custom-${node.id}`}
                                className="mb-1 block text-xs font-medium text-slate-600"
                            >
                                Custom field name
                            </label>
                            <input
                                id={`cpe-custom-${node.id}`}
                                type="text"
                                value={customField}
                                onChange={handleCustomFieldChange}
                                disabled={roundTripFailed}
                                placeholder="e.g. revenue, user_context.tier"
                                className="w-full rounded-md border border-slate-200 px-2.5 py-1.5 font-mono text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300 disabled:bg-slate-100"
                                data-testid="cpe-guided-custom-field-input"
                            />
                        </div>
                    )}

                    <div>
                        <label
                            htmlFor={`cpe-op-${node.id}`}
                            className="mb-1 block text-xs font-medium text-slate-600"
                        >
                            Operator
                        </label>
                        <select
                            id={`cpe-op-${node.id}`}
                            value={guided.operator}
                            onChange={handleOperatorChange}
                            disabled={roundTripFailed}
                            className="w-full rounded-md border border-slate-200 px-2.5 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300 disabled:bg-slate-100"
                            data-testid="cpe-guided-operator-select"
                        >
                            {OPERATORS.map((op) => (
                                <option key={op} value={op}>
                                    {op}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label
                            htmlFor={`cpe-val-${node.id}`}
                            className="mb-1 block text-xs font-medium text-slate-600"
                        >
                            Value
                        </label>
                        <input
                            id={`cpe-val-${node.id}`}
                            type="text"
                            value={
                                typeof guided.value === 'string'
                                    ? guided.value
                                    : String(guided.value)
                            }
                            onChange={handleValueChange}
                            disabled={roundTripFailed}
                            placeholder={
                                guided.operator === 'in' ||
                                guided.operator === 'not in'
                                    ? 'comma-separated, e.g. premium,enterprise'
                                    : 'string, number, or true/false'
                            }
                            className="w-full rounded-md border border-slate-200 px-2.5 py-1.5 font-mono text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300 disabled:bg-slate-100"
                            data-testid="cpe-guided-value-input"
                        />
                    </div>
                </div>
            )}

            {/* Advanced panel */}
            {mode === 'advanced' && (
                <div
                    className="space-y-2"
                    data-testid="cpe-advanced-panel"
                    role="tabpanel"
                    aria-label="Advanced JSON expression editor"
                >
                    <p className="text-xs text-slate-500">
                        Raw JSONLogic. See{' '}
                        <a
                            href="https://jsonlogic.com/"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-600 underline"
                        >
                            jsonlogic.com
                        </a>{' '}
                        for syntax reference.
                    </p>
                    <div
                        className="overflow-hidden rounded-md border border-slate-200"
                        data-testid="cpe-advanced-codemirror-wrap"
                    >
                        <CodeMirror
                            value={advancedJson}
                            height="180px"
                            extensions={[jsonLang()]}
                            onChange={handleAdvancedChange}
                            basicSetup={{
                                lineNumbers: true,
                                foldGutter: false,
                                highlightActiveLine: false,
                            }}
                        />
                    </div>
                    {jsonParseError && (
                        <div
                            className="rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-700"
                            data-testid="cpe-advanced-parse-error"
                            role="alert"
                        >
                            Invalid JSON: {jsonParseError}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default ConditionPropertiesEditor;
