# Ship-It Skill Walkthrough: Large Changeset Evaluation

**Task:** "push everything to prod, but I'm a bit worried because I changed a lot of files across the backend agents and the frontend config page. Make sure nothing breaks."

**Context:** 25+ files changed across backend agents, tools, MCP integrations, frontend config page/API route, and backend config router. No migration files.

**Mode:** SIMULATION / DRY-RUN -- no commands executed, all outputs simulated.

---

## Phase 1: Scan and Assess

### What the skill instructs

Run `git status`, `git diff`, and `git diff --staged` to understand the full scope of changes. Categorize files into domains (backend, frontend, migrations, config, tests). Report a summary. Flag any migration files.

### What I would do

1. Run `git status` to confirm the full list of modified, staged, and untracked files.
2. Run `git diff` and `git diff --staged` to inspect the actual code changes.
3. Categorize by domain using the pipeline-commands reference grep patterns:
   - `git diff --name-only | grep -E '^app/'`
   - `git diff --name-only | grep -E '^frontend/'`
   - `git diff --name-only | grep -E '^supabase/migrations/'`

### Simulated output

Based on the git status snapshot provided:

| Domain | Files | Details |
|--------|-------|---------|
| **Backend** | ~20 | `app/agent.py`, 10 agent files in `app/agents/`, `app/agents/enhanced_tools.py`, 5 tool files in `app/agents/tools/`, `app/mcp/config.py`, `app/mcp/integrations/email_service.py`, `app/mcp/tools/form_handler.py`, `app/mcp/tools/supabase_landing.py`, `app/routers/configuration.py`, `app/social/publisher.py`, `app/workflows/marketing.py`, `app/skills/*`, `app/prompts/executive_instruction.txt` |
| **Frontend** | 2 | `frontend/src/app/dashboard/configuration/page.tsx`, `frontend/src/app/api/configuration/save-api-key/route.ts` |
| **Migrations** | 0 modified (1 untracked) | `supabase/migrations/20260318000000_self_improvement.sql` is untracked -- needs investigation |
| **Config** | 1 | `app/.env.example` |
| **New/Untracked** | 7 | `app/agents/tools/self_improve.py`, `app/services/interaction_logger.py`, `app/services/self_improvement_engine.py`, 4 professional skill files, `supabase/migrations/20260318000000_self_improvement.sql` |

**Summary:** "~30 files changed across 4 domains (backend, frontend, config, skills). No migration files are staged, but one untracked migration file exists."

### Large changeset considerations

The skill's Abort Conditions section states: **"More than 30 files changed (confirm scope)"**. This changeset is at or near that threshold. I would flag this to the user:

> "This changeset touches approximately 30 files across backend agents, tools, MCP integrations, frontend configuration, and new service modules. The skill recommends confirming scope for changesets this large. Would you like to proceed with shipping everything, or would you prefer to split this into smaller deployments (e.g., backend agents first, then frontend config, then new services)?"

Given the user explicitly said "push everything to prod" and expressed concern about breakage (which the quality gates will address), I would proceed after noting the flag.

### Untracked migration file decision

The file `supabase/migrations/20260318000000_self_improvement.sql` is untracked. This is critical -- it means someone created a migration that has not been committed. I would:

1. Ask the user: "There's an untracked migration file `20260318000000_self_improvement.sql`. Should this be included in this deployment? If yes, it triggers the Supabase Migration Gate (Phase 4)."
2. For this walkthrough, I will assume the user says **yes**, which activates Phase 4.

---

## Phase 2: Deployment Timing Guard

### What the skill instructs

1. Check project memory for merge freezes or deployment blackouts.
2. Check the current time -- warn if outside 7 AM - 10 PM local time.
3. Check for active incidents on Cloud Run or Vercel status pages.
4. If the user confirms, proceed.

### What I would do

1. **Check memory:** Review the MEMORY.md file and any project memory files for freeze/blackout mentions. The current memory files cover skills audit, braindump enhancements, and enhanced_tools removal -- none mention a merge freeze or blackout.

2. **Check time:** Run `date +"%H:%M %Z"` and `date +"%u"` (day of week).

### Simulated output

```
Current time: 14:30 EST (Wednesday)
Day of week: 3 (Wednesday)
```

This is within business hours (7 AM - 10 PM) on a weekday. No timing warning needed.

3. **Incident check:** I would attempt to check Cloud Run and Vercel status pages (if the WebFetch tool is available). In simulation:
   - Cloud Run status: No active incidents.
   - Vercel status: No active incidents.

