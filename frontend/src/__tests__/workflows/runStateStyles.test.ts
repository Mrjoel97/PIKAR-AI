// @vitest-environment node
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for runStateStyles helpers — Phase 111 Plan 05.
 *
 * Helpers:
 *   - getNodeRunStateClasses(runState): returns Tailwind classes describing
 *     the live-run state of a graph node (active/completed/pending/skipped/
 *     failed). Driven by Discretion #7 — active node uses
 *     `animate-pulse ring-2 ring-amber-500`.
 *   - getEdgeRunStateStyle(runState): returns a React Flow Edge `style`
 *     object highlighting taken edges and muting not-taken edges (taken =
 *     emerald stroke + thicker weight; not_taken = slate + opacity 0.3 +
 *     dashed).
 *
 * These helpers are consumed by:
 *   - The 7 node components (TriggerNode, AgentActionNode, OutputNode,
 *     ConditionNode, ParallelNode, MergeNode, HumanApprovalNode) via
 *     `data.runState` — Task 05-01b extends each component to read this
 *     optional prop and append the returned className string to the
 *     outermost wrapper.
 *   - WorkflowGraphRunWidget (Task 05-03) for edge styling.
 */

import { describe, it, expect } from 'vitest';
import {
    getNodeRunStateClasses,
    getEdgeRunStateStyle,
} from '@/components/workflows/editor/runStateStyles';

describe('getNodeRunStateClasses', () => {
    it('returns_active_classes_for_active', () => {
        const cls = getNodeRunStateClasses('active');
        expect(cls).toContain('animate-pulse');
        expect(cls).toContain('ring-amber-500');
    });

    it('returns_completed_classes_for_completed', () => {
        const cls = getNodeRunStateClasses('completed');
        expect(cls).toContain('ring-emerald-500');
    });

    it('returns_pending_classes_for_pending', () => {
        const cls = getNodeRunStateClasses('pending');
        expect(cls).toContain('opacity-50');
    });

    it('returns_skipped_classes_for_skipped', () => {
        const cls = getNodeRunStateClasses('skipped');
        expect(cls).toContain('opacity-30');
        expect(cls).toContain('grayscale');
    });

    it('returns_failed_classes_for_failed', () => {
        const cls = getNodeRunStateClasses('failed');
        expect(cls).toContain('ring-red-500');
    });

    it('returns_empty_string_for_undefined', () => {
        const cls = getNodeRunStateClasses(undefined);
        expect(cls).toBe('');
    });
});

describe('getEdgeRunStateStyle', () => {
    it('returns_emerald_stroke_for_taken', () => {
        const style = getEdgeRunStateStyle('taken');
        expect(style.stroke).toBeDefined();
        expect(typeof style.stroke).toBe('string');
        // The taken-edge stroke is the emerald-500 hex
        expect(style.stroke).toBe('#10b981');
        // Taken edge should also be thicker than default
        expect(typeof style.strokeWidth).toBe('number');
        expect(style.strokeWidth as number).toBeGreaterThan(1);
    });

    it('returns_muted_style_for_not_taken', () => {
        const style = getEdgeRunStateStyle('not_taken');
        expect(style.opacity).toBeDefined();
        expect(style.opacity as number).toBeLessThan(0.5);
        expect(style.strokeDasharray).toBeDefined();
        expect(typeof style.strokeDasharray).toBe('string');
    });

    it('returns_empty_object_for_pending', () => {
        const style = getEdgeRunStateStyle('pending');
        expect(Object.keys(style).length).toBe(0);
    });

    it('returns_empty_object_for_undefined', () => {
        const style = getEdgeRunStateStyle(undefined);
        expect(Object.keys(style).length).toBe(0);
    });
});
