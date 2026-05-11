// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Per-kind Zod schemas for workflow node config validation
 * (Phase 110 — Plan 04).
 *
 * Mirrors the server-side Pydantic per-kind config schemas in
 * ``app/workflows/graph_validation.py``. Kinds that execute in Phase 110
 * (trigger, agent-action, output) get tight schemas; the four Phase 3/4
 * kinds (condition, parallel, merge, human-approval) ship with permissive
 * placeholders so users can drag them onto the canvas and save without
 * errors. Phase 3/4 will tighten these without breaking Plan 04's
 * frontend (the schema object is the single source of truth for rule-7
 * client-side validation).
 *
 * Used by:
 *   - useGraphValidation.ts (rule 7 — config valid for kind)
 *   - NodePropertiesDrawer.tsx (per-field inline error rendering)
 *
 * Note: this file does NOT use react-hook-form. Per CONTEXT.md Claude's
 * Discretion #2, properties drawer uses raw <input> + useState +
 * Zod.safeParse on blur. Simpler, fewer deps, matches existing codebase.
 */

import { z } from 'zod';

import type { NodeKind } from '@/services/workflows';

/** Phase 110 trigger config: tight on trigger_type, permissive on extras. */
export const TriggerConfigSchema = z
    .object({
        trigger_type: z
            .enum(['manual', 'schedule', 'event'])
            .optional(),
    })
    .passthrough();

/** Phase 110 agent-action config: tool_name is required. */
export const AgentActionConfigSchema = z
    .object({
        tool_name: z.string().min(1, 'Tool name is required'),
        arguments: z.record(z.string(), z.unknown()).default({}),
        agent_role: z.string().optional(),
    })
    .passthrough();

/** Phase 110 output config: optional output_format, permissive on extras. */
export const OutputConfigSchema = z
    .object({
        output_format: z.string().optional(),
    })
    .passthrough();

/**
 * Permissive placeholder for condition/parallel/merge/human-approval.
 * Phase 3/4 will tighten these individually. Saving a graph with these
 * kinds in Phase 110 produces no rule-7 errors regardless of config.
 */
const PermissiveConfigSchema = z.object({}).passthrough();

/**
 * Map of node kind → Zod schema. The single source of truth for rule-7
 * validation on the client. Server-side equivalent lives in
 * ``app/workflows/graph_validation.py:_CONFIG_SCHEMAS``.
 */
export const CONFIG_SCHEMAS: Record<NodeKind, z.ZodTypeAny> = {
    trigger: TriggerConfigSchema,
    'agent-action': AgentActionConfigSchema,
    output: OutputConfigSchema,
    condition: PermissiveConfigSchema,
    parallel: PermissiveConfigSchema,
    merge: PermissiveConfigSchema,
    'human-approval': PermissiveConfigSchema,
};

/**
 * Validate a single node's config object against its per-kind schema.
 * Returns Zod's safeParse result so callers can read ``.success``
 * synchronously and surface ``.error.issues`` without try/catch.
 *
 * Unknown kinds short-circuit to a permissive parse (matches server
 * behavior — unknown kinds silently skip rule 7).
 *
 * Note: Zod v4 renamed/removed the previous ``SafeParseReturnType`` export.
 * We derive the return type from ``safeParse`` directly so this stays
 * portable across Zod majors.
 */
export type ValidateNodeConfigResult = ReturnType<
    z.ZodTypeAny['safeParse']
>;

export function validateNodeConfig(
    kind: NodeKind,
    config: unknown,
): ValidateNodeConfigResult {
    const schema = CONFIG_SCHEMAS[kind] ?? PermissiveConfigSchema;
    return schema.safeParse(config ?? {});
}