4. **Result:** All clear. Proceed.

### What I would do differently for the large changeset

Because this is a large changeset (25+ files), I would add an **extra** timing consideration: "With this many changes across backend and frontend, deploying mid-day means production users will be active during the canary rollout. This is actually beneficial -- real traffic will exercise the changes during canary. But it also means any bugs will affect real users at 10% traffic. This is the expected tradeoff and within normal deployment parameters."

---

## Phase 3: Quality Gates (Parallel Execution)

### What the skill instructs

Run backend and frontend quality gates in parallel since they are independent.

**Backend gate:** ruff check --fix, ruff format, codespell, ty check, workflow validation, baseline generation, pytest unit, pytest integration.

**Frontend gate:** npm run lint, npx tsc --noEmit, npm test, npm run build.

After both complete, stage any auto-fixed files, manually fix remaining errors, and distinguish pre-existing failures from new ones.

### What I would do

Launch two parallel processes using the background bash strategy from `pipeline-commands.md`:

**Backend quality gate (background process 1):**
```bash
(
  uv run ruff check app/ --fix && \
  uv run ruff format app/ && \
  uv run codespell && \
  uv run ty check . && \
  uv run python scripts/verify/validate_workflow_templates.py && \
  uv run python scripts/verify/generate_workflow_baseline.py && \
  uv run pytest tests/unit -q && \
  uv run pytest tests/integration -q
) > /tmp/backend-quality.log 2>&1 &
```

**Frontend quality gate (background process 2):**
```bash
(
  cd frontend && \
  npm run lint && \
  npx tsc --noEmit && \
  npm test && \
  CI=1 NEXT_TELEMETRY_DISABLE=1 \
  NEXT_PUBLIC_API_URL=http://localhost:8000 \
  NEXT_PUBLIC_SUPABASE_URL=https://example.supabase.co \
  NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_test_key \
  npm run build
) > /tmp/frontend-quality.log 2>&1 &
```

Wait for both PIDs, then read both log files.

### Simulated output

**Backend quality gate:**
```
ruff check app/ --fix: Found 3 fixable issues, auto-fixed.
  - app/agents/tools/self_improve.py:12: F401 unused import 'os'
  - app/services/self_improvement_engine.py:45: I001 import sorting
  - app/services/interaction_logger.py:8: W291 trailing whitespace

ruff format app/: 4 files reformatted.
  - app/agents/tools/self_improve.py
  - app/services/self_improvement_engine.py
  - app/services/interaction_logger.py
  - app/skills/professional_finance_legal.py

codespell: No issues found.

ty check .: 0 errors, 2 warnings.
  Warning: app/agents/tools/self_improve.py:23 - type could be narrowed
  Warning: app/services/self_improvement_engine.py:67 - Optional access without guard

validate_workflow_templates.py: All templates valid.
generate_workflow_baseline.py: Baseline generated.

pytest tests/unit -q: 47 passed, 0 failed.
pytest tests/integration -q: 12 passed, 0 failed.

BACKEND EXIT: 0
```

**Frontend quality gate:**
```
npm run lint: No ESLint errors.
npx tsc --noEmit: No type errors.
npm test: 8 tests passed.
npm run build: Build successful.

FRONTEND EXIT: 0
```

### Post-gate actions

1. **Auto-fixed files to stage later:** `app/agents/tools/self_improve.py`, `app/services/self_improvement_engine.py`, `app/services/interaction_logger.py`, `app/skills/professional_finance_legal.py` (ruff formatting changes).
2. **ty warnings:** These are warnings, not errors. The skill says "zero errors across all quality gates" -- warnings are acceptable. I would note them but not block.
3. **Result:** Quality gates PASSED. Zero errors.

### What I would do differently for the large changeset

With 10 agent files changed, I would pay special attention to:
- Whether `app/agent.py` (the orchestrator) still correctly imports and references all 10 sub-agents
- Whether `app/agents/enhanced_tools.py` changes are compatible with all 10 agent files that might use it
- Whether the `app/agents/tools/tool_registry.py` changes are consistent with `app/agents/tools/agent_skills.py` and other tool files

If tests pass, these concerns are addressed. If any test references are missing for the changed agents, I would flag it: "10 agent files changed but only N agents have test coverage. Consider adding smoke tests before shipping."

---

## Phase 4: Supabase Migration Gate

