# Ship It Skill -- Full Walkthrough (Dry Run)

**Task:** "ship it"
**Context:** pikar-ai repo at `C:\Users\expert\documents\pka\pikar-ai`, with uncommitted changes to several Python files in `app/agents/` and some frontend TypeScript files. No migration files changed.
**Mode:** Simulation / Dry Run -- no commands are actually executed.

---

## Pre-Phase: Read Reference Files

The skill instructs: "Read `references/pipeline-commands.md` for the exact commands for each phase. Read `references/deployment-verification.md` for health checks, rollback, canary, env diffing, and performance baselines. Read `references/supabase-migrations.md` when migration files are in the changeset."

**What I would do:**
- Use the `Read` tool to read `skills/ship-it/references/pipeline-commands.md`
- Use the `Read` tool to read `skills/ship-it/references/deployment-verification.md`
- Since the context says no migration files are changed, I would note this but still read `references/supabase-migrations.md` to understand the full pipeline. In practice, I could skip it since Phase 4 will be skipped.

**Decision:** All three reference files have been read. I am now equipped with exact commands, verification procedures, and migration workflows.

---

## Phase 1: Scan and Assess

**Goal:** Understand what has changed before touching anything.

**What I would do:**

1. **Run `git status`** using the Bash tool:
   ```bash
   git status
   ```
   **Simulated output:** Shows modified files including:
   - `app/.env.example` (M)
   - `app/agent.py` (M)
   - `app/agents/compliance/agent.py` (M)
   - `app/agents/content/agent.py` (M)
   - `app/agents/customer_support/agent.py` (M)
   - `app/agents/data/agent.py` (M)
   - `app/agents/enhanced_tools.py` (M)
   - `app/agents/financial/agent.py` (M)
   - `app/agents/hr/agent.py` (M)
   - `app/agents/marketing/agent.py` (M)
   - `app/agents/operations/agent.py` (M)
   - `app/agents/sales/agent.py` (M)
   - `app/agents/tools/agent_skills.py` (M)
   - `app/agents/tools/configuration.py` (M)
   - `app/agents/tools/integration_tools.py` (M)
   - `app/agents/tools/social.py` (M)
   - `app/agents/tools/tool_registry.py` (M)
   - `app/mcp/config.py` (M)
   - `app/mcp/integrations/email_service.py` (M)
   - `app/mcp/tools/form_handler.py` (M)
   - `app/mcp/tools/supabase_landing.py` (M)
   - `app/prompts/executive_instruction.txt` (M)
   - `app/routers/configuration.py` (M)
   - `app/skills/__init__.py` (M)
   - `app/skills/library.py` (M)
   - `app/skills/loader.py` (M)
   - `app/social/publisher.py` (M)
   - `app/workflows/marketing.py` (M)
   - `frontend/src/app/api/configuration/save-api-key/route.ts` (M)
   - `frontend/src/app/dashboard/configuration/page.tsx` (M)
   - Untracked: `app/agents/tools/self_improve.py`, `app/services/interaction_logger.py`, `app/services/self_improvement_engine.py`, `app/skills/professional_*.py`, `supabase/migrations/20260318000000_self_improvement.sql` (but context says no migrations changed, so I note this discrepancy)
   - Other untracked: `.next/`, `.playwright-cli/`, `output/`, `skills/`, `tiktok-demo.mp4`

2. **Run `git diff`** to see actual changes:
   ```bash
   git diff
   git diff --staged
   ```

3. **Categorize changes into domains:**
   - **Backend:** ~28 files in `app/**/*.py` -- agent files, tools, skills, MCP, workflows, routers, services
   - **Frontend:** 2 files in `frontend/src/**/*.{ts,tsx}` -- `save-api-key/route.ts`, `configuration/page.tsx`
   - **Migrations:** `supabase/migrations/20260318000000_self_improvement.sql` is listed as untracked. The task context says "no migration files changed" but git status shows this file exists. **Decision:** I would flag this to the user -- there IS an untracked migration file. This would trigger Phase 4.
   - **Config:** `app/.env.example` is modified (config domain)
   - **Tests:** No test file changes detected

4. **Report to user:**
   > "~30 files changed across 4 domains: backend (28 Python files), frontend (2 TypeScript files), config (1 .env.example), and 1 untracked Supabase migration file. There are also 4 new untracked Python files (self_improve.py, interaction_logger.py, self_improvement_engine.py, professional skill files)."

5. **Migration flag:** The untracked migration file `supabase/migrations/20260318000000_self_improvement.sql` IS present. This WILL trigger Phase 4.

**Abort condition check:** More than 30 files changed. The skill says: "More than 30 files changed (confirm scope)." **Decision:** I would warn the user:
> "There are approximately 34 files to be committed (30 modified + 4 new untracked). This exceeds the 30-file threshold. Shall I proceed?"

Assuming user confirms, continue.

---

## Phase 2: Deployment Timing Guard

**Goal:** Check whether it is safe to deploy right now.

**What I would do:**

1. **Check project memory for merge freezes or deployment blackouts:**
   - Read the MEMORY.md file. No mention of any active merge freezes or deployment blackouts found.
   - **Result:** No freeze/blackout active.

2. **Check current time:**
   ```bash
   date +"%H:%M %Z"
   date +"%u"
   ```
   **Simulated output:** Let's say it is `14:30 EDT` on a Wednesday (day 3).
   - Within business hours (7 AM - 10 PM): YES
   - Weekday: YES
   - **Result:** Safe to deploy from a timing perspective.

3. **Check for active incidents on Cloud Run / Vercel status pages:**
   - I would use the `WebFetch` tool (deferred) to check `https://status.cloud.google.com/` and `https://www.vercel-status.com/` if available.
   - **Simulated result:** No active incidents.

4. **Decision:** All clear. Proceed to Phase 3.

---

## Phase 3: Quality Gates (Parallel Execution)

**Goal:** Run all lint, type-check, and test commands. Auto-fix what can be auto-fixed.

**What I would do:**

Since both backend and frontend files changed, I would run BOTH quality gates in parallel.

### Backend Quality Gate

I would run these commands in a single background Bash call:

```bash
uv run ruff check app/ --fix && \
uv run ruff format app/ && \
uv run codespell && \
uv run ty check . && \
uv run python scripts/verify/validate_workflow_templates.py && \
uv run python scripts/verify/generate_workflow_baseline.py && \
uv run pytest tests/unit -q && \
uv run pytest tests/integration -q
```

**Simulated output:**
- `ruff check app/ --fix`: Found 3 issues, auto-fixed 3. (e.g., unused imports, import sorting)
- `ruff format app/`: Reformatted 5 files.
- `codespell`: No spelling errors found.
- `ty check .`: No type errors found (or some warnings noted).
- `validate_workflow_templates.py`: All templates valid.
- `generate_workflow_baseline.py`: Baseline generated.
- `pytest tests/unit -q`: 47 passed, 0 failed.
- `pytest tests/integration -q`: 12 passed, 0 failed.
- **Overall backend exit code: 0 (success)**

### Frontend Quality Gate

I would run these commands in a parallel background Bash call:

```bash
cd frontend && \
npm run lint && \
npx tsc --noEmit && \
npm test && \
CI=1 NEXT_TELEMETRY_DISABLE=1 \
NEXT_PUBLIC_API_URL=http://localhost:8000 \
NEXT_PUBLIC_SUPABASE_URL=https://example.supabase.co \
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_test_key \
npm run build
```

**Simulated output:**
- `npm run lint`: No ESLint errors.
- `npx tsc --noEmit`: No TypeScript errors.
- `npm test`: All tests pass.
- `npm run build`: Build succeeds.
- **Overall frontend exit code: 0 (success)**

