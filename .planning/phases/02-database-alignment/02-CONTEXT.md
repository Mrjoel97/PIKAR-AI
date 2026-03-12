# Phase 2: Database Alignment - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Ensure Supabase schema and codebase are in full agreement — create 3 missing tables, add missing column to skills, reconcile or remove Alembic, and update/remove ORM models to match reality. No new features, no new capabilities.

</domain>

<decisions>
## Implementation Decisions

### Alembic fate
- Remove Alembic entirely — delete config, migrations directory, and alembic dependency
- Supabase is the sole migration system going forward
- Claude to check for any auto-migration code at startup (e.g., `alembic upgrade head` in entrypoint) and remove it
- Claude to recommend a Supabase migration workflow (CLI vs Dashboard) based on what exists

### SQLAlchemy ORM models
- Claude's discretion: evaluate which ORM models are actively used in queries vs dead references
- Remove dead ORM models and their imports; update actively-used models to match Supabase schema
- Supabase schema always wins when there's a mismatch — never alter Supabase to match a model

### Dead code strategy
- Aggressively remove all dead code, but verify nothing breaks
- Patch all code paths that reference missing tables/columns so they work against Supabase
- For stubbed services: Claude decides per case — if close to working, create backing table; if pure placeholder, skip

### Input validation
- Add Pydantic validators and database constraints (NOT NULL, FK, CHECK) on new/updated fields
- Important for data integrity at 500k+ user scale

### New table policies
- RLS: Claude decides per table based on how each table is used in code
- All new tables get standard audit columns: created_at (timestamptz, default now()), updated_at (trigger), created_by (uuid FK to auth.users)
- Proactively add indexes on FK columns, user_id, and columns used in WHERE clauses
- Add GIN index on skills.agent_ids (jsonb) for fast agent-scoped lookups

### Claude's Discretion
- SQLAlchemy: keep or remove based on actual usage analysis
- RLS policy specifics per new table
- Whether stubbed services warrant table creation
- Auto-migration removal scope
- Supabase migration workflow recommendation (CLI vs Dashboard)

</decisions>

<specifics>
## Specific Ideas

- System must support 500k+ users — all schema decisions should favor performance and scalability
- Reliability and easy maintenance are top priorities
- "Inspect all dead code and delete them all but make sure it does not break the codebase"

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/database/models/__init__.py`: Current ORM model definitions (single file)
- `app/database/migrations/versions/001_initial.py`: Stale Alembic migration (to be removed)
- `app/services/content_bundle_service.py`: Service referencing content_bundles tables
- `app/skills/database_loader.py`: DatabaseSkillLoader referencing skills.agent_ids

### Established Patterns
- Supabase client used for most queries (not SQLAlchemy sessions)
- 76 tables with RLS policies — established security pattern
- Circuit breaker pattern on cache layer (Redis)
- Async throughout — all DB access should be async-safe

### Integration Points
- `app/database/__init__.py`: Session factory and connection setup — may reference Alembic
- `app/config/validation.py`: Startup validation — may check for Alembic
- `app/skills/` directory: Multiple files reference agent_ids on skills table
- `app/workflows/`: References content_bundle and workspace_item patterns
- 19 files reference content_bundle, workspace_item, or agent_ids

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-database-alignment*
*Context gathered: 2026-03-12*