### What the skill instructs

Skip if no files in `supabase/migrations/` were modified or added. Since we identified an untracked migration file in Phase 1 and assumed the user wants to include it, this phase IS triggered.

### What I would do

1. **Fetch Supabase MCP tool schemas** using ToolSearch.
2. **Identify the project:** Call `mcp__plugin_supabase_supabase__list_projects` to find the pikar-ai project ID.

   Simulated result: `project_id = "abc123-pikar-ai"`

3. **Check current migration state:** Call `mcp__plugin_supabase_supabase__list_migrations` with `{ project_id: "abc123-pikar-ai" }`.

   Simulated result: Lists existing migrations. `20260318000000_self_improvement` is NOT in the list (it is new).

4. **Read the migration SQL:** Read `supabase/migrations/20260318000000_self_improvement.sql` to inspect the content.

   Simulated content: Creates tables for self-improvement tracking (e.g., `self_improvement_logs`, `interaction_metrics`), adds indexes, and possibly adds RLS policies.

5. **Structural checks:**
   - Does it use `IF NOT EXISTS`? Check each CREATE TABLE/INDEX statement.
   - Does it enable RLS on new tables?
   - Does it reference existing tables (foreign keys to `users`, etc.)?

6. **Schema existence checks:** Call `mcp__plugin_supabase_supabase__list_tables` with `{ project_id: "abc123-pikar-ai", schemas: ["public"], verbose: true }` to verify any referenced tables exist.

7. **Dry-run validation:** Call `mcp__plugin_supabase_supabase__execute_sql` with validation queries to confirm no naming conflicts:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public' AND table_name IN ('self_improvement_logs', 'interaction_metrics');
   ```
   Simulated result: No conflicts found.

8. **Apply the migration:** Call `mcp__plugin_supabase_supabase__apply_migration` with:
   ```
   { project_id: "abc123-pikar-ai", name: "self_improvement", query: "<SQL content>" }
   ```
   Simulated result: Migration applied successfully.

9. **Post-migration advisory scan (BOTH types):**
   - `mcp__plugin_supabase_supabase__get_advisors` with `{ project_id: "abc123-pikar-ai", type: "security" }`
   - `mcp__plugin_supabase_supabase__get_advisors` with `{ project_id: "abc123-pikar-ai", type: "performance" }`

   Simulated results:
   - Security: No advisories (assuming the migration includes RLS).
   - Performance: Warning -- "Consider adding index on `self_improvement_logs.created_at` for time-range queries."

   The performance warning is noted but does not block deployment per the skill's rules.

10. **Verify migration integrity:** Call `list_migrations` again to confirm the new migration appears.

11. **Check Postgres logs:** Call `mcp__plugin_supabase_supabase__get_logs` with `{ project_id: "abc123-pikar-ai", service: "postgres" }`. Simulated: No errors.

### Result

Migration gate PASSED. One performance advisory noted (non-blocking).

---

## Phase 5: Environment Variable Diff

### What the skill instructs

Compare `.env.example` against production env vars on both Cloud Run and Vercel. Flag any missing variables, especially `NEXT_PUBLIC_*` vars on Vercel which would cause frontend runtime failures.

### What I would do

**Backend -- Cloud Run:**

1. Run:
   ```bash
   gcloud run services describe pikar-ai \
     --region us-central1 \
     --format="yaml(spec.template.spec.containers[0].env)"
   ```

2. Read `app/.env.example` (which is modified in this changeset -- important to check what was added).

3. Run the diff command from pipeline-commands.md:
   ```bash
   diff <(grep -E '^[A-Z_]+=' app/.env.example | cut -d= -f1 | sort) \
        <(gcloud run services describe pikar-ai --region us-central1 \
          --format="json(spec.template.spec.containers[0].env[].name)" 2>/dev/null | \
          python3 -c "import sys,json; [print(e['name']) for e in json.load(sys.stdin)]" | sort) \
        || true
   ```

### Simulated output

```
Variables in .env.example but NOT in Cloud Run:
  - SELF_IMPROVEMENT_ENABLED (new, added in this changeset)
  - INTERACTION_LOG_RETENTION_DAYS (new, added in this changeset)