### Post Quality Gate Assessment

- Ruff auto-fixed 3 files and reformatted 5 files -- these need to be staged along with the original changes.
- No remaining errors.
- All tests pass.

**Result:** Quality gates PASSED. Proceed.

---

## Phase 4: Supabase Migration Gate

**Goal:** Validate and apply database migrations safely.

The skill says: "Skip this phase if no files in `supabase/migrations/` were modified or added." However, there IS an untracked migration file: `supabase/migrations/20260318000000_self_improvement.sql`. This is a new (untracked) file, so this phase should NOT be skipped.

**What I would do:**

1. **Identify the project:**
   - Fetch the `mcp__plugin_supabase_supabase__list_projects` tool definition via `ToolSearch`.
   - Call `mcp__plugin_supabase_supabase__list_projects` to find the pikar-ai project.
   - **Simulated result:** Project ID = `abcdef123456`, name = `pikar-ai`.

2. **Check current migration state:**
   - Call `mcp__plugin_supabase_supabase__list_migrations` with `project_id: "abcdef123456"`.
   - **Simulated result:** Lists all currently applied migrations, e.g., migrations up through `20260317...`. The `20260318000000_self_improvement` migration is NOT in the list -- it is new.
   - Compare against local `supabase/migrations/` directory. Confirm `20260318000000_self_improvement.sql` is the only new migration.

3. **Validate migration SQL:**
   - Use `Read` tool to read `supabase/migrations/20260318000000_self_improvement.sql`.
   - Check for:
     - `IF NOT EXISTS` guards on CREATE statements
     - Transaction wrapping (`BEGIN`/`COMMIT`)
     - Destructive `DROP` operations with guards
     - RLS policies for new tables
     - Foreign key references to existing tables
   - **Simulated result:** The migration creates a `self_improvement` related table. It uses `IF NOT EXISTS`. It includes RLS policies. No destructive operations.

4. **Dry-run validation:**
   - Call `mcp__plugin_supabase_supabase__list_tables` with `project_id, schemas: ["public"], verbose: true` to verify referenced tables exist.
   - Call `mcp__plugin_supabase_supabase__execute_sql` with validation queries to check for naming conflicts and foreign key targets.
   - **Simulated result:** All referenced tables exist. No naming conflicts.

5. **Apply migration:**
   - Call `mcp__plugin_supabase_supabase__apply_migration` with:
     - `project_id: "abcdef123456"`
     - `name: "self_improvement"`
     - `query: "<full SQL content of the migration file>"`
   - **Simulated result:** Migration applied successfully.

6. **Post-migration advisory scan:**
   - Call `mcp__plugin_supabase_supabase__get_advisors` with `project_id, type: "security"`.
   - Call `mcp__plugin_supabase_supabase__get_advisors` with `project_id, type: "performance"`.
   - **Simulated results:**
     - Security: No advisories (RLS was included in the migration).
     - Performance: 1 advisory -- suggest adding an index on a frequently queried column. Non-blocking.
   - Report the performance advisory to the user as a warning.

7. **Verify migration integrity:**
   - Call `mcp__plugin_supabase_supabase__list_migrations` again to confirm the new migration appears.
   - **Simulated result:** `20260318000000_self_improvement` is now listed.

8. **Check Postgres logs:**
   - Call `mcp__plugin_supabase_supabase__get_logs` with `project_id, service: "postgres"`.
   - **Simulated result:** No errors or warnings related to the migration.

**Result:** Migration gate PASSED. 1 performance advisory noted (non-blocking).

---

## Phase 5: Environment Variable Diff

**Goal:** Verify production env vars match what the code expects.

**What I would do:**

### Backend -- Cloud Run

