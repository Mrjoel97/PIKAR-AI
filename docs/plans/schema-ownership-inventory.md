# Schema Ownership Inventory

Date: 2026-03-13
Status: Updated after Phase 2 reporting alignment, local storage recovery, and Supabase link refresh
Validation: Fresh local DB reset succeeded on 2026-03-13 in both minimal mode and the configured local stack. The broader local stack now starts with `supabase start -x logflare,vector --ignore-health-check`, and bucket/policy bootstrap is verified after `supabase db reset --local --no-seed`.
Environment: Local storage startup is repaired on this Windows/Docker setup after upgrading the Supabase CLI to 2.75.0, refreshing the project with `supabase link`, and restarting the configured stack. The local runtime is now using `gotrue v2.187.0` and `storage-api v1.37.7`, `supabase_storage_Pikar-Ai` becomes healthy, `storage.buckets` and `storage.objects` are available, and the expected buckets/policies are present after reset. The main operational nuance is that `supabase db reset --local --no-seed` can return before storage finishes its post-reset health check; the container settles healthy within about 60 seconds.
Canonical rule: `supabase/migrations/` is the only approved production schema authority.

## Purpose

This inventory records which tables, views, and storage buckets are clearly owned by canonical Supabase migrations, which ones are still owned by out-of-band SQL, and which live code references still lack a canonical create-table source.

## Ownership Rules

- `supabase/migrations/*.sql` is the source of truth for production schema and storage.
- SQL under `migrations/` and `app/**.sql` is legacy or app-local unless explicitly migrated into `supabase/migrations/`.
- If live code references a table and this inventory cannot point to a canonical `CREATE TABLE` in `supabase/migrations/`, treat that object as unresolved.

## Canonical Objects Confirmed

| Object | Canonical owner | Live references | Status |
|---|---|---|---|
| `content_bundles` | [supabase/migrations/20260308120000_content_bundle_workspace_contract.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260308120000_content_bundle_workspace_contract.sql) | [app/services/content_bundle_service.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/content_bundle_service.py) | Canonical |
| `content_bundle_deliverables` | [supabase/migrations/20260308120000_content_bundle_workspace_contract.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260308120000_content_bundle_workspace_contract.sql) | [app/services/content_bundle_service.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/content_bundle_service.py) | Canonical |
| `workspace_items` | [supabase/migrations/20260308120000_content_bundle_workspace_contract.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260308120000_content_bundle_workspace_contract.sql) | [frontend/src/contexts/ChatSessionContext.tsx](C:/Users/expert/Documents/PKA/Pikar-Ai/frontend/src/contexts/ChatSessionContext.tsx), [frontend/src/components/dashboard/ActiveWorkspace.tsx](C:/Users/expert/Documents/PKA/Pikar-Ai/frontend/src/components/dashboard/ActiveWorkspace.tsx) | Canonical |
| `knowledge-vault` storage bucket | [supabase/migrations/0033_knowledge_vault_tables.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/0033_knowledge_vault_tables.sql), [supabase/migrations/0037_fix_storage_rls.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/0037_fix_storage_rls.sql), [supabase/migrations/0049_fix_knowledge_vault_storage_rls.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/0049_fix_knowledge_vault_storage_rls.sql) | [app/routers/vault.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/routers/vault.py), [frontend/src/components/vault/VaultInterface.tsx](C:/Users/expert/Documents/PKA/Pikar-Ai/frontend/src/components/vault/VaultInterface.tsx), [frontend/src/components/knowledge-vault/KnowledgeVault.tsx](C:/Users/expert/Documents/PKA/Pikar-Ai/frontend/src/components/knowledge-vault/KnowledgeVault.tsx) | Canonical |
| `financial_records` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/services/financial_service.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/financial_service.py), [app/services/dashboard_summary_service.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/dashboard_summary_service.py), [app/agents/financial/tools.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/agents/financial/tools.py) | Canonicalized |
| `mcp_integration_templates` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | Seed data owned by canonical migration; archived legacy reference at [user_integrations_schema.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/docs/archive/legacy-schema/user_integrations_schema.sql) | Canonicalized |
| `user_mcp_integrations` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/mcp/user_config.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/mcp/user_config.py) | Canonicalized |
| `analytics_events` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/services/analytics_service.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/analytics_service.py) | Canonicalized |
| `analytics_reports` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/services/analytics_service.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/analytics_service.py) | Canonicalized |
| `user_activity_log` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/services/semantic_workflow_matcher.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/semantic_workflow_matcher.py), [app/services/journey_discovery.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/journey_discovery.py) | Canonicalized |
| `initiative_phase_history` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/services/semantic_workflow_matcher.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/semantic_workflow_matcher.py), [app/agents/strategic/tools.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/agents/strategic/tools.py) | Canonicalized |
| `spreadsheet_connections` | [supabase/migrations/20260313173000_reporting_connection_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313173000_reporting_connection_alignment.sql) | [app/agents/tools/google_sheets.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/agents/tools/google_sheets.py), [app/services/report_scheduler.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/report_scheduler.py), [app/agents/tools/report_scheduling.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/agents/tools/report_scheduling.py) | Canonicalized |
| `report_schedules` | [supabase/migrations/20260313173000_reporting_connection_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313173000_reporting_connection_alignment.sql) | [app/services/report_scheduler.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/report_scheduler.py), [app/agents/tools/report_scheduling.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/agents/tools/report_scheduling.py) | Canonicalized |
| `generated_reports` | [supabase/migrations/20260313173000_reporting_connection_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313173000_reporting_connection_alignment.sql) | [app/services/report_scheduler.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/report_scheduler.py) | Canonicalized |

## Remaining Unresolved Live References

No unresolved live table references remain from this inventory pass.

## Resolved Naming Mismatch

| Canonical object | Resolved reference | Status |
|---|---|---|
| `knowledge-vault` bucket | [frontend/src/components/knowledge-vault/KnowledgeVault.tsx](C:/Users/expert/Documents/PKA/Pikar-Ai/frontend/src/components/knowledge-vault/KnowledgeVault.tsx) now uses `knowledge-vault` | Fixed |

## Archived Legacy Schema Sources

- [001_create_financial_records.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/docs/archive/legacy-schema/001_create_financial_records.sql) is archived from the old top-level `migrations/` directory.
- [user_integrations_schema.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/docs/archive/legacy-schema/user_integrations_schema.sql) is archived from the old `app/mcp/` path.

## Next Follow-Up

1. Run `supabase link` when convenient so the local version pins match the linked project and the lingering `gotrue` / `storage-api` mismatch warning goes away.
2. Keep new schema changes out of `migrations/` and `app/*.sql` unless they are explicitly being migrated into `supabase/migrations/` in the same change.