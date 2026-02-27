# Stack Traceability

## Files

- `app\routers\workflows.py`: present
- `app\routers\initiatives.py`: present
- `app\workflows\engine.py`: present
- `app\services\edge_functions.py`: present
- `frontend\src\app\dashboard\workflows\templates\page.tsx`: present
- `frontend\src\app\dashboard\journeys\page.tsx`: present
- `frontend\src\services\workflows.ts`: present
- `supabase\migrations\0040_user_journeys_workflow_and_outcomes.sql`: present
- `supabase\migrations\0050_workflow_template_quality_guards.sql`: present
- `supabase\migrations\0051_workflow_lifecycle_and_execution_metadata.sql`: present
- `supabase\migrations\0057_workflow_readiness_registry.sql`: present
- `supabase\migrations\0058_journey_readiness_view.sql`: present

## Frontend Contracts

- `journeys_calls_from_journey`: `True`
- `journeys_calls_start_journey_workflow`: `True`
- `journeys_outcomes_modal_present`: `True`
- `workflow_service_start_endpoint`: `True`
- `workflow_service_exec_details_endpoint`: `True`
- `workflow_service_approve_endpoint`: `True`
- `workflow_service_sse_endpoint`: `True`

## Backend Contracts

- `workflows_start_route`: `True`
- `workflows_events_route`: `True`
- `workflows_approve_route`: `True`
- `initiatives_from_journey_route`: `True`
- `initiatives_start_journey_workflow_route`: `True`
- `workflow_engine_edge_callback`: `True`
- `workflow_engine_async_trigger`: `True`
- `edge_function_client_execute_workflow`: `True`
- `edge_function_requires_service_role_key`: `True`

## Class Presence

- `WorkflowEngine`: `True`
- `EdgeFunctionClient`: `True`
- `StartWorkflowRequest`: `True`
- `ApproveStepRequest`: `True`
- `CreateFromJourneyRequest`: `True`
