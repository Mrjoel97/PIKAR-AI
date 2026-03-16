# Phase 2 Summary: Database Alignment

## Outcome

Completed the Phase 2 database-alignment plan in code, migrations, and local database verification. The codebase now treats Supabase SQL migrations as the canonical schema surface, aligns active skill persistence with the runtime contract, and removes the stale Alembic/SQLAlchemy migration path.

## What Changed

- Added `supabase/migrations/20260312183000_phase2_database_alignment.sql` to:
  - normalize `public.skills.agent_ids` to `jsonb`
  - create or align `public.custom_skills` for the active runtime service
  - add `created_by` plus update triggers/indexes to `content_bundles`, `content_bundle_deliverables`, and `workspace_items`
- Updated runtime code to persist and read the aligned schema:
  - `app/skills/database_loader.py`
  - `app/skills/custom_skills_service.py`
  - `app/skills/skill_creator.py`
  - `app/services/content_bundle_service.py`
  - `scripts/migrate_skills.py`
- Added focused regression coverage:
  - `tests/unit/test_database_skill_loader.py`
  - `tests/unit/test_content_bundle_service.py`
- Removed stale Alembic/SQLAlchemy migration surfaces and their pyproject dependencies:
  - `alembic.ini`
  - `app/database/__init__.py`
  - `app/database/migrations/env.py`
  - `app/database/migrations/versions/001_initial.py`
  - `app/database/models/__init__.py`
  - `app/database/run_migration.py`
  - dependency cleanup in `pyproject.toml`
- Updated `CLAUDE.md` to document Supabase CLI migrations as the schema source of truth.
- Patched legacy storage-policy migrations to stop depending on `storage.foldername(...)` path helpers during local verification attempts:
  - `supabase/migrations/0018_create_storage.sql`
  - `supabase/migrations/0033_knowledge_vault_tables.sql`
  - `supabase/migrations/0037_fix_storage_rls.sql`
  - `supabase/migrations/0049_fix_knowledge_vault_storage_rls.sql`
  - `supabase/migrations/20260307184500_restore_worker_media_alignment.sql`

## Verification

Passed tests:
- `uv run pytest tests/unit/test_database_skill_loader.py -q`
- `uv run pytest tests/unit/test_content_bundle_service.py -q`
- `uv run pytest tests/unit/test_skill_creator.py -q`
- `uv run pytest tests/unit/test_media_routing.py -q`
- `uv run pytest tests/unit/test_user_workflow_storage.py -q`
- `uv run pytest tests/unit/test_workflow_execution_contracts.py -q`

Local database verification:
- Host-level `supabase db push --local` and `supabase db reset --local` were unreliable on this workstation because the installed Supabase CLI is `v2.26.9`, the local stack only materialized the database container, and the migration role lacked `CREATE` on the `storage` schema.
- Bootstrapped the missing local `storage.buckets` and `storage.objects` tables inside the DB container using `supabase_admin`, transferred table ownership to `postgres`, and replayed the remaining migrations directly with `psql` inside the container.
- Confirmed the migration history includes:
  - `20260308120000` (`content_bundle_workspace_contract`)
  - `20260312183000` (`phase2_database_alignment`)
  - `20260313103000` (`schema_truth_alignment`)
- Confirmed final schema state in the local database:
  - `public.skills.agent_ids` is `jsonb`, `NOT NULL`, default `'[]'::jsonb`
  - `public.custom_skills.agent_ids` is `jsonb`, `NOT NULL`
  - `public.custom_skills.created_by` is `uuid`, `NOT NULL`
  - `public.content_bundles.created_by` is `uuid`, `NOT NULL`
  - `public.content_bundle_deliverables.created_by` is `uuid`, `NOT NULL`
  - `public.workspace_items.created_by` is `uuid`, `NOT NULL`
  - key indexes exist: `idx_skills_agent_ids`, `idx_custom_skills_agent_ids`, `idx_content_bundles_created_by`, `idx_content_bundle_deliverables_created_by`, `idx_workspace_items_created_by`

## Follow-up

- Refresh `uv.lock` in an environment with a real `uv lock` command.
- Upgrade the local Supabase CLI so future resets and pushes can run through the supported CLI path instead of the direct-container workaround.
