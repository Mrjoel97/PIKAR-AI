# Workflow Schema Contract v1

Status: frozen for program execution (Phase 0 `P0-T02`).

## Template Object

Required fields:
- `name`: `string`
- `description`: `string`
- `category`: `string`
- `phases`: `Phase[]`

Lifecycle metadata (program target state):
- `template_key`: `string`
- `version`: `integer`
- `lifecycle_status`: `draft | published | archived`
- `is_generated`: `boolean`
- `personas_allowed`: `string[]`
- `created_by`: `string`
- `published_by`: `string | null`
- `published_at`: `string | null` (`ISO-8601`)

## Phase Object

Required fields:
- `name`: `string`
- `steps`: `Step[]`

## Step Object

Required fields:
- `name`: `string`
- `tool`: `string` (must resolve in registry)

Optional fields:
- `description`: `string`
- `required_approval`: `boolean`
- `retry_policy`: object
- `timeout_seconds`: `integer`
- `parallel_group`: `string`

Execution metadata (program target state):
- `phase_index`: `integer`
- `step_index`: `integer`
- `attempt_count`: `integer`
- `tool_name`: `string`
- `tool_input_hash`: `string`
- `idempotency_key`: `string`
- `approval_request_id`: `string | null`

## Publish Rules

A template can be published only if:
- every step has a non-empty `tool`,
- no deprecated tool is used,
- every step tool resolves in registry,
- schema validation passes.

## Environment Guards

Production defaults:
- `WORKFLOW_STRICT_TOOL_RESOLUTION=true`
- `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD=true`

## Source of Truth

- Runtime validator: `scripts/verify/validate_workflow_templates.py`
- Program baseline generator: `scripts/verify/generate_workflow_baseline.py`
- Database constraints: `supabase/migrations/0050_workflow_template_quality_guards.sql`
