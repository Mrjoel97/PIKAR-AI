# Ship-It Skill Walkthrough: Migration Deploy Scenario

**Task:** "I just finished adding a new braindump_sessions table with a migration file. Deploy everything to production and make sure the database is clean."

**Context:** The repo has a new migration file `supabase/migrations/20260318000000_self_improvement.sql`, changes to `app/services/self_improvement_engine.py`, and changes to `app/agents/tools/brain_dump.py`. We are on the `main` branch.

**Mode:** SIMULATION / DRY-RUN. No commands or MCP tools are actually executed.

---

## Phase 1: Scan and Assess

### Actions I Would Take

1. **Run `git status`** to see all modified, staged, and untracked files.

   Simulated output (from the git status snapshot provided):
   ```
   Modified:
     app/services/self_improvement_engine.py  (untracked/new)
     app/agents/tools/brain_dump.py           (would show in diff if modified)
   Untracked:
     supabase/migrations/20260318000000_self_improvement.sql
     app/services/self_improvement_engine.py
   ```

2. **Run `git diff` and `git diff --staged`** to see actual changes.

3. **Run `git log --oneline -5`** to see recent commit style.

   Simulated output:
   ```
   28d59ef feat: add client-side timer UI, session timeout handling, and summary card
   9fe109b fix: add missing get_error_and_escalation_instructions to shared_instructions
   ba1a34a Merge branch 'claude/tender-kapitsa': mobile responsiveness
   4da5409 feat: add session timer, DB tracking, and comprehensive brainstorm analysis
   07d0389 feat: add braindump_sessions table and braindump_analysis widget
   ```

4. **Categorize changes by domain:**
   - **backend**: `app/services/self_improvement_engine.py`, `app/agents/tools/brain_dump.py` (2 files)
   - **migrations**: `supabase/migrations/20260318000000_self_improvement.sql` (1 file)
   - **frontend**: none in this specific task scope (though git status shows frontend changes exist)
   - **config**: none
   - **tests**: none

5. **Report to user:**
   > "3 files changed across 2 domains (backend, migrations). 1 new migration file detected -- this triggers the Supabase Migration Gate in Phase 4."

6. **Flag migration files:** YES -- `supabase/migrations/20260318000000_self_improvement.sql` is a new, untracked file. Phase 4 is required.

**Note:** The git status snapshot also shows many other modified files (agent files, skill files, frontend config, etc.). I would ask the user:
> "Git status shows ~30+ modified/untracked files beyond the 3 you mentioned. Should I include all of these in the deployment, or only the self-improvement migration, self_improvement_engine.py, and brain_dump.py?"

For this walkthrough, I will assume the user says "deploy everything" and all changes are in scope. This also triggers the **Abort Condition** for >30 files changed, so I would confirm scope with the user before proceeding.

---

## Phase 2: Deployment Timing Guard

### Actions I Would Take

1. **Check project memory** for merge freezes or deployment blackouts.
   - No active merge freezes noted in MEMORY.md.

2. **Check current time:**
   ```bash
   date +"%H:%M %Z"
   ```
   Simulated output: `14:30 EST` (within business hours 7 AM - 10 PM).

3. **Check day of week:**
   ```bash
   date +"%u"
   ```
   Simulated output: `3` (Wednesday -- a weekday, safe to deploy).

4. **Check for active incidents** on Cloud Run or Vercel status pages.
   - Would attempt to check status pages if accessible. In simulation, assume no active incidents.

**Result:** All clear. Proceed to Phase 3.

---

## Phase 3: Quality Gates (Parallel Execution)

### Actions I Would Take

Since both backend and frontend files are modified (git status shows frontend changes), I would run BOTH quality gates in parallel.

#### Backend Quality Gate

I would run these commands in sequence (or as a single background job):

1. **`uv run ruff check app/ --fix`** -- Auto-fix Python lint issues.
   Simulated output: `Found 3 issues (3 fixed, 0 remaining)`

2. **`uv run ruff format app/`** -- Auto-format Python code.
   Simulated output: `12 files reformatted, 45 files left unchanged`

