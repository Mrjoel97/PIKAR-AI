# Plan: Phase 2 - Database Alignment

**Objective:** Make Supabase migrations, deployed schema, and Python code agree with each other. Remove stale Alembic/SQLAlchemy drift and keep scope to DB-01 through DB-04.

## Scope Rules
- No new product features.
- Supabase migrations become the only schema authority.
- Prefer deleting dead database code over preserving legacy paths.
- Verify real schema state before creating new DDL.

## 1. Audit Schema Truth
**Goal:** establish one canonical view of reality before editing code.

**Tasks:**
- Compare local/deployed Supabase schema to `supabase/migrations`.
- Treat `supabase/migrations/20260308120000_content_bundle_workspace_contract.sql` as the starting point for DB-01 because it already defines `content_bundles`, `content_bundle_deliverables`, and `workspace_items` with RLS and indexes.
- Compare `supabase/migrations/0019_create_skills.sql` to `deployment/terraform/sql/skills_schema.sql` and document every mismatch.
- Confirm whether `custom_skills` is active schema debt or dead code. If active, fold it into the same alignment pass; if dead, remove the code path.
- Verify workflow/session tables and metadata columns already assumed by live runtime code so Phase 2 closes old Alembic drift across the real persistence surface, not just the new content tables.
- Update stale docs/planning notes that still describe already-created tables as missing.

**Files:**
- `supabase/migrations/0019_create_skills.sql`
- `supabase/migrations/20260308120000_content_bundle_workspace_contract.sql`
- `supabase/migrations/0005_sessions.sql`
- `supabase/migrations/0051_workflow_lifecycle_and_execution_metadata.sql`
- `deployment/terraform/sql/skills_schema.sql`
- `docs/backend_analysis_report.md`

## 2. Land Canonical Supabase Migrations
**Goal:** satisfy DB-01 and DB-02 without duplicate-table churn.

**Tasks:**
- Verify the three content/workspace tables are actually present in the target schema and match current writers/readers.
- Add `skills.agent_ids` as `jsonb` per phase context, with safe backfill/default handling.
- Add the required GIN index for `skills.agent_ids`.
- If any environment already has `agent_ids` as `text[]`, normalize it in migration instead of recreating it.
- Add any missing constraints or FK/index fixes only where active code depends on them.
- Add or tighten Pydantic/request-model validation anywhere this phase changes accepted database-backed fields.
- Preserve the phase decisions on RLS, `created_at`, `updated_at`, and `created_by` where applicable.
- Verify workflow template/session schema still matches runtime expectations before declaring schema alignment complete.

**Code paths that must match the final schema:**
- `app/services/content_bundle_service.py`
- `app/agents/tools/media.py`
- `app/mcp/tools/canva_media.py`
- `frontend/src/components/dashboard/ActiveWorkspace.tsx`
- `frontend/src/contexts/ChatSessionContext.tsx`
- `frontend/src/hooks/useAgentChat.ts`
- `app/skills/database_loader.py`
- `app/skills/custom_skills_service.py`
- `app/persistence/supabase_session_service.py`
- `app/workflows/engine.py`
- `app/fast_api_app.py`

## 3. Remove Legacy Migration Paths
**Goal:** satisfy DB-03 by removing Alembic and other known-divergent migration authorities.

**Tasks:**
- Delete or retire:
  - `alembic.ini`
  - `app/database/migrations/env.py`
  - `app/database/migrations/versions/001_initial.py`
  - `app/database/run_migration.py`
- Remove any runtime, startup, CI, or docs references to Alembic.
- Remove legacy dependency declarations that keep advertising Alembic/ORM migration workflows once the code is gone.
- Update developer guidance to use Supabase CLI only.
- Translate the roadmap's old `alembic upgrade head` success check into: no Alembic entrypoints remain and Supabase migration flow is documented.

**Files to inspect:**
- `CLAUDE.md`
- `pyproject.toml`
- `app/database/__init__.py`
- any scripts or Make targets that mention Alembic

## 4. Delete or Prove the ORM Surface
**Goal:** satisfy DB-04 with the smallest possible Python database surface.

**Tasks:**
- Inventory all imports of `app/database/models/__init__.py` and `app/database/__init__.py`.
- Default decision: remove ORM models and sync SQLAlchemy helpers unless a live non-Alembic code path proves they are needed.
- If any ORM model/helper is retained, align it to the real Supabase schema and document why deletion was unsafe.
- Remove `Base.metadata.create_all()` and `drop_all()` helpers.
- Remove `app/database/__init__.py` entirely if no live caller needs it after Alembic cleanup.
- Patch any remaining imports so runtime code uses supported Supabase paths only.

## 5. Verification
**Schema:**
- Run `scripts/verify/check_migrations.py` if still applicable.
- Run `supabase db push --local`.
- Verify directly that:
  - `skills.agent_ids` exists with the intended type/default/index
  - `content_bundles`, `content_bundle_deliverables`, and `workspace_items` are queryable
  - workflow metadata columns expected by runtime exist, including `template_key`, `version`, `lifecycle_status`, `is_generated`, `personas_allowed`, and `published_at`
  - session tables match the canonical Supabase contract from `0005_sessions.sql`
  - RLS exists for new/normalized tables

**Tests and verification commands:**
- `uv run pytest tests/unit/test_content_bundle_service.py -q`
- `uv run pytest tests/unit/test_media_routing.py -q`
- `uv run pytest tests/unit/test_user_workflow_storage.py -q`
- `uv run pytest tests/integration/test_concurrent_session_events.py -q`
- `uv run pytest tests/integration/test_rls_edge_function_config.py -q`
- `uv run python scripts/verify/test_persistence.py`
- `uv run python scripts/verify/validate_workflow_templates.py`
- add a focused DB smoke test for `DatabaseSkillLoader`
- add an integration test that `register_media_output()` creates linked rows in all three content/workspace tables

## Execution Order
1. Audit schema truth and choose canonical migration actions.
2. Land Supabase migration changes for `skills.agent_ids` and any still-active uncovered schema debt.
3. Patch backend/frontend code to the final table and column contract.
4. Remove Alembic, `run_migration.py`, and legacy dependency/docs references.
5. Delete or explicitly justify any remaining ORM surface, then rerun verification.

## Risks
- The repo may already define the "missing" tables even if a target environment does not.
- `agent_ids` may exist as `text[]` in some environments and need careful normalization to `jsonb`.
- `custom_skills` may be active hidden debt even though it is absent from the current migration chain.
- The worktree is already dirty, so implementation must isolate Phase 2 changes tightly.
