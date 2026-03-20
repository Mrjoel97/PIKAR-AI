# Workflow Baseline Report

- Generated at: `2026-03-20 17:42:26 UTC`
- Seeds scanned: `supabase\migrations\0009_seed_workflows.sql, supabase\migrations\0038_seed_yaml_workflows.sql`

## Coverage Snapshot

- Templates discovered: `68`
- Total phases: `234`
- Total steps: `261`
- Validator errors: `0`

## Category Distribution

- `content`: `1`
- `data`: `6`
- `finance`: `6`
- `hr`: `6`
- `legal`: `5`
- `marketing`: `10`
- `operations`: `6`
- `product`: `5`
- `sales`: `8`
- `strategy`: `10`
- `support`: `5`

## Critical Tool Implementation Status

- ✅ `approve_request` -> `approve_request`
- ✅ `execute_payroll` -> `execute_payroll`
- ✅ `process_payment` -> `process_payment_high_risk`
- ✅ `query_timesheets` -> `query_timesheets`
- ✅ `send_contract` -> `send_contract`
- ✅ `send_payment` -> `send_payment`
- ✅ `transfer_money` -> `transfer_money_high_risk`

## Placeholder Mapping Snapshot

- Registry entries mapped to `placeholder_tool`: `0`

## Validator Errors

- ✅ No validation errors.

## Notes

- This baseline is intended for Phase 0 tracking and weekly progress checks.
- Re-generate with: `uv run python scripts/verify/generate_workflow_baseline.py`