3. **`uv run codespell`** -- Catch spelling errors.
   Simulated output: no errors found.

4. **`uv run ty check .`** -- Python type checking.
   Simulated output: `0 errors, 0 warnings`

5. **`uv run python scripts/verify/validate_workflow_templates.py`** -- Workflow validation.
   Simulated output: `All workflow templates valid.`

6. **`uv run python scripts/verify/generate_workflow_baseline.py`** -- Baseline generation.
   Simulated output: `Baseline generated successfully.`

7. **`uv run pytest tests/unit -q`** -- Unit tests.
   Simulated output: `42 passed in 8.3s`

8. **`uv run pytest tests/integration -q`** -- Integration tests.
   Simulated output: `15 passed in 12.1s`

#### Frontend Quality Gate (in parallel)

1. **`cd frontend && npm run lint`** -- ESLint.
   Simulated output: no errors.

2. **`cd frontend && npx tsc --noEmit`** -- TypeScript type check.
   Simulated output: no errors.

3. **`cd frontend && npm test`** -- Frontend tests.
   Simulated output: `Tests: 8 passed, 8 total`

4. **`cd frontend && CI=1 NEXT_TELEMETRY_DISABLE=1 NEXT_PUBLIC_API_URL=http://localhost:8000 NEXT_PUBLIC_SUPABASE_URL=https://example.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_test_key npm run build`** -- Build verification.
   Simulated output: build succeeds.

#### After Both Complete

- Ruff auto-fix changed some files. These are noted for staging in Phase 6.
- Zero errors remain across all quality gates.

**Result:** Phase 3 PASSED.

---

## Phase 4: Supabase Migration Gate

**This phase is TRIGGERED** because `supabase/migrations/20260318000000_self_improvement.sql` is a new file.

This is the critical phase for this scenario. Here is the full step-by-step with exact MCP tool calls.

### Step 4.1: Identify the Project

**MCP Tool Call:**
```
Tool: mcp__plugin_supabase_supabase__list_projects
Parameters: {}
```

**Simulated Response:**
```json
[
  {
    "id": "abcdefghijklmnop",
    "name": "pikar-ai",
    "organization_id": "org_xyz",
    "region": "us-east-1",
    "created_at": "2025-12-01T00:00:00Z"
  }
]
```

**Action:** Save `project_id = "abcdefghijklmnop"` for all subsequent calls.

### Step 4.2: Check Current Migration State

**MCP Tool Call:**
```
Tool: mcp__plugin_supabase_supabase__list_migrations
Parameters: { "project_id": "abcdefghijklmnop" }
```

**Simulated Response:** A list of all applied migrations, up through `20260317000000_braindump_sessions`. The migration `20260318000000_self_improvement` is NOT in the list (it is new).

**Action:** Compare against local `supabase/migrations/` directory listing. Identify that the following migrations may be new (not yet applied in production):
- `20260318000000_self_improvement.sql` -- confirmed new
- `20260318100000_marketing_content_tools.sql` -- also present locally; need to check if applied

Note: There could be other recently-added migrations. The skill requires comparing the full list. For this walkthrough, I focus on `20260318000000_self_improvement.sql` as the primary new migration the user mentioned.

### Step 4.3: Validate Migration SQL

**Action:** Read the migration file content (already read above). Perform structural checks:

| Check | Result |
|-------|--------|
| Uses `IF NOT EXISTS` for CREATE TABLE? | YES -- all 4 tables use `CREATE TABLE IF NOT EXISTS` |
| Uses `IF EXISTS` for DROP? | N/A -- no DROP statements |
| Transaction wrapping (`BEGIN`/`COMMIT`)? | NO -- **this is a concern but not blocking** since Supabase `apply_migration` wraps each migration in a transaction automatically |
| References existing tables? | YES -- references `auth.users(id)` via foreign key in `interaction_logs` and `coverage_gaps` |
| Includes RLS policies for new tables? | YES -- all 4 tables have `ENABLE ROW LEVEL SECURITY` and CREATE POLICY statements |
| Avoids hardcoded IDs? | YES -- uses `gen_random_uuid()` |
| Index creation? | YES -- 11 indexes created, no `CONCURRENTLY` (fine for apply_migration context) |

**Schema existence checks via MCP:**

**MCP Tool Call:**
```
Tool: mcp__plugin_supabase_supabase__list_tables
Parameters: { "project_id": "abcdefghijklmnop", "schemas": ["public", "auth"], "verbose": true }
```

**Simulated Response:** Returns the list of existing tables. I would verify that `auth.users` exists and has an `id` column of type UUID (it does -- this is a standard Supabase table).

### Step 4.4: Dry-Run Validation

**MCP Tool Call 1** -- Check that the `interaction_logs` table does not already exist (to avoid conflicts):
```
Tool: mcp__plugin_supabase_supabase__execute_sql
Parameters: {
  "project_id": "abcdefghijklmnop",
  "query": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('interaction_logs', 'skill_scores', 'improvement_actions', 'coverage_gaps');"
}
```

**Simulated Response:**
```json
{ "rows": [] }
```
No naming conflicts. All 4 table names are available.

**MCP Tool Call 2** -- Verify the foreign key target `auth.users(id)` exists:
```
Tool: mcp__plugin_supabase_supabase__execute_sql
Parameters: {
  "project_id": "abcdefghijklmnop",
  "query": "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'auth' AND table_name = 'users' AND column_name = 'id';"
}
```

**Simulated Response:**
```json
{ "rows": [{ "column_name": "id", "data_type": "uuid" }] }
```
Foreign key target confirmed.

### Step 4.5: Apply the Migration

**MCP Tool Call:**
```
Tool: mcp__plugin_supabase_supabase__apply_migration
Parameters: {
  "project_id": "abcdefghijklmnop",
  "name": "self_improvement",
  "query": "<full SQL content of supabase/migrations/20260318000000_self_improvement.sql>"
}
```

The `query` parameter would contain the entire 175-line SQL file content, creating all 4 tables (`interaction_logs`, `skill_scores`, `improvement_actions`, `coverage_gaps`), their 11 indexes, and their RLS policies.

**Simulated Response:**
```json
{ "status": "success", "message": "Migration applied successfully" }
```

### Step 4.6: Post-Migration Advisory Scan

This is the most critical step. Run BOTH advisory types.

**MCP Tool Call 1 -- Security Advisory:**
```
Tool: mcp__plugin_supabase_supabase__get_advisors
Parameters: { "project_id": "abcdefghijklmnop", "type": "security" }
```

**Simulated Response (realistic scenario with an advisory):**
```json
[
  {
    "name": "rls_disabled_in_public",
    "title": "No RLS policies on public tables",
    "description": "The following tables in the public schema do not have RLS enabled: (none found for the new tables)",
    "detail": "All new tables have RLS enabled.",
    "remediation_url": "https://supabase.com/docs/guides/auth/row-level-security"
  },
  {
    "name": "insecure_auth_function",
    "title": "Function search_path not set",
    "description": "Some functions do not have search_path set, which could lead to schema injection.",
    "detail": "Functions: (pre-existing functions, not related to this migration)",
    "remediation_url": "https://supabase.com/docs/guides/database/functions#security"
  }
]
```

**Analysis:**
- The new tables (`interaction_logs`, `skill_scores`, `improvement_actions`, `coverage_gaps`) all have RLS enabled and policies defined in the migration SQL. No security blockers from the new migration.
- Any pre-existing security advisories (e.g., function search_path) are noted but not caused by this change. I would report these to the user but not block deployment.

**Handling a BLOCKING advisory scenario:** If the advisory had reported that one of the new tables lacked RLS (e.g., if the migration author forgot to add `ALTER TABLE coverage_gaps ENABLE ROW LEVEL SECURITY`), I would:

1. Create a corrective migration SQL:
   ```sql
   ALTER TABLE public.coverage_gaps ENABLE ROW LEVEL SECURITY;

   CREATE POLICY "coverage_gaps_user_access" ON public.coverage_gaps
     FOR ALL USING (auth.uid() = user_id);

   CREATE POLICY "coverage_gaps_service_access" ON public.coverage_gaps
     FOR ALL USING (auth.role() = 'service_role');
   ```