Variables in Cloud Run but NOT in .env.example:
  - LEGACY_WEBHOOK_URL (likely legacy -- note but don't block)
```

**Action:** I would warn the user:

> "Two new environment variables were added to `.env.example` in this changeset but are not yet configured in Cloud Run:
> - `SELF_IMPROVEMENT_ENABLED` -- If the code defaults to `False` when missing, this is safe to deploy without it. If not, it could cause a runtime error.
> - `INTERACTION_LOG_RETENTION_DAYS` -- Same concern.
>
> Should I set these in Cloud Run before deploying, or does the code handle missing values gracefully?"

**Frontend -- Vercel:**

1. Run `cd frontend && vercel env ls`
2. Check `frontend/.env.example` for `NEXT_PUBLIC_*` variables.

### Simulated output

```
Vercel env vars: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY (all present)
Expected NEXT_PUBLIC_* vars from .env.example: same list.
No missing NEXT_PUBLIC_* variables.
```

**Result:** Frontend env vars are complete. Backend has 2 potentially missing vars -- flagged to user. Assuming user confirms the code handles defaults, proceed.

### What I would do differently for the large changeset

Because `app/.env.example` is explicitly modified in this changeset, the env var diff is especially critical. I would:
1. Read the actual diff of `.env.example` to see exactly which variables were added/removed/renamed.
2. Cross-reference those additions against the new service files (`self_improvement_engine.py`, `interaction_logger.py`) to confirm they are used.
3. Check whether those new services have sensible defaults (e.g., `os.getenv("SELF_IMPROVEMENT_ENABLED", "false")`). If they do, missing env vars in prod are safe. If they call `os.environ["VAR"]` (which raises `KeyError`), deployment will crash.

---

## Phase 6: Stage and Commit

### What the skill instructs

Run `git status` again (to capture auto-fix changes from Phase 3), stage files specifically (never blind `git add .`), craft a descriptive commit message, create the commit, verify clean working tree.

### What I would do

1. Run `git status` to see the full picture including ruff auto-fixes.

2. Stage files by domain, explicitly naming them:

   ```bash
   # Backend agent changes (modified)
   git add app/agent.py \
     app/agents/compliance/agent.py \
     app/agents/content/agent.py \
     app/agents/customer_support/agent.py \
     app/agents/data/agent.py \
     app/agents/financial/agent.py \
     app/agents/hr/agent.py \
     app/agents/marketing/agent.py \
     app/agents/operations/agent.py \
     app/agents/sales/agent.py \
     app/agents/enhanced_tools.py

   # Backend tool changes
   git add app/agents/tools/agent_skills.py \
     app/agents/tools/configuration.py \
     app/agents/tools/integration_tools.py \
     app/agents/tools/social.py \
     app/agents/tools/tool_registry.py

   # New backend files
   git add app/agents/tools/self_improve.py \
     app/services/interaction_logger.py \
     app/services/self_improvement_engine.py

   # MCP changes
   git add app/mcp/config.py \
     app/mcp/integrations/email_service.py \
     app/mcp/tools/form_handler.py \
     app/mcp/tools/supabase_landing.py

   # Skills
   git add app/skills/__init__.py \
     app/skills/library.py \
     app/skills/loader.py \
     app/skills/professional_finance_legal.py \
     app/skills/professional_marketing_sales.py \
     app/skills/professional_operations_data.py \
     app/skills/professional_pm_productivity_content.py

   # Other backend
   git add app/routers/configuration.py \
     app/social/publisher.py \
     app/workflows/marketing.py \
     app/prompts/executive_instruction.txt

   # Config
   git add app/.env.example

   # Frontend
   git add frontend/src/app/dashboard/configuration/page.tsx \
     frontend/src/app/api/configuration/save-api-key/route.ts

   # Migration
   git add supabase/migrations/20260318000000_self_improvement.sql
   ```

   **Explicitly NOT staged:** `.env` files with secrets, `node_modules/`, `.next/`, `output/`, `tiktok-demo.mp4`, `.playwright-cli/`, `antigravity-awesome-skills` submodule, `skills/` directory (unless confirmed).

3. Craft commit message:

   ```
   feat: add professional skills library, self-improvement engine, and configuration management

   Introduces 62 professional skills across 4 domain modules, a self-improvement
   engine with interaction logging, and updates the configuration page with
   API key management. Updates all 10 specialized agents with enhanced tool
   integration and refreshed skill references.

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
   ```

4. Create the commit using HEREDOC format.
5. Run `git status` to verify working tree is clean (except intentionally untracked files).

### What I would do differently for the large changeset

With 30+ files, I would:
- Double-check that no `.env` files with actual secrets are accidentally staged (the modified `app/.env.example` is fine -- it is a template)
- Verify the untracked `skills/` directory should or should not be included (it is listed as untracked in git status but not mentioned by the user -- ask before including)
- Ensure the commit message accurately reflects the breadth of changes, not just one aspect

---

## Phase 7: Push and Create PR

### What the skill instructs

If on `main`, create a feature branch first. Push with `-u`. Create a PR with quality gate results, migration status, and deployment plan. Monitor CI checks.

### What I would do

1. The git status shows we are on `main`. Create a feature branch:
   ```bash
   git checkout -b ship/professional-skills-self-improvement
   ```

2. Push to remote:
   ```bash
   git push -u origin ship/professional-skills-self-improvement
   ```

3. Create PR:
   ```bash
   gh pr create --title "feat: professional skills, self-improvement engine, config management" --body "$(cat <<'EOF'
   ## Summary
   - Add 62 professional skills across 4 domain modules (finance/legal, marketing/sales, operations/data, PM/productivity/content)
   - Introduce self-improvement engine with interaction logging and DB migration
   - Update configuration page with API key management (frontend + backend)
   - Refresh all 10 specialized agents with enhanced tool integration

   ## Quality Gates
   - [x] Lint (ruff check --fix + format + codespell) -- 3 auto-fixes applied
   - [x] Type check (ty check) -- 0 errors, 2 warnings
   - [x] Frontend lint (ESLint) -- clean
   - [x] Frontend type check (tsc --noEmit) -- clean
   - [x] Unit tests (pytest) -- 47 passed
   - [x] Integration tests (pytest) -- 12 passed
   - [x] Frontend tests -- 8 passed
   - [x] Frontend build -- successful
   - [x] Supabase migration validated and applied
   - [x] Security advisory check -- clean
   - [x] Performance advisory -- 1 non-blocking warning (missing index on created_at)
   - [x] Env var diff -- 2 new backend vars flagged, defaults confirmed safe

   ## Deployment Plan
   - Database: 1 Supabase migration (self_improvement tables) -- already applied
   - Backend: Cloud Run canary (10% -> 50% -> 100%)
   - Frontend: Vercel atomic deploy

   ## Test plan
   - [ ] Backend health checks pass at each canary stage
   - [ ] Frontend configuration page loads correctly
   - [ ] API key save endpoint responds correctly
   - [ ] No new security advisories post-deploy
   - [ ] Performance within baseline thresholds

   Generated with Claude Code
   EOF
   )"
   ```

4. Monitor CI:
   ```bash
   gh pr checks <pr-number> --watch
   ```

### Simulated output

```
PR #42 created: https://github.com/org/pikar-ai/pull/42
CI checks: backend-trust-gate (running), frontend-trust-gate (running)
...
All checks passed.
```

---

## Phase 8: Merge to Main

### What the skill instructs

Check PR is ready (CI passed, no conflicts). Merge with `--merge --delete-branch`. Pull latest main locally.

### What I would do

1. Check merge readiness:
   ```bash
   gh pr checks 42
   ```
   Simulated: All checks passed.

2. Check for merge conflicts:
   Simulated: No conflicts.

3. Merge:
   ```bash
   gh pr merge 42 --merge --delete-branch
   ```

4. Update local:
   ```bash
   git checkout main && git pull origin main
   ```

### Simulated output

```
PR #42 merged successfully.
Branch ship/professional-skills-self-improvement deleted.
Already on 'main'. Pulled latest.
```

---

## Phase 9: Post-Merge Main Scan

### What the skill instructs

Re-run the same quality gates from Phase 3 on main to catch integration issues from the merge.

### What I would do

Re-run the full parallel quality gate pipeline from Phase 3, now on the merged `main` branch.

### Simulated output

```
Backend: ruff check clean, ruff format clean, codespell clean, ty check 0 errors,
  workflow validation passed, pytest unit 47 passed, pytest integration 12 passed.
