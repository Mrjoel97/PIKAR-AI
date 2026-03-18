# Supabase Migration Reference

This document covers how to safely apply database migrations using Supabase MCP tools, validate them with advisory checks, and remediate any issues found.

## MCP Tools Overview

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__plugin_supabase_supabase__list_projects` | Find the pikar-ai project ID | Start of migration phase |
| `mcp__plugin_supabase_supabase__list_migrations` | See what migrations are already applied | Before and after applying |
| `mcp__plugin_supabase_supabase__list_tables` | Check table schema (columns, PKs, FKs) | Validate migration targets exist |
| `mcp__plugin_supabase_supabase__execute_sql` | Run read-only validation queries | Pre-migration checks |
| `mcp__plugin_supabase_supabase__apply_migration` | Apply DDL migrations | The actual migration |
| `mcp__plugin_supabase_supabase__get_advisors` | Security + performance advisory scan | Post-migration validation |
| `mcp__plugin_supabase_supabase__get_logs` | Check Postgres logs for errors | Post-migration diagnosis |

## Step-by-Step Migration Workflow

### 1. Discover Project ID

```
Tool: mcp__plugin_supabase_supabase__list_projects
```
Find the project named "pikar-ai" (or matching the SUPABASE_URL in `.env`). Save the `id` for all subsequent calls.

### 2. Audit Current Migration State

```
Tool: mcp__plugin_supabase_supabase__list_migrations
Params: { project_id: "<id>" }
```

This returns all migrations that have been applied to production. Compare this list against the local `supabase/migrations/` directory:

```bash
ls supabase/migrations/
```

Any local migration files NOT in the production list are "new" and need to be applied. Migrations are applied in filename order (they use timestamp prefixes like `20260318000000_`).

### 3. Pre-Migration Validation

For each new migration file, read its SQL content and validate:

**Structural checks (do manually by reading the SQL):**
- Does it use `IF NOT EXISTS` / `IF EXISTS` guards for CREATE/DROP?
- Does it wrap destructive operations in a transaction (`BEGIN`/`COMMIT`)?
- Does it reference tables/columns that should already exist?
- Does it include RLS policies for new tables?
- Does it avoid hardcoded IDs (use `gen_random_uuid()` or sequences instead)?

**Schema existence checks (use MCP):**
```
Tool: mcp__plugin_supabase_supabase__list_tables
Params: { project_id: "<id>", schemas: ["public"], verbose: true }
```
Verify that tables/columns referenced by the migration actually exist. For example, if the migration adds a foreign key to `users(id)`, confirm the `users` table exists and has an `id` column.

**Dry-run validation queries (use MCP):**
```
Tool: mcp__plugin_supabase_supabase__execute_sql
Params: { project_id: "<id>", query: "<validation query>" }
```

Example validation queries:
```sql
-- Check if a table exists before migration that adds a column to it
SELECT EXISTS (
  SELECT 1 FROM information_schema.tables
  WHERE table_schema = 'public' AND table_name = 'target_table'
);

-- Check if a column already exists (to avoid duplicate column errors)
SELECT EXISTS (
  SELECT 1 FROM information_schema.columns
  WHERE table_schema = 'public'
    AND table_name = 'target_table'
    AND column_name = 'new_column'
);

-- Check for naming conflicts
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'proposed_table_name';

-- Verify foreign key target exists
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'referenced_table'
  AND column_name = 'referenced_column';