2. Apply it via MCP:
   ```
   Tool: mcp__plugin_supabase_supabase__apply_migration
   Parameters: {
     "project_id": "abcdefghijklmnop",
     "name": "fix_rls_for_coverage_gaps",
     "query": "<corrective SQL above>"
   }
   ```

3. Also save the corrective migration locally as a new file `supabase/migrations/20260318000001_fix_rls_for_coverage_gaps.sql` so the local state matches production.

4. Re-run the security advisory check to confirm the fix resolved the issue.

In this simulation, the migration already includes proper RLS, so no corrective migration is needed.

**MCP Tool Call 2 -- Performance Advisory:**
```
Tool: mcp__plugin_supabase_supabase__get_advisors
Parameters: { "project_id": "abcdefghijklmnop", "type": "performance" }
```

**Simulated Response:**
```json
[
  {
    "name": "missing_index_on_fk",
    "title": "Unindexed foreign keys",
    "description": "Foreign key columns without indexes can cause slow joins and cascading deletes.",
    "detail": "coverage_gaps.user_id references auth.users(id) but has no index.",
    "remediation_url": "https://supabase.com/docs/guides/database/postgres/indexes"
  }
]
```

**Analysis:**
- `coverage_gaps.user_id` is a foreign key to `auth.users(id)` but has no dedicated index. The existing indexes on `coverage_gaps` are on `(resolved, created_at)` and `(agent_id)`, but not on `user_id`.
- This is a WARNING, not a blocker. I would report it to the user:
  > "Performance advisory: `coverage_gaps.user_id` has no index. This could slow joins and cascading deletes. Consider adding `CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_coverage_gaps_user ON coverage_gaps(user_id);` in a follow-up migration. Reference: https://supabase.com/docs/guides/database/postgres/indexes"
- Similarly, `interaction_logs.user_id` does have an index (`idx_interaction_logs_user` on `(user_id, created_at DESC)`), so that is covered.
- I would NOT block deployment for this performance advisory.

### Step 4.7: Verify Migration Integrity

**MCP Tool Call:**
```
Tool: mcp__plugin_supabase_supabase__list_migrations
Parameters: { "project_id": "abcdefghijklmnop" }
```

**Simulated Response:** The migration list now includes `20260318000000_self_improvement` with a successful status. Confirmed applied.

### Step 4.8: Check Postgres Logs

**MCP Tool Call:**
```
Tool: mcp__plugin_supabase_supabase__get_logs
Parameters: { "project_id": "abcdefghijklmnop", "service": "postgres" }
```

**Simulated Response:** Recent logs showing the CREATE TABLE, CREATE INDEX, and ALTER TABLE statements executed successfully. No ERROR or FATAL messages related to the migration.

**Result:** Phase 4 PASSED. Migration applied successfully. Zero security blockers. One performance warning documented (missing index on `coverage_gaps.user_id`).

---

## Phase 5: Environment Variable Diff

### Backend -- Cloud Run

1. **Get current production env vars:**
   ```bash
   gcloud run services describe pikar-ai --region us-central1 --format="yaml(spec.template.spec.containers[0].env)"
   ```
   Simulated output: returns the list of env vars currently set in Cloud Run.

2. **Read `.env.example`** (already read above -- 176 lines of configuration).

