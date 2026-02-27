# Workflow Tool Inventory by Domain

Generated from baseline snapshot in `docs/plans/workflow_baseline.md`.

## Summary

- Critical high-risk tools implemented (non-placeholder): `approve_request`, `send_contract`, `query_timesheets`, `execute_payroll`, `process_payment`, `send_payment`, `transfer_money`.
- Remaining placeholder-mapped tools: `78`.
- Objective: replace placeholder-mapped tools with real implementations in Phase 1.

## Finance

Pending implementations:
- `create_forecast`
- `generate_forecast`
- `query_bank`
- `query_ledger`
- `update_budget`
- `update_ledger`
- `verify_po`

## HR

Pending implementations:
- `assign_training`
- `post_job_board`
- `submit_form`
- `update_hris`

## Legal / Compliance

Pending implementations:
- `approve_document`
- `review_policy`
- `run_audit`
- `scan_database`
- `send_file`
- `upload_document`
- `upload_file`

## Sales

Pending implementations:
- `create_contact`
- `listen_call`
- `manage_comments`
- `query_crm`
- `query_feedback`
- `score_lead`
- `send_form`
- `send_message`
- `start_call`
- `update_subscription`

## Operations

Pending implementations:
- `book_travel`
- `create_checklist`
- `create_folder`
- `create_po`
- `create_project`
- `create_task_list`
- `create_vendor`
- `log_shipment`
- `process_expense`
- `process_forms`
- `read_docs`
- `record_notes`
- `run_checklist`
- `run_script`
- `setup_monitoring`
- `update_asset_log`
- `update_inventory`
- `update_settings`

## Marketing / Growth

Pending implementations:
- `analyze_sentiment`
- `configure_ads`
- `create_alert`
- `create_form`
- `optimize_spend`
- `query_analytics`
- `query_usage`
- `send_guide`
- `update_cms`
- `update_gantt`

## Product / Engineering / Data

Pending implementations:
- `audit_logs`
- `calculate_score`
- `check_logs`
- `create_chart`
- `create_connection`
- `create_query`
- `create_record`
- `create_table`
- `create_tracking_plan`
- `create_pr`
- `deploy_service`
- `edit_document`
- `ocr_document`
- `process_data`
- `run_deployment`
- `run_test`
- `test_scenario`
- `train_model`
- `update_code`
- `update_record`

## Legacy / Cleanup

- `sent_contract` (legacy typo alias retained for backward compatibility; templates migrated to `send_contract`).

## Sequenced Implementation Order

1. Finance + legal/compliance pending tools.
2. HR tools tied to onboarding/recruitment/payroll journeys.
3. Operations and sales tools needed by highest-frequency templates.
4. Product/engineering/data long-tail tools.