Frontend: lint clean, tsc clean, tests 8 passed, build successful.
```

All clear. No integration issues introduced by the merge.

### What I would do differently for the large changeset

This phase is especially important for a large changeset because:
- The merge to main could interact with any commits that landed since we branched (even though we branched from main moments ago, CI itself may have tested against a slightly different state)
- With 10 agent files changed, import resolution on the merged tree is worth re-verifying
- I would also run the CI-specific trust gate tests mentioned in `pipeline-commands.md`:
  ```bash
  uv run python scripts/verify/check_migrations.py
  uv run python scripts/verify/validate_journey_workflow_references.py
  ```
  These cross-reference workflow templates against agent capabilities and would catch any broken references from the agent changes.

---

## Phase 10: Capture Pre-Deploy Baselines

### What the skill instructs

Hit each health endpoint 3 times and record average response times. Save baselines for comparison after deployment.

### What I would do

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

### Simulated output

```
=== Sample 1 (cold start, will be discarded) ===
  /health/live: 0.450s
  /health/connections: 0.820s
  /health/cache: 0.380s
  /health/workflows/readiness: 0.950s

=== Sample 2 ===
  /health/live: 0.035s
  /health/connections: 0.145s
  /health/cache: 0.068s
  /health/workflows/readiness: 0.210s

=== Sample 3 ===
  /health/live: 0.028s
  /health/connections: 0.138s
  /health/cache: 0.055s
  /health/workflows/readiness: 0.195s
```

**Baselines (average of samples 2 and 3, discarding cold start sample 1):**

| Endpoint | Baseline |
|----------|----------|
| `/health/live` | 31.5ms |
| `/health/connections` | 141.5ms |
| `/health/cache` | 61.5ms |
| `/health/workflows/readiness` | 202.5ms |

All within expected ranges per the deployment-verification reference.

---

## Phase 11: Deploy with Canary Strategy

### What the skill instructs

Deploy backend to Cloud Run with canary traffic splitting (10% -> 50% -> 100%). Deploy frontend to Vercel atomically. Verify health at each canary stage.

### What I would do

**Step 1: Deploy backend without traffic**

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

Simulated: Build and deploy successful. New revision `pikar-ai-00042-abc` created with 0% traffic.

**Step 2: Get new revision name**

```bash
NEW_REV=$(gcloud run revisions list --service pikar-ai --region us-central1 --limit 1 --format="value(REVISION)")
```

Simulated: `NEW_REV=pikar-ai-00042-abc`

**Step 3: Canary at 10%**

```bash
gcloud run services update-traffic pikar-ai \
  --region us-central1 \
  --to-revisions=pikar-ai-00042-abc=10
```

Simulated: Traffic split updated: 10% to new revision, 90% to previous.

**Verify at 10%:** Hit health endpoints, check error logs:

```bash
TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")

curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/connections"

gcloud run logs read pikar-ai --region us-central1 --limit 20 \
  --log-filter="severity>=ERROR AND timestamp>=\"$(date -u -d '2 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\""
```

Simulated: Health checks return 200. No error-level logs. Safe to proceed.

**Step 4: Ramp to 50%**

```bash
gcloud run services update-traffic pikar-ai \
  --region us-central1 \
  --to-revisions=pikar-ai-00042-abc=50
```

Wait 30 seconds. Re-check health and error logs.

Simulated: Healthy at 50%. No errors.

**Step 5: Ramp to 100%**

```bash
gcloud run services update-traffic pikar-ai \
  --region us-central1 \
  --to-revisions=pikar-ai-00042-abc=100
```

Simulated: 100% traffic now on new revision.

**Frontend -- Vercel:**

```bash
cd frontend && vercel --prod
```

Simulated: Deployment successful. Production URL: `https://pikar-ai.vercel.app`

### What I would do differently for the large changeset

Because 10 agent files changed (the core business logic routing), the canary stage is especially important:

1. **At 10% canary:** I would not just check health endpoints -- I would also check Cloud Run logs specifically for import errors or agent initialization failures:
   ```bash
   gcloud run logs read pikar-ai --region us-central1 --limit 50 \
     --log-filter="severity>=WARNING AND textPayload:agent"
   ```
   Agent initialization errors might not trigger health check failures (the health endpoints don't test agent functionality) but would cause runtime failures when users interact with agents.

2. **At 50% canary:** I would check for a broader set of error patterns including the configuration router and MCP integrations:
   ```bash
   gcloud run logs read pikar-ai --region us-central1 --limit 50 \
     --log-filter="severity>=ERROR AND timestamp>=\"$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\""
   ```

3. **Between each canary stage:** I would wait slightly longer than the minimum (45-60 seconds instead of 30) to give more real traffic time to exercise the new code paths, because the changes touch so many agents.

---

## Phase 12: Verify Deployments and Compare Baselines

### What the skill instructs

Hit all health endpoints, compare response times against Phase 10 baselines, check for performance regressions. Re-run Supabase advisory checks if migrations were applied. Retry loop up to 5 times per platform.

### What I would do

**Backend verification:**

```bash
TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")

curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/connections"
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/cache"
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/workflows/readiness"
```

Simulated: All return 200 with healthy status.

**Frontend verification:**

```bash
vercel ls --prod
curl -s -o /dev/null -w "%{http_code}" https://pikar-ai.vercel.app
```

Simulated: Status 200. Deployment state: READY.

**Performance comparison (3 samples, discard first):**

```
=== Sample 1 (discarded, cold start) ===
  /health/live: 0.520s
  /health/connections: 0.910s
  /health/cache: 0.410s
  /health/workflows/readiness: 1.100s

=== Sample 2 ===
  /health/live: 0.038s
  /health/connections: 0.155s
  /health/cache: 0.072s
  /health/workflows/readiness: 0.225s

=== Sample 3 ===
  /health/live: 0.032s
  /health/connections: 0.148s
  /health/cache: 0.065s
  /health/workflows/readiness: 0.218s
```

**Post-deploy averages (samples 2-3):**

| Endpoint | Baseline | Post-Deploy | Ratio | Status |
|----------|----------|-------------|-------|--------|
| `/health/live` | 31.5ms | 35.0ms | 1.11x | OK |
| `/health/connections` | 141.5ms | 151.5ms | 1.07x | OK |
| `/health/cache` | 61.5ms | 68.5ms | 1.11x | OK |
| `/health/workflows/readiness` | 202.5ms | 221.5ms | 1.09x | OK |

All within the 1.5x threshold. No performance regressions detected.

**Post-deploy Supabase advisory re-check (since migrations were applied in Phase 4):**

Call `mcp__plugin_supabase_supabase__get_advisors` with both `security` and `performance` types.

Simulated:
- Security: Clean (no new advisories).
- Performance: Same warning about `created_at` index (pre-existing from Phase 4, non-blocking).

**Cloud Run error log check:**

```bash
gcloud run logs read pikar-ai --region us-central1 --limit 20 --log-filter="severity>=ERROR"
```

Simulated: No error-level logs in the last 5 minutes.

### Result

Both platforms verified healthy. Performance within baseline. No security advisories. No errors in logs.

---

## Phase 13: Auto-Rollback (if needed)

### What the skill instructs

If Phase 12 retries exhausted and deployment is still unhealthy, auto-rollback.

### What I would do

**This phase is NOT triggered in this simulation** because both deployments are healthy and performance is within thresholds.

However, if rollback were needed, the procedure would be:

**Backend rollback:**
```bash
# Find previous revision
gcloud run revisions list --service pikar-ai --region us-central1 --limit 5

# Route 100% to previous
gcloud run services update-traffic pikar-ai \
  --region us-central1 \
  --to-revisions=pikar-ai-00041-xyz=100

# Verify
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
```

**Frontend rollback:**
```bash
vercel rollback
curl -s -o /dev/null -w "%{http_code}" https://pikar-ai.vercel.app
```

**Post-rollback:** Tag the failed commit with `rollback/<date>-<hash>`, report full diagnosis, do NOT attempt re-deployment.

### What I would do differently for the large changeset

With this many files changed, a rollback scenario would be more complex to diagnose. I would:
1. Check logs for specific agent initialization failures (which of the 10 agents is breaking?)
2. Check if the issue is in the shared modules (`enhanced_tools.py`, `tool_registry.py`) that all agents depend on -- this would cause widespread failures
3. Consider whether a partial rollback is possible (e.g., if only the frontend config page is broken, rollback Vercel only)

---

## Phase 14: Notification

### What the skill instructs

Console report with status, URLs, migration count, performance comparison, changes summary, PR URL, commit hash, duration. Git deployment tag on success.

### What I would do

**Console report:**

```
SHIP IT COMPLETE
================
Status: SUCCESS

Backend (Cloud Run):  https://pikar-ai-xxxxx-uc.a.run.app -- HEALTHY
Frontend (Vercel):    https://pikar-ai.vercel.app -- HEALTHY
Database (Supabase):  1 migration applied (self_improvement)

Performance:
  /health/live:              35.0ms (baseline: 31.5ms) -- OK (1.11x)
  /health/connections:       151.5ms (baseline: 141.5ms) -- OK (1.07x)
  /health/cache:             68.5ms (baseline: 61.5ms) -- OK (1.11x)
  /health/workflows/readiness: 221.5ms (baseline: 202.5ms) -- OK (1.09x)

Advisories:
  Security: clean
  Performance: 1 non-blocking (missing index on self_improvement_logs.created_at)

Changes shipped:
- 62 professional skills across 4 domain modules
- Self-improvement engine with interaction logging
- Configuration page with API key management (frontend + backend)
- All 10 specialized agents updated with enhanced tool integration
- 1 Supabase migration (self_improvement tables)

PR: https://github.com/org/pikar-ai/pull/42
Commit: abc1234
Duration: ~25 minutes
```

**Git deployment tag:**

```bash
TAG="deploy/$(date +%Y%m%d)-$(git rev-parse --short HEAD)"
git tag $TAG
git push origin $TAG
```

Simulated: Tag `deploy/20260318-abc1234` created and pushed.

---

## Summary: What the Skill Did Well for This Large Changeset

1. **Phase 1 (Scan) correctly triggers the >30 file abort condition.** The skill's threshold caught this large changeset and prompted confirmation before proceeding. This directly addresses the user's concern about "a lot of files."

2. **Phase 3 (Quality Gates) runs backend and frontend in parallel.** With 25+ files, sequential quality gates would be slow. The parallel strategy from `pipeline-commands.md` cuts the time roughly in half.

3. **Phase 4 (Migration Gate) handles the untracked migration file.** The skill's Phase 1 scan identified it, and Phase 4 provided a thorough validation workflow before applying it to production.

4. **Phase 5 (Env Var Diff) catches new variables from the `.env.example` change.** Since `.env.example` was modified, the diff against Cloud Run production env vars surfaces missing variables that could cause runtime crashes.

5. **Phase 10-12 (Baselines + Canary + Verification) provide the safety net the user asked for.** The canary strategy (10% -> 50% -> 100%) with health verification at each stage means breakage is caught before it affects all users.

6. **Phase 11 (Canary) is especially valuable for agent changes.** With 10 agent files changed, a canary deployment lets a small fraction of traffic exercise the new agent code while monitoring for errors. If any agent initialization fails, it is caught at 10% traffic rather than 100%.

7. **Phase 13 (Auto-Rollback) is the ultimate safety net.** If all verification fails, production is automatically restored to the previous known-good state. This directly addresses the user's concern about "nothing breaks."

## What I Would Do Differently Because of the Large Changeset

1. **Phase 1:** Explicitly ask whether to split the deployment into smaller batches (agents only, then frontend, then new services). The skill flags the file count but does not prescribe splitting strategy.

2. **Phase 3:** Add targeted checks beyond the standard quality gates -- verify that `app/agent.py` correctly references all 10 modified sub-agents, and that `enhanced_tools.py` changes are compatible with each agent's expectations.

3. **Phase 5:** Read the actual diff of `.env.example` (not just compare names) to understand what variables were added and verify the code handles missing defaults gracefully.

4. **Phase 9 (Post-Merge Scan):** Run the additional trust-gate scripts (`check_migrations.py`, `validate_journey_workflow_references.py`) that cross-reference workflow templates against agent capabilities -- important when agent files change.

5. **Phase 11 (Canary):** Wait longer between canary stages (45-60s instead of 30s) and check agent-specific log patterns beyond just health endpoints. Health endpoints prove the container is running but do not prove agent functionality works correctly.

6. **Phase 12 (Verification):** Add a functional smoke test beyond health checks -- attempt a simple agent interaction through the `/a2a/app/run_sse` endpoint to verify the agent orchestration layer works end-to-end with the new code.

## Skill Coverage Assessment

| Concern from User | How Skill Addresses It | Adequate? |
|---|---|---|
| "changed a lot of files" | Phase 1: >30 file abort condition | Yes -- flags and confirms |
| "across the backend agents" | Phase 3: full backend quality gate + Phase 11: canary | Yes -- caught by tests, type checks, and gradual rollout |
| "frontend config page" | Phase 3: frontend quality gate (lint, tsc, build) | Yes -- build verification catches compile-time issues |
| "make sure nothing breaks" | Phase 10-12: baselines + canary + verification | Yes -- layered safety from canary traffic to auto-rollback |
| Unmentioned: migration file | Phase 1: flagged untracked file, Phase 4: full migration gate | Yes -- surfaced and handled |
| Unmentioned: new env vars | Phase 5: env var diff | Yes -- surfaced missing prod vars |
