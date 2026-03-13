# Schema Ownership Inventory

Date: 2026-03-13
Status: Updated after Phase 2 implementation pass
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
| `mcp_integration_templates` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/mcp/user_integrations_schema.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/app/mcp/user_integrations_schema.sql) | Canonicalized |
| `user_mcp_integrations` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/mcp/user_config.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/mcp/user_config.py) | Canonicalized |
| `analytics_events` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/services/analytics_service.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/analytics_service.py) | Canonicalized |
| `analytics_reports` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/services/analytics_service.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/analytics_service.py) | Canonicalized |
| `user_activity_log` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/services/semantic_workflow_matcher.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/semantic_workflow_matcher.py), [app/services/journey_discovery.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/journey_discovery.py) | Canonicalized |
| `initiative_phase_history` | [supabase/migrations/20260313103000_schema_truth_alignment.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/20260313103000_schema_truth_alignment.sql) | [app/services/semantic_workflow_matcher.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/semantic_workflow_matcher.py), [app/agents/strategic/tools.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/agents/strategic/tools.py) | Canonicalized |

## Remaining Unresolved Live References

The objects below are still referenced by live code, but this pass did not find a canonical `CREATE TABLE` statement for them under `supabase/migrations/`.

| Object | Live references | Notes |
|---|---|---|
| `report_schedules` | [app/services/report_scheduler.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/report_scheduler.py), [app/agents/tools/report_scheduling.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/agents/tools/report_scheduling.py) | Policy/index fixes exist in [supabase/migrations/0028_fix_advisor_issues.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/0028_fix_advisor_issues.sql) and [supabase/migrations/0053_fix_advisors_part_3.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/0053_fix_advisors_part_3.sql), but canonical creation is still blocked by the missing owner for `spreadsheet_connections` |
| `generated_reports` | [app/services/report_scheduler.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/report_scheduler.py) | Policy/index fixes exist in [supabase/migrations/0028_fix_advisor_issues.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/0028_fix_advisor_issues.sql) and [supabase/migrations/0053_fix_advisors_part_3.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/0053_fix_advisors_part_3.sql), but canonical creation is still blocked by the missing owner for `spreadsheet_connections` |
| `spreadsheet_connections` | [app/services/report_scheduler.py](C:/Users/expert/Documents/PKA/Pikar-Ai/app/services/report_scheduler.py) | Live policy references exist, but this inventory still has no canonical create-table source for the parent table |

## Resolved Naming Mismatch

| Canonical object | Resolved reference | Status |
|---|---|---|
| `knowledge-vault` bucket | [frontend/src/components/knowledge-vault/KnowledgeVault.tsx](C:/Users/expert/Documents/PKA/Pikar-Ai/frontend/src/components/knowledge-vault/KnowledgeVault.tsx) now uses `knowledge-vault` | Fixed |

## Next Follow-Up

1. Find or create the canonical owner for `spreadsheet_connections`.
2. Once `spreadsheet_connections` is canonical, promote `report_schedules` and `generated_reports` into `supabase/migrations/`.
3. Remove or archive the legacy schema sources in [migrations/001_create_financial_records.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/migrations/001_create_financial_records.sql) and [app/mcp/user_integrations_schema.sql](C:/Users/expert/Documents/PKA/Pikar-Ai/app/mcp/user_integrations_schema.sql) after downstream environments are confirmed to be on the canonical chain.
4. Keep new schema changes out of `migrations/` and `app/*.sql` unless they are explicitly being migrated into `supabase/migrations/` in the same change.