```

### 4. Apply Migrations

Apply each new migration in order using the MCP tool:

```
Tool: mcp__plugin_supabase_supabase__apply_migration
Params: {
  project_id: "<id>",
  name: "<migration_name_in_snake_case>",
  query: "<full SQL content of the migration file>"
}
```

The `name` should come from the migration filename. For example:
- File: `20260318000000_self_improvement.sql`
- Name: `self_improvement`

Apply one migration at a time, in timestamp order. If a migration fails:
1. Read the error message carefully.
2. Do NOT skip it and move to the next one — migrations are sequential.
3. Fix the SQL issue (create a corrective migration if needed).
4. Retry.

### 5. Post-Migration Advisory Scan

This is the most important step. Run both advisory checks immediately after migration:

**Security advisories:**
```
Tool: mcp__plugin_supabase_supabase__get_advisors
Params: { project_id: "<id>", type: "security" }
```

Common security findings after migrations:
- **Missing RLS policies**: New tables created without `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` and without policies. This means the table is accessible to any authenticated user via PostgREST.
- **Exposed to anon role**: Table or function accessible to the `anon` role without intent.
- **Insecure function**: Function created with `SECURITY DEFINER` without proper validation.

**Performance advisories:**
```
Tool: mcp__plugin_supabase_supabase__get_advisors
Params: { project_id: "<id>", type: "performance" }
```

Common performance findings after migrations:
- **Missing indexes**: New columns used in WHERE/JOIN clauses without indexes.
- **Table bloat**: Large tables that need VACUUM.
- **Duplicate indexes**: Redundant indexes that waste space and slow writes.

### 6. Remediate Advisories

**Security advisories are BLOCKERS** — do not deploy until they are resolved.

For missing RLS policies, create and apply a corrective migration:

```sql
-- Example: Enable RLS on a new table
ALTER TABLE public.new_table ENABLE ROW LEVEL SECURITY;

-- Example: Add a basic authenticated-user policy
CREATE POLICY "Users can view own data"
  ON public.new_table
  FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own data"
  ON public.new_table
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);
```

Apply the corrective migration:
```
Tool: mcp__plugin_supabase_supabase__apply_migration
Params: {
  project_id: "<id>",
  name: "fix_rls_for_<table_name>",
  query: "<corrective SQL>"
}
```

Then re-run the security advisory check to confirm the fix:
```
Tool: mcp__plugin_supabase_supabase__get_advisors
Params: { project_id: "<id>", type: "security" }
```

**Performance advisories are WARNINGS** — report them to the user but do not block deployment unless critical (e.g., missing primary key index).

For missing indexes, you may create them:
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_table_column
  ON public.table_name (column_name);
```

Note: use `CONCURRENTLY` to avoid locking the table during index creation.

### 7. Verify Migration Integrity

After all migrations and remediations are applied:

```
Tool: mcp__plugin_supabase_supabase__list_migrations
Params: { project_id: "<id>" }
```

Confirm all new migrations appear in the list with successful status.

### 8. Check Postgres Logs

```
Tool: mcp__plugin_supabase_supabase__get_logs
Params: { project_id: "<id>", service: "postgres" }
```

Look for:
- ERROR level messages related to the migration
- WARNING messages about deprecated features
- FATAL messages indicating connection issues
- Any pattern of repeated errors that started after migration

### 9. Post-Deploy Re-Check

After the application is deployed and running against the new schema, run the advisory checks one more time:

```
Tool: mcp__plugin_supabase_supabase__get_advisors (security)
Tool: mcp__plugin_supabase_supabase__get_advisors (performance)
```

This catches issues that only appear when the application interacts with the new schema — for example, the app might create new tables at runtime, or the app's query patterns might reveal missing indexes.

## Common Migration Pitfalls

| Pitfall | How to Catch | Fix |
|---------|-------------|-----|
| Table without RLS | `get_advisors(security)` | `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + policies |
| Missing foreign key index | `get_advisors(performance)` | `CREATE INDEX CONCURRENTLY` |
| Column type mismatch | `list_tables(verbose)` before migration | Fix the migration SQL |
| Dropped column still referenced | App deployment after migration | Deploy app code AFTER migration, not before |
| Duplicate migration name | `apply_migration` error | Rename the migration file |
| Missing IF NOT EXISTS | `apply_migration` error on re-run | Add guard clause |
| Function without search_path | `get_advisors(security)` | `SET search_path = ''` in function |

## Migration Ordering Rules

Migrations must be applied in this order relative to deployment:

1. **Schema additions** (new tables, columns, indexes) — apply BEFORE deploying new app code, because the app may expect the new schema.
2. **Data migrations** (backfills, transformations) — apply AFTER schema additions but BEFORE app deployment if the app requires the data.
3. **Schema removals** (drop columns, tables) — apply AFTER deploying new app code that no longer references the removed objects. This prevents the running app from crashing on missing columns.

The ship-it pipeline applies migrations in Phase 4 (before deployment in Phase 11) — this means it handles cases 1 and 2 correctly. For case 3 (removals), warn the user that the old app version must be deployed first without the removal, then a second deployment with the removal migration.