3. **Compare the two lists.** Simulated finding: no new env vars were introduced by the self-improvement engine changes. The code uses existing `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, etc.

4. **Result:** No missing env vars for backend.

### Frontend -- Vercel

1. **Get current Vercel env vars:**
   ```bash
   cd frontend && vercel env ls
   ```

2. **Check `frontend/.env.example`** for expected `NEXT_PUBLIC_*` variables.

3. **Result:** No new frontend env vars required by this change.

**Result:** Phase 5 PASSED. No missing environment variables.

---

## Phase 6: Stage and Commit

### Actions I Would Take

1. **Run `git status`** again to see the full picture including auto-fix changes from Phase 3 (ruff fixed 3 issues and reformatted 12 files).

2. **Stage files selectively** (never blind `git add .`):
   ```bash
   # Backend Python changes
   git add app/services/self_improvement_engine.py
   git add app/services/interaction_logger.py
   git add app/agents/tools/brain_dump.py
   git add app/agents/tools/self_improve.py

   # Migration
   git add supabase/migrations/20260318000000_self_improvement.sql

   # Other modified backend files (auto-fixed by ruff)
   git add app/agent.py
   git add app/agents/compliance/agent.py
   git add app/agents/content/agent.py
   # ... (stage each modified app/ file individually)

   # Other modified files from git status
   git add app/agents/tools/agent_skills.py
   git add app/agents/tools/configuration.py
   git add app/agents/tools/integration_tools.py
   git add app/agents/tools/social.py
   git add app/agents/tools/tool_registry.py
   git add app/mcp/config.py
   git add app/mcp/integrations/email_service.py
   git add app/mcp/tools/form_handler.py
   git add app/mcp/tools/supabase_landing.py
   git add app/prompts/executive_instruction.txt
   git add app/routers/configuration.py
   git add app/skills/__init__.py
   git add app/skills/library.py
   git add app/skills/loader.py
   git add app/skills/professional_finance_legal.py
   git add app/skills/professional_marketing_sales.py
   git add app/skills/professional_operations_data.py
   git add app/skills/professional_pm_productivity_content.py
   git add app/social/publisher.py
   git add app/workflows/marketing.py
   git add app/.env.example

   # Frontend changes
   git add frontend/src/app/api/configuration/save-api-key/route.ts
   git add frontend/src/app/dashboard/configuration/page.tsx
   ```

   **Explicitly NOT staged:**
   - `.env` files with secrets
   - `.next/` (build artifacts)
   - `.playwright-cli/` (dev tooling)
   - `output/` (generated output)
   - `tiktok-demo.mp4` (large binary)
   - `skills/` directory (skill definitions, unless user confirms)

3. **Craft commit message** (following repo's `feat:` convention from recent commits):
   ```bash
   git commit -m "$(cat <<'EOF'
   feat: add self-improvement system with interaction logging and skill scoring

   Introduces 4 new database tables (interaction_logs, skill_scores,
   improvement_actions, coverage_gaps) for autonomous agent quality
   tracking. Includes the self-improvement engine service and interaction
   logger, plus updates to brain_dump tools and agent configurations.

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
   EOF
   )"
   ```

4. **Verify with `git status`** that the working tree is clean or only has intentionally untracked files.

**Result:** Phase 6 PASSED. Commit created.

---

## Phase 7: Push and Create PR

### Actions I Would Take

1. **Determine current branch:** We are on `main`. Per the skill, create a feature branch:
   ```bash
   git checkout -b ship/self-improvement-system
   ```

2. **Push to origin:**
   ```bash
   git push -u origin ship/self-improvement-system
   ```

3. **Create PR:**
   ```bash
   gh pr create --title "feat: add self-improvement system" --body "$(cat <<'EOF'
   ## Summary
   - Adds 4 database tables for agent self-improvement (interaction_logs, skill_scores, improvement_actions, coverage_gaps)
   - Implements self-improvement engine service and interaction logger
   - Updates brain_dump tools and agent configurations
   - Includes professional skill library additions and configuration updates

   ## Quality Gates
   - [x] Lint (ruff check + format + codespell)
   - [x] Type check (ty + tsc)
   - [x] Tests (pytest + vitest)
   - [x] Build verification (next build)
   - [x] Migration validation (Supabase MCP)
   - [x] Security advisory check (Supabase) -- PASSED, all tables have RLS
   - [x] Performance advisory check -- 1 warning: missing index on coverage_gaps.user_id
   - [x] Env var diff (Cloud Run + Vercel) -- no missing vars

   ## Deployment Plan
   - Database: 1 Supabase migration (self_improvement) -- already applied in Phase 4
   - Backend: Cloud Run (canary: 10% -> 50% -> 100%)
   - Frontend: Vercel (atomic deploy)

   ## Test plan
   - [ ] Backend health checks pass at each canary stage
   - [ ] Frontend loads correctly
   - [ ] Performance within baseline thresholds
   - [ ] No new security advisories post-deploy

   Generated with Claude Code
   EOF
   )"
   ```

4. **Monitor CI:**
   ```bash
   gh pr checks <pr-number> --watch
   ```
   Simulated: CI passes.

**Result:** Phase 7 PASSED. PR created, CI checks pass.

---

## Phase 8: Merge to Main

### Actions I Would Take

1. **Check PR readiness:**
   ```bash
   gh pr checks <pr-number>
   ```
   Simulated: all checks pass, no conflicts.

2. **Merge the PR:**
   ```bash
   gh pr merge <pr-number> --merge --delete-branch
   ```

3. **Update local main:**
   ```bash
   git checkout main && git pull origin main
   ```

**Result:** Phase 8 PASSED. PR merged, branch deleted, local main updated.

---

## Phase 9: Post-Merge Main Scan

### Actions I Would Take

Re-run the quality gates from Phase 3 on `main` to catch any integration issues from the merge.

1. `uv run ruff check app/ --fix` -- clean
2. `uv run ruff format app/` -- clean
3. `uv run codespell` -- clean
4. `uv run ty check .` -- clean
5. `uv run pytest tests/unit -q` -- all pass
6. `uv run pytest tests/integration -q` -- all pass
7. `cd frontend && npm run build` -- succeeds

Simulated: no new issues introduced by merge.

**Result:** Phase 9 PASSED.

---

## Phase 10: Capture Pre-Deploy Baselines

### Actions I Would Take

```bash
SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")
TOKEN=$(gcloud auth print-identity-token)

for i in 1 2 3; do
  echo "=== Sample $i ==="
  curl -s -o /dev/null -w "  /health/live: %{time_total}s\n" \
    -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
  curl -s -o /dev/null -w "  /health/connections: %{time_total}s\n" \
    -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/connections"
  curl -s -o /dev/null -w "  /health/cache: %{time_total}s\n" \
    -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/cache"
  curl -s -o /dev/null -w "  /health/workflows/readiness: %{time_total}s\n" \
    -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/workflows/readiness"
done
```

**Simulated Baselines (average of 3 samples):**

| Endpoint | Avg Response Time |
|----------|------------------|
| `/health/live` | 38ms |
| `/health/connections` | 142ms |
| `/health/cache` | 67ms |
| `/health/workflows/readiness` | 215ms |

Saved in memory for Phase 12 comparison.

**Result:** Phase 10 PASSED. Baselines captured.

---

## Phase 11: Deploy with Canary Strategy

### Backend -- Cloud Run (Canary)

1. **Deploy new revision WITHOUT migrating traffic:**
   ```bash
   PROJECT_ID=$(gcloud config get-value project)
   gcloud beta run deploy pikar-ai \
     --source . \
     --memory "4Gi" \
     --project $PROJECT_ID \
     --region "us-central1" \
     --no-allow-unauthenticated \
     --no-cpu-throttling \
     --labels "created-by=adk" \
     --no-traffic
   ```
   Simulated: deploy succeeds, new revision `pikar-ai-00042-xyz` created.

2. **Get new revision name:**
   ```bash
   NEW_REV=$(gcloud run revisions list --service pikar-ai --region us-central1 --limit 1 --format="value(REVISION)")
   ```
   Simulated: `NEW_REV=pikar-ai-00042-xyz`

3. **Canary at 10%:**
   ```bash
   gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=pikar-ai-00042-xyz=10
   ```
   Simulated: traffic split applied.

4. **Verify at 10%:** Hit health endpoints, check for errors in logs.
   ```bash
   gcloud run logs read pikar-ai --region us-central1 --limit 20 --log-filter="severity>=ERROR"
   ```
   Simulated: no errors at 10%.

5. **Ramp to 50%:**
   ```bash
   gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=pikar-ai-00042-xyz=50
   ```
   Simulated: traffic split applied. Wait 30 seconds. Check logs again. No errors.

6. **Ramp to 100%:**
   ```bash
   gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=pikar-ai-00042-xyz=100
   ```
   Simulated: full traffic now on new revision.

### Frontend -- Vercel

```bash
cd frontend && vercel --prod
```

Simulated: deployment succeeds. Deployment URL: `https://pikar-ai-abcdef.vercel.app`

