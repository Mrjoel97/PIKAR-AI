# Workflow Baseline Report

- Generated at: `2026-02-16 11:18:34 UTC`
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

- Registry entries mapped to `placeholder_tool`: `78`
- Placeholder tool keys:
  - `analyze_sentiment`
  - `approve_document`
  - `assign_training`
  - `audit_logs`
  - `book_travel`
  - `calculate_score`
  - `check_logs`
  - `configure_ads`
  - `create_alert`
  - `create_chart`
  - `create_checklist`
  - `create_connection`
  - `create_contact`
  - `create_folder`
  - `create_forecast`
  - `create_form`
  - `create_po`
  - `create_pr`
  - `create_project`
  - `create_query`
  - `create_record`
  - `create_table`
  - `create_task_list`
  - `create_tracking_plan`
  - `create_vendor`
  - `deploy_service`
  - `edit_document`
  - `generate_forecast`
  - `grant_access`
  - `listen_call`
  - `log_shipment`
  - `manage_comments`
  - `ocr_document`
  - `optimize_spend`
  - `post_job_board`
  - `process_data`
  - `process_expense`
  - `process_forms`
  - `query_analytics`
  - `query_bank`
  - `query_crm`
  - `query_feedback`
  - `query_ledger`
  - `query_usage`
  - `read_docs`
  - `record_notes`
  - `review_policy`
  - `run_audit`
  - `run_checklist`
  - `run_deployment`
  - `run_script`
  - `run_test`
  - `scan_database`
  - `score_lead`
  - `send_file`
  - `send_form`
  - `send_guide`
  - `send_message`
  - `sent_contract`
  - `setup_monitoring`
  - `start_call`
  - `submit_form`
  - `test_scenario`
  - `train_model`
  - `update_asset_log`
  - `update_budget`
  - `update_cms`
  - `update_code`
  - `update_gantt`
  - `update_hris`
  - `update_inventory`
  - `update_ledger`
  - `update_record`
  - `update_settings`
  - `update_subscription`
  - `upload_document`
  - `upload_file`
  - `verify_po`

## Validator Errors

- ✅ No validation errors.

## Notes

- This baseline is intended for Phase 0 tracking and weekly progress checks.
- Re-generate with: `uv run python scripts/verify/generate_workflow_baseline.py`