1. **Get current production env vars:**
   ```bash
   gcloud run services describe pikar-ai --region us-central1 --format="yaml(spec.template.spec.containers[0].env)"
   ```
   **Simulated output:** Lists env vars like `GOOGLE_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `REDIS_HOST`, `REDIS_PORT`, `WORKFLOW_SERVICE_SECRET`, etc.

2. **Read `.env.example`:**
   - Already read. Contains variables like `ENVIRONMENT`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `REDIS_HOST`, `REDIS_PORT`, `GOOGLE_API_KEY`, etc.

3. **Compare:**
   ```bash
   diff <(grep -E '^[A-Z_]+=' .env.example | cut -d= -f1 | sort) \
        <(gcloud run services describe pikar-ai --region us-central1 \
          --format="json(spec.template.spec.containers[0].env[].name)" 2>/dev/null | \
          python3 -c "import sys,json; [print(e['name']) for e in json.load(sys.stdin)]" | sort) \
        || true
   ```
   **Simulated result:** All critical variables present. The `.env.example` was modified in this changeset, so I would check if any NEW variables were added that might be missing in Cloud Run. If the `.env.example` change added new vars (e.g., for self-improvement features), I would flag them.

   **Decision:** If new vars are needed for the self_improvement feature, warn the user: "New env vars may be required for the self-improvement engine. Please verify they are configured in Cloud Run."

### Frontend -- Vercel

1. **List Vercel env vars:**
   ```bash
   cd frontend && vercel env ls
   ```
   **Simulated output:** Lists `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, etc.

2. **Check expected vars:**
   ```bash
   grep -E '^NEXT_PUBLIC_' frontend/.env.example 2>/dev/null | cut -d= -f1 | sort
   ```
   **Simulated result:** All `NEXT_PUBLIC_*` vars are present in Vercel.

3. **Flag issues:** None found (simulated).

**Result:** Env var diff PASSED. Any new variables flagged to user.

---

## Phase 6: Stage and Commit

**Goal:** Stage all relevant files and create a well-crafted commit.

**What I would do:**

1. **Run `git status` again** to see the full picture (including auto-fix changes from Phase 3):
   ```bash
   git status
   ```
   **Simulated output:** Same modified files as before, plus any files reformatted by ruff in Phase 3.

2. **Stage files specifically** (never `git add .`):
   ```bash
   # Stage modified Python files
   git add app/agent.py app/agents/compliance/agent.py app/agents/content/agent.py \
     app/agents/customer_support/agent.py app/agents/data/agent.py \
     app/agents/enhanced_tools.py app/agents/financial/agent.py \
     app/agents/hr/agent.py app/agents/marketing/agent.py \
     app/agents/operations/agent.py app/agents/sales/agent.py \
     app/agents/tools/agent_skills.py app/agents/tools/configuration.py \
     app/agents/tools/integration_tools.py app/agents/tools/social.py \
     app/agents/tools/tool_registry.py app/mcp/config.py \
     app/mcp/integrations/email_service.py app/mcp/tools/form_handler.py \
     app/mcp/tools/supabase_landing.py app/prompts/executive_instruction.txt \
     app/routers/configuration.py app/skills/__init__.py app/skills/library.py \
     app/skills/loader.py app/social/publisher.py app/workflows/marketing.py

   # Stage new Python files
   git add app/agents/tools/self_improve.py app/services/interaction_logger.py \
     app/services/self_improvement_engine.py app/skills/professional_finance_legal.py \
     app/skills/professional_marketing_sales.py app/skills/professional_operations_data.py \
     app/skills/professional_pm_productivity_content.py

   # Stage frontend files
   git add frontend/src/app/api/configuration/save-api-key/route.ts \
     frontend/src/app/dashboard/configuration/page.tsx

   # Stage config
   git add app/.env.example

   # Stage migration
   git add supabase/migrations/20260318000000_self_improvement.sql
   ```

   **Explicitly NOT staging:**
   - `.next/` (build artifact)
   - `.playwright-cli/` (tooling)
   - `output/` (generated output)
   - `skills/` (skill definitions, not application code)
   - `tiktok-demo.mp4` (large binary)
   - `antigravity-awesome-skills` (submodule change -- requires separate handling)
   - Any `.env` files with real secrets

   **Abort condition check:** The `.env.example` file is being staged, not an actual `.env` file. Safe to proceed.

3. **Analyze changes and craft commit message:**
   - The changes span: professional skills addition, self-improvement engine, agent instruction updates, configuration page updates, tool registry enhancements.
   - Based on recent commit style (e.g., `feat: add client-side timer UI...`), the project uses conventional commits.

4. **Create the commit:**
   ```bash
   git commit -m "$(cat <<'EOF'
   feat: add professional skills library, self-improvement engine, and configuration enhancements

   Adds 62 professional skills across 4 domain modules, introduces a self-improvement
   engine with interaction logging, updates all agent instructions, and enhances the
   frontend configuration page with API key management.

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
   EOF
   )"
   ```

5. **Verify with `git status`:**
   ```bash
   git status
   ```
   **Simulated output:** Only intentionally untracked files remain (`.next/`, `.playwright-cli/`, `output/`, `skills/`, `tiktok-demo.mp4`).

**Result:** Commit created successfully.

---

## Phase 7: Push and Create PR

**Goal:** Get the code onto a feature branch and create a PR.

**What I would do:**

1. **Determine current branch:**
   - We are on `main` (from git status context).
   - Per the skill: "If on `main`, create a feature branch first."

2. **Create feature branch:**
   ```bash
   git checkout -b ship/professional-skills-and-self-improvement
   ```

3. **Push to origin:**
   ```bash
   git push -u origin ship/professional-skills-and-self-improvement
   ```

4. **Create PR:**
   ```bash
   gh pr create --title "feat: add professional skills, self-improvement engine" --body "$(cat <<'EOF'
   ## Summary
   - Adds 62 professional skills across 4 domain modules (finance/legal, marketing/sales, operations/data, PM/productivity/content)
   - Introduces self-improvement engine with interaction logging and feedback loop
   - Updates all 10 specialized agent instructions to reference new skills
   - Enhances frontend configuration page with API key management
   - Adds Supabase migration for self_improvement tables

   ## Quality Gates
   - [x] Lint (ruff check + format + codespell) -- all passed, 3 auto-fixes applied
   - [x] Type check (ty + tsc) -- no errors
   - [x] Tests (pytest unit + integration, frontend tests) -- all passed
   - [x] Build verification (next build) -- success
   - [x] Migration validation (Supabase MCP) -- applied successfully
   - [x] Security advisory check (Supabase) -- no security issues
   - [x] Performance advisory -- 1 non-blocking index suggestion noted
   - [x] Env var diff (Cloud Run + Vercel) -- all required vars present

   ## Deployment Plan
   - Database: 1 Supabase migration (20260318000000_self_improvement) -- already applied
   - Backend: Cloud Run (canary: 10% -> 50% -> 100%)
   - Frontend: Vercel (atomic deploy)

   ## Test plan
   - [ ] Backend health checks pass at each canary stage
   - [ ] Frontend loads correctly
   - [ ] Performance within baseline thresholds
   - [ ] No new security advisories
   - [ ] Self-improvement engine endpoints respond correctly
   - [ ] Professional skills are accessible via agent interactions

   Generated with Claude Code
   EOF
   )"
   ```

5. **Monitor CI:**
   ```bash
   gh pr checks <pr-number> --watch
   ```
   **Simulated result:** CI checks pass (GitHub Actions runs the trust gate suite).

**Result:** PR created, CI passes.

---

## Phase 8: Merge to Main

**Goal:** Merge the PR into main.

**What I would do:**

1. **Check PR is ready:**
   ```bash
   gh pr checks <pr-number>
   ```
   **Simulated result:** All checks passed, no conflicts.

2. **Merge the PR:**
   ```bash
   gh pr merge <pr-number> --merge --delete-branch
   ```
   **Simulated result:** PR merged successfully, branch `ship/professional-skills-and-self-improvement` deleted.

3. **Update local main:**
   ```bash
   git checkout main && git pull origin main
   ```
   **Simulated result:** Local main is now up to date with the merged commit.

**Result:** PR merged, local main updated.

---

## Phase 9: Post-Merge Main Scan

**Goal:** Verify main is healthy after merge before deploying.

**What I would do:**

1. **Re-run the same quality gates from Phase 3 on main:**

   **Backend:**
   ```bash
   uv run ruff check app/ --fix && \
   uv run ruff format app/ && \
   uv run codespell && \
   uv run ty check . && \
   uv run python scripts/verify/validate_workflow_templates.py && \
   uv run python scripts/verify/generate_workflow_baseline.py && \
   uv run pytest tests/unit -q && \
   uv run pytest tests/integration -q
   ```

   **Frontend:**
   ```bash
   cd frontend && npm run lint && npx tsc --noEmit && npm test && \
   CI=1 NEXT_TELEMETRY_DISABLE=1 \
   NEXT_PUBLIC_API_URL=http://localhost:8000 \
   NEXT_PUBLIC_SUPABASE_URL=https://example.supabase.co \
   NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_test_key \
   npm run build
   ```

   **Simulated result:** All gates pass on main. No integration issues from the merge.

2. **No new issues found.** Build passes.

**Result:** Post-merge scan PASSED.

---

## Phase 10: Capture Pre-Deploy Baselines

**Goal:** Record current production performance metrics before deploying new code.

**What I would do:**

1. **Get service URL and auth token:**
   ```bash
   SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")
   TOKEN=$(gcloud auth print-identity-token)
   ```

2. **Collect 3 samples per endpoint:**
   ```bash
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

   **Simulated baselines (averaged from samples 2 and 3, discarding sample 1 for cold start):**
   | Endpoint | Avg Response Time |
   |----------|------------------|
   | `/health/live` | 35ms |
   | `/health/connections` | 150ms |
   | `/health/cache` | 80ms |
   | `/health/workflows/readiness` | 220ms |

3. **Save baselines in memory** for comparison in Phase 12.

**Result:** Baselines captured. All within expected ranges.

---

## Phase 11: Deploy with Canary Strategy

**Goal:** Deploy to both Cloud Run (canary) and Vercel (atomic).

### Backend -- Cloud Run (Canary)

1. **Deploy new revision WITHOUT traffic:**
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
   **Simulated result:** New revision `pikar-ai-00042-abc` deployed. No traffic routed to it.

2. **Get the new revision name:**
   ```bash
   NEW_REV=$(gcloud run revisions list --service pikar-ai --region us-central1 --limit 1 --format="value(REVISION)")
   ```
   **Simulated result:** `NEW_REV=pikar-ai-00042-abc`

3. **Canary at 10%:**
   ```bash
   gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=pikar-ai-00042-abc=10
   ```
   **Simulated result:** Traffic split: 10% to new, 90% to previous.

4. **Verify at 10%:**
   - Hit health endpoints multiple times.
   - Check error logs:
     ```bash
     gcloud run logs read pikar-ai --region us-central1 --limit 20 --log-filter="severity>=ERROR"
     ```
   - **Simulated result:** No errors. Health checks return 200.

5. **Ramp to 50%:**
   ```bash
   gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=pikar-ai-00042-abc=50
   ```
   - Wait 30 seconds. Check logs again.
   - **Simulated result:** No errors at 50%.

6. **Ramp to 100%:**
   ```bash
   gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=pikar-ai-00042-abc=100
   ```
   - **Simulated result:** 100% traffic on new revision.

### Frontend -- Vercel

1. **Deploy to production:**
   ```bash
   cd frontend && vercel --prod
   ```
   **Simulated result:** Deployment successful. URL: `https://pikar-ai.vercel.app` (or similar). Deployment ID captured.

**Result:** Both deployments completed successfully.

---

## Phase 12: Verify Deployments and Compare Baselines

**Goal:** Confirm both deployments are healthy AND performance has not regressed.

### Backend Verification (Cloud Run)

1. **Hit health endpoints:**
   ```bash
   SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")
   TOKEN=$(gcloud auth print-identity-token)

   curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
   curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/connections"
   curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/cache"
   curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/workflows/readiness"
   ```
   **Simulated results:**
   - `/health/live`: 200 OK
   - `/health/connections`: 200 OK, `{"status": "healthy", "supabase": {...}, "cache": {"status": "healthy"}}`
   - `/health/cache`: 200 OK, circuit_breaker_state: "closed" (healthy)
   - `/health/workflows/readiness`: 200 OK, workflow engine ready

2. **Check error logs:**
   ```bash
   gcloud run logs read pikar-ai --region us-central1 --limit 20 --log-filter="severity>=ERROR"
   ```
   **Simulated result:** No errors.

### Frontend Verification (Vercel)

1. **Check deployment status:**
   ```bash
   vercel ls --prod
   ```
   **Simulated result:** Latest deployment shows `State: READY`.

2. **Hit the deployment URL:**
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://pikar-ai.vercel.app
   ```
   **Simulated result:** `200`

### Performance Comparison

Collect 3 new samples (discard first for cold start):

**Simulated post-deploy performance (averaged from samples 2 and 3):**
| Endpoint | Pre-Deploy | Post-Deploy | Ratio | Status |
|----------|-----------|-------------|-------|--------|
| `/health/live` | 35ms | 38ms | 1.09x | OK |
| `/health/connections` | 150ms | 160ms | 1.07x | OK |
| `/health/cache` | 80ms | 85ms | 1.06x | OK |
| `/health/workflows/readiness` | 220ms | 230ms | 1.05x | OK |

All within 1.5x of baseline. No regressions.

### Post-Deploy Supabase Advisory Re-Check

Since migrations were applied in Phase 4:
- Call `mcp__plugin_supabase_supabase__get_advisors` with `type: "security"`.
- Call `mcp__plugin_supabase_supabase__get_advisors` with `type: "performance"`.
- **Simulated result:** Same as Phase 4 -- no new security advisories, same performance advisory about indexing.

**Result:** Both deployments VERIFIED HEALTHY. No performance regressions. No new security advisories.

---

## Phase 13: Auto-Rollback

**This phase is SKIPPED** because Phase 12 succeeded. Both deployments are healthy.

If Phase 12 had failed after 5 retries, I would have:

1. **Cloud Run rollback:**
   ```bash
   gcloud run revisions list --service pikar-ai --region us-central1 --limit 5
   gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=<previous-revision>=100
   ```
   Then verify the rollback is healthy.

2. **Vercel rollback:**
   ```bash
   vercel rollback
   ```
   Then verify with a curl to the production URL.

3. Report diagnosis to user and stop -- no automatic re-deployment after rollback.

---

## Phase 14: Notification

**Goal:** Report final status and tag the deployment.

### Console Report

```
SHIP IT COMPLETE
================
Status: SUCCESS

Backend (Cloud Run):  https://pikar-ai-xxxxx-uc.a.run.app -- HEALTHY
Frontend (Vercel):    https://pikar-ai.vercel.app -- HEALTHY
Database (Supabase):  1 migration applied (20260318000000_self_improvement)

Performance:
  /health/live:              38ms (baseline: 35ms) -- OK
  /health/connections:       160ms (baseline: 150ms) -- OK
  /health/cache:             85ms (baseline: 80ms) -- OK
  /health/workflows/readiness: 230ms (baseline: 220ms) -- OK

Advisory Notes:
  - 1 performance advisory: consider adding index on self_improvement query column (non-blocking)