**Result:** Phase 11 PASSED. Both platforms deployed.

---

## Phase 12: Verify Deployments and Compare Baselines

### Backend Verification (Cloud Run)

```bash
SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")
TOKEN=$(gcloud auth print-identity-token)

curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/connections"
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/cache"
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/workflows/readiness"
```

Simulated results:
- `/health/live` -- 200 OK
- `/health/connections` -- 200 OK, `{"status": "healthy", "supabase": {...}, "cache": {"status": "healthy"}}`
- `/health/cache` -- 200 OK, Redis healthy, circuit breaker closed
- `/health/workflows/readiness` -- 200 OK, workflow engine ready

### Frontend Verification (Vercel)

```bash
vercel ls --prod
curl -s -o /dev/null -w "%{http_code}" https://pikar-ai-abcdef.vercel.app
```

Simulated: 200 OK.

### Performance Comparison

Collect 3 new samples and compare against Phase 10 baselines:

| Endpoint | Baseline | Post-Deploy | Ratio | Status |
|----------|----------|-------------|-------|--------|
| `/health/live` | 38ms | 42ms | 1.1x | OK |
| `/health/connections` | 142ms | 158ms | 1.1x | OK |
| `/health/cache` | 67ms | 71ms | 1.06x | OK |
| `/health/workflows/readiness` | 215ms | 228ms | 1.06x | OK |

All endpoints within 1.5x of baseline. No performance regression detected.

### Post-Deploy Supabase Advisory Re-Check

Since migrations were applied in Phase 4, re-run advisory checks:

**MCP Tool Call 1:**
```
Tool: mcp__plugin_supabase_supabase__get_advisors
Parameters: { "project_id": "abcdefghijklmnop", "type": "security" }
```

Simulated: same results as Phase 4.6 -- no new security issues.

**MCP Tool Call 2:**
```
Tool: mcp__plugin_supabase_supabase__get_advisors
Parameters: { "project_id": "abcdefghijklmnop", "type": "performance" }
```

Simulated: same performance warning about `coverage_gaps.user_id` index. No new issues from the deployed code interacting with the schema.

**Result:** Phase 12 PASSED. Both deployments confirmed healthy, no performance regression, no new advisories.

---

## Phase 13: Auto-Rollback

**SKIPPED** -- Phase 12 passed. No rollback needed.

---

## Phase 14: Notification

### Console Report

```
SHIP IT COMPLETE
================
Status: SUCCESS

Backend (Cloud Run):  https://pikar-ai-xxxxxxx.run.app -- HEALTHY
Frontend (Vercel):    https://pikar-ai-abcdef.vercel.app -- HEALTHY
Database (Supabase):  1 migration applied (self_improvement)

Performance:
  /health/live:              42ms (baseline: 38ms) -- OK
  /health/connections:       158ms (baseline: 142ms) -- OK
  /health/cache:             71ms (baseline: 67ms) -- OK
  /health/workflows/readiness: 228ms (baseline: 215ms) -- OK

Advisories:
  Security: 0 new issues
  Performance: 1 warning (missing index on coverage_gaps.user_id)

Changes shipped:
- Self-improvement system: 4 new tables (interaction_logs, skill_scores,
  improvement_actions, coverage_gaps) with full RLS policies
- Self-improvement engine service and interaction logger
- Brain dump tool updates
- Agent configuration updates
- Professional skill library additions
- Frontend configuration page updates

PR: https://github.com/org/pikar-ai/pull/XXX
Commit: abc1234
Duration: ~25 minutes
```

### Git Deployment Tag

```bash
TAG="deploy/$(date +%Y%m%d)-$(git rev-parse --short HEAD)"
git tag $TAG
git push origin $TAG
```

Simulated: tag `deploy/20260318-abc1234` created and pushed.

**Result:** Phase 14 COMPLETE.

---

## Summary of MCP Tools Called (Phase 4 Detail)

| # | MCP Tool | Parameters | Purpose |
|---|----------|------------|---------|
| 1 | `mcp__plugin_supabase_supabase__list_projects` | `{}` | Find project ID |
| 2 | `mcp__plugin_supabase_supabase__list_migrations` | `{ project_id }` | Check which migrations are already applied |
| 3 | `mcp__plugin_supabase_supabase__list_tables` | `{ project_id, schemas: ["public", "auth"], verbose: true }` | Verify referenced tables exist |
| 4 | `mcp__plugin_supabase_supabase__execute_sql` | `{ project_id, query: "SELECT table_name FROM information_schema.tables WHERE ..." }` | Check for naming conflicts |
| 5 | `mcp__plugin_supabase_supabase__execute_sql` | `{ project_id, query: "SELECT column_name, data_type FROM information_schema.columns WHERE ..." }` | Verify FK target exists |
| 6 | `mcp__plugin_supabase_supabase__apply_migration` | `{ project_id, name: "self_improvement", query: "<full SQL>" }` | Apply the migration |
| 7 | `mcp__plugin_supabase_supabase__get_advisors` | `{ project_id, type: "security" }` | Post-migration security scan |
| 8 | `mcp__plugin_supabase_supabase__get_advisors` | `{ project_id, type: "performance" }` | Post-migration performance scan |
| 9 | `mcp__plugin_supabase_supabase__list_migrations` | `{ project_id }` | Verify migration was applied |
| 10 | `mcp__plugin_supabase_supabase__get_logs` | `{ project_id, service: "postgres" }` | Check for errors in Postgres logs |
| 11 | `mcp__plugin_supabase_supabase__get_advisors` | `{ project_id, type: "security" }` | Post-deploy re-check (Phase 12) |
| 12 | `mcp__plugin_supabase_supabase__get_advisors` | `{ project_id, type: "performance" }` | Post-deploy re-check (Phase 12) |

## Handling Advisory Findings: Decision Tree

```
Security Advisory Found?
  |
  +-- YES: Missing RLS on new table
  |     |
  |     +-- BLOCKER: Do not proceed to deployment
  |     +-- Create corrective migration SQL (ALTER TABLE ... ENABLE RLS + CREATE POLICY)
  |     +-- Apply via mcp__plugin_supabase_supabase__apply_migration
  |     +-- Save corrective migration file locally
  |     +-- Re-run get_advisors(security) to confirm fix
  |     +-- Only proceed when clean
  |
  +-- YES: Pre-existing advisory (not from this migration)
  |     +-- NOTE: Report to user, do not block
  |
  +-- NO: Proceed

Performance Advisory Found?
  |
  +-- YES: Missing index on FK column
  |     +-- WARNING: Report to user with remediation URL
  |     +-- Suggest follow-up migration with CREATE INDEX CONCURRENTLY
  |     +-- Do NOT block deployment
  |
  +-- YES: Critical (missing PK index, extreme bloat)
  |     +-- BLOCKER: Fix before deployment
  |
  +-- NO: Proceed
```

## Key Observations About the Skill

1. **Migration ordering is correct**: The skill applies migrations in Phase 4 (before code deployment in Phase 11). Since the new app code expects the new tables to exist, this ordering prevents runtime errors.

2. **RLS verification is thorough**: The migration SQL already includes RLS for all 4 tables, which is exactly what the advisory scan would check for. The skill correctly identifies this as a security blocker if missing.

3. **Double advisory check**: The skill runs advisories twice -- once in Phase 4 (after migration) and once in Phase 12 (after deployment). This catches issues that only emerge when the application interacts with the new schema.

4. **The skill correctly flags the user's terminology mismatch**: The user said "braindump_sessions table" but the migration file is named `self_improvement.sql` and creates `interaction_logs`, `skill_scores`, `improvement_actions`, and `coverage_gaps` tables. The `braindump_sessions` table was created by a different migration (`20260317000000_braindump_sessions.sql`). The skill's Phase 1 scan would surface this discrepancy.

5. **Canary strategy adds safety**: Rather than deploying directly, the 10% -> 50% -> 100% traffic ramp gives time to catch issues before full rollout.