Changes shipped:
- 62 professional skills across 4 domain modules
- Self-improvement engine with interaction logging
- Updated agent instructions for all 10 specialized agents
- Frontend configuration page with API key management
- Supabase migration for self_improvement tables

PR: https://github.com/<org>/pikar-ai/pull/<number>
Commit: <full-commit-hash>
Duration: ~25 minutes (estimated)
```

### Git Deployment Tag

```bash
TAG="deploy/$(date +%Y%m%d)-$(git rev-parse --short HEAD)"
git tag $TAG
git push origin $TAG
```

**Simulated result:** Tag `deploy/20260318-a1b2c3d` created and pushed.

**Result:** Pipeline complete. Production is live and verified.

---

## Summary of All Phases

| Phase | Name | Status | Notes |
|-------|------|--------|-------|
| 1 | Scan and Assess | DONE | ~34 files across 4 domains, migration flagged |
| 2 | Deployment Timing Guard | DONE | Within business hours, no freezes |
| 3 | Quality Gates | PASSED | 3 auto-fixes applied, all tests pass |
| 4 | Supabase Migration Gate | PASSED | 1 migration applied, no security advisories |
| 5 | Environment Variable Diff | PASSED | All required vars present |
| 6 | Stage and Commit | DONE | Specific files staged, conventional commit |
| 7 | Push and Create PR | DONE | Feature branch, PR created, CI passed |
| 8 | Merge to Main | DONE | PR merged, branch deleted |
| 9 | Post-Merge Main Scan | PASSED | All quality gates pass on main |
| 10 | Capture Pre-Deploy Baselines | DONE | 4 endpoints baselined |
| 11 | Deploy with Canary | DONE | Cloud Run canary 10%->50%->100%, Vercel atomic |
| 12 | Verify Deployments | PASSED | All healthy, no regressions |
| 13 | Auto-Rollback | SKIPPED | Not needed -- deployments healthy |
| 14 | Notification | DONE | Report printed, deployment tag pushed |

## Key Decisions Made During Walkthrough

1. **Abort condition triggered (30+ files):** Would ask user to confirm scope before proceeding.
2. **Migration file detected:** Despite task context saying "no migrations changed," git status shows an untracked migration file. Chose to include it and run Phase 4.
3. **Staging strategy:** Listed every file explicitly rather than using `git add .`. Excluded build artifacts, large binaries, skill definitions, and environment files.
4. **Commit message style:** Followed the project's conventional commit format observed in recent git log.
5. **Branch naming:** Used `ship/<description>` format as specified by the skill.
6. **Canary strategy:** Used the full 10% -> 50% -> 100% ramp with verification at each stage.
7. **Performance comparison:** Used the 1.5x / 3x / 5x thresholds from the deployment-verification reference.
8. **Post-deploy advisory re-check:** Performed because migrations were applied in Phase 4.

## Tools Used (Would Have Used)

| Tool | Purpose |
|------|---------|
| `Bash` | git commands, quality gate commands, gcloud/vercel CLI, curl health checks |
| `Read` | Reference files, migration SQL, .env.example |
| `ToolSearch` | Fetch deferred MCP tool schemas for Supabase |
| `mcp__plugin_supabase_supabase__list_projects` | Find project ID |
| `mcp__plugin_supabase_supabase__list_migrations` | Check migration state |
| `mcp__plugin_supabase_supabase__list_tables` | Validate schema targets |
| `mcp__plugin_supabase_supabase__execute_sql` | Dry-run validation queries |
| `mcp__plugin_supabase_supabase__apply_migration` | Apply the migration |
| `mcp__plugin_supabase_supabase__get_advisors` | Security + performance advisory scans |
| `mcp__plugin_supabase_supabase__get_logs` | Check Postgres logs |
| `WebFetch` (deferred) | Check Cloud Run / Vercel status pages |
