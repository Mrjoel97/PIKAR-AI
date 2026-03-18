---
name: ship-it
description: Full CI/CD pipeline automation — scans changes for errors, runs lint/type-check/tests in parallel, auto-fixes issues, handles Supabase migrations via MCP with advisory checks, commits, creates PRs, merges to main, deploys to both Vercel and Cloud Run with canary traffic strategy, verifies both deployments with performance baselines, and auto-rollbacks on failure. Use this skill whenever the user says "ship it", "deploy everything", "push to production", "release", "send it", "merge and deploy", or wants to go from local changes to live production in one shot. Also use when the user wants to run the full quality gate pipeline before deploying, or when they want to verify and fix deployment issues on both platforms.
---

# Ship It — Full Pipeline Automation

This skill takes the codebase from its current state all the way to verified production deployments on both Vercel (frontend) and Google Cloud Run (backend). It is sequential and relentless — it does not stop until both deployments are confirmed healthy, fixing issues along the way.

## Philosophy

The pipeline follows a "measure twice, cut once" approach: it runs every quality check before touching git, and only deploys after the PR is clean-merged. If a deployment fails, it diagnoses, fixes, and retries. If retries are exhausted, it auto-rollbacks to the last known-good state. It never leaves production in a broken state.

## Before You Start

Read `references/pipeline-commands.md` for the exact commands for each phase.
Read `references/deployment-verification.md` for health checks, rollback, canary, env diffing, and performance baselines.
Read `references/supabase-migrations.md` when migration files are in the changeset.

## Pipeline Phases

Use TaskCreate to track each phase. Mark each in_progress before starting and completed when done. If a phase fails, create a sub-task for the fix before retrying.

---

### Phase 1: Scan and Assess

Understand what has changed before touching anything.

1. Run `git status` to see all modified, staged, and untracked files.
2. Run `git diff` to see the actual changes (staged and unstaged).
3. Categorize changes into domains:
   - **backend** — `app/**/*.py`
   - **frontend** — `frontend/src/**/*.{ts,tsx}`
   - **migrations** — `supabase/migrations/*.sql`
   - **config** — `pyproject.toml`, `package.json`, `Makefile`, `Dockerfile`, `vercel.json`
   - **tests** — `tests/**/*.py`, `frontend/src/__tests__/**`
4. Report a summary to the user: "X files changed across Y domains."
5. Flag any migration files — these trigger the Supabase Migration phase later.

If there are no changes at all, tell the user and stop.

### Phase 2: Deployment Timing Guard

Before investing time in quality gates, check whether it is safe to deploy.

1. Check project memory for any active merge freezes or deployment blackouts.
2. Check the current time — if outside business hours (before 7 AM or after 10 PM local), warn the user:
   > "It's currently outside business hours. Deploying now means fewer eyes on production. Proceed?"
3. Check if there are any active incidents on Cloud Run or Vercel status pages (if accessible).
4. If the user confirms, proceed. If not, stop and save progress so they can resume later.

### Phase 3: Quality Gates (Parallel Execution)

Run backend and frontend quality checks in parallel since they are independent. Use subagents or parallel bash commands.

**Backend quality gate (run together):**
1. `uv run ruff check app/ --fix` — auto-fix Python lint issues
2. `uv run ruff format app/` — auto-format Python code
3. `uv run codespell` — catch spelling errors
4. `uv run ty check .` — Python type checking
5. `uv run python scripts/verify/validate_workflow_templates.py` — workflow validation
6. `uv run python scripts/verify/generate_workflow_baseline.py` — baseline generation
7. `uv run pytest tests/unit -q` — unit tests
8. `uv run pytest tests/integration -q` — integration tests

**Frontend quality gate (run together, only if frontend files changed):**
1. `cd frontend && npm run lint` — ESLint
2. `cd frontend && npx tsc --noEmit` — TypeScript type check
3. `cd frontend && npm test` — frontend tests
4. `cd frontend && npm run build` — build verification

**After both complete:**
- If lint auto-fix changed files, note them for staging.
- If any errors remain that cannot be auto-fixed, fix them manually.
- If tests fail due to current changes, fix them. Pre-existing failures unrelated to current changes should be noted and flagged to the user.

Success: zero errors across all quality gates.
If unfixable: report the specific errors and ask the user whether to proceed or abort.

### Phase 4: Supabase Migration Gate

**Skip this phase if no files in `supabase/migrations/` were modified or added.**

This phase ensures database migrations are clean and safe before they reach production. Read `references/supabase-migrations.md` for the full MCP tool workflow.

1. **Identify the project**: Use `mcp__plugin_supabase_supabase__list_projects` to find the pikar-ai project ID.

2. **Check current migration state**: Use `mcp__plugin_supabase_supabase__list_migrations` to see what migrations are already applied in production. Compare against the local `supabase/migrations/` directory to identify which migrations are new.

3. **Validate migration SQL**: For each new migration file:
   - Read the SQL content.
   - Check for common issues: missing `IF NOT EXISTS`, destructive `DROP` without guards, missing `BEGIN`/`COMMIT` transaction wrapping.
   - Verify that referenced tables/columns exist using `mcp__plugin_supabase_supabase__list_tables` with `verbose: true`.

4. **Dry-run validation**: Use `mcp__plugin_supabase_supabase__execute_sql` to run non-destructive validation queries:
   - Check if tables/columns being referenced exist.
   - Verify no naming conflicts with existing objects.
   - Validate foreign key targets exist.

5. **Apply migrations**: Use `mcp__plugin_supabase_supabase__apply_migration` for each new migration in order. Provide the migration name (from the filename, in snake_case) and the SQL content.

6. **Post-migration advisory scan**: This is critical. Run BOTH advisory checks:
   - `mcp__plugin_supabase_supabase__get_advisors` with `type: "security"` — catches missing RLS policies, exposed schemas, insecure defaults.
   - `mcp__plugin_supabase_supabase__get_advisors` with `type: "performance"` — catches missing indexes, table bloat, inefficient queries.

7. **Remediate advisories**: If advisories are found:
   - For **security** advisories (missing RLS, exposed tables): these are blockers. Create a new migration to fix them, apply it, and re-check.
   - For **performance** advisories (missing indexes): warn the user but do not block deployment unless the advisory is critical.
   - Include remediation URLs from the advisory response so the user can reference the issues.

8. **Verify migration integrity**: Use `mcp__plugin_supabase_supabase__list_migrations` again to confirm all new migrations were applied successfully.

9. **Check Postgres logs**: Use `mcp__plugin_supabase_supabase__get_logs` with `service: "postgres"` to check for any errors or warnings from the migration application.

Success: all migrations applied, zero security advisories, performance advisories documented.
If migration fails: read the error, fix the SQL, create a corrective migration, and retry.

### Phase 5: Environment Variable Diff

Before deploying, verify that production environment variables match what the code expects.

**Backend — Cloud Run:**
1. Run `gcloud run services describe pikar-ai --region us-central1 --format="yaml(spec.template.spec.containers[0].env)"` to get current production env vars.
2. Read the local `.env.example` to see what the code expects.
3. Compare the two lists. Flag any variables that:
   - Exist in `.env.example` but not in Cloud Run (missing in prod).
   - Were recently added to the codebase but not yet configured in Cloud Run.
4. For missing variables, warn the user and ask if they should be set before deploying.

**Frontend — Vercel:**
1. Run `cd frontend && vercel env ls` to see current Vercel env vars.
2. Check `frontend/.env.example` or `frontend/.env.local.example` for expected variables.
3. Flag any `NEXT_PUBLIC_*` variables that are missing — these will cause runtime failures in the browser.

Success: all required env vars are present in both platforms.
If missing: warn the user. For non-secret vars, offer to set them. For secrets, ask the user to configure them manually.

### Phase 6: Stage and Commit

Only reach this phase if all quality gates and migration checks passed.

1. Run `git status` again to see the full picture (including auto-fix changes from Phase 3).
2. Stage all relevant files. Be specific — do not use `git add .` blindly. Exclude `.env` files, credentials, large binaries, and `node_modules/`.
3. Analyze the changes and craft a commit message:
   - Summarize the nature (feat, fix, refactor, chore, etc.)
   - Focus on the "why" not the "what"
   - Keep it concise (1-2 sentences)
4. Create the commit.
5. Verify with `git status` that the working tree is clean (or only has intentionally untracked files).

### Phase 7: Push and Create PR

1. Determine the current branch name. If on `main`, create a feature branch first:
   ```
   git checkout -b ship/<short-description>
   ```
2. Push the branch to origin: `git push -u origin <branch-name>`
3. Create a PR to `main` using `gh pr create`:
   - Title: concise summary (under 70 chars)
   - Body: include quality gate results, migration status, deployment plan
4. Wait for CI checks if GitHub Actions are configured. Monitor with `gh pr checks <pr-number>`.

Success: PR created and CI checks pass.
If CI fails: diagnose, fix locally, push again, repeat.

### Phase 8: Merge to Main

1. Check the PR is ready to merge: CI passed, no conflicts.
2. If there are merge conflicts, resolve them:
   - `git fetch origin main`
   - `git merge origin/main` (or rebase if the user prefers)
   - Fix conflicts, commit, push
3. Merge the PR: `gh pr merge <pr-number> --merge --delete-branch`
4. Pull the latest main locally: `git checkout main && git pull origin main`

Success: PR merged, local main is up to date.

### Phase 9: Post-Merge Main Scan

After merging, verify main is healthy before deploying.

1. Run the same quality gates from Phase 3 on main to catch any integration issues.
2. If new issues are found on main (e.g., from merge resolution), fix them immediately:
   - Create a fix commit directly on main
   - Or create a hotfix branch, PR, and merge
3. Verify the build still passes.

Success: main passes all quality gates.

### Phase 10: Capture Pre-Deploy Baselines

Before deploying new code, capture performance baselines from the current production so you can detect regressions.

Read `references/deployment-verification.md` § Performance Baseline for the full strategy.

1. **Backend baseline**: Hit each health endpoint 3 times and record average response times:
   - `/health/live` — expected <50ms
   - `/health/connections` — expected <200ms
   - `/health/cache` — expected <100ms
2. **Frontend baseline**: Record the current production page load time (if accessible).
3. Save these baselines in memory for comparison after deployment.

### Phase 11: Deploy with Canary Strategy

Deploy to both platforms, but use canary traffic splitting where supported to catch issues before full rollout.

Read `references/deployment-verification.md` § Canary Deployment for the full strategy.

**Backend — Cloud Run (Canary):**
1. Deploy the new revision WITHOUT migrating traffic:
   ```
   gcloud run deploy pikar-ai --source . --region us-central1 --no-traffic [... other flags from Makefile]
   ```
2. Route 10% of traffic to the new revision:
   ```
   gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=<new-revision>=10
   ```
3. Verify health at 10% (hit health endpoints, check logs for errors).
4. If healthy at 10%, ramp to 50%:
   ```
   gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=<new-revision>=50
   ```
5. Verify again at 50%.
6. If healthy at 50%, ramp to 100%:
   ```
   gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=<new-revision>=100
   ```

If errors spike at any canary stage: immediately rollback traffic to the previous revision (see Rollback section).

**Frontend — Vercel:**
1. Run `cd frontend && vercel --prod`.
2. Vercel handles atomic deployments — the new version replaces the old one instantly.
3. Capture the deployment URL.

If either deployment command fails:
- Read the error output carefully.
- Common issues: auth expired, quota exceeded, build timeout, missing env vars.
- Fix the issue and retry. Do NOT give up.

### Phase 12: Verify Deployments and Compare Baselines

This is the most critical phase. Do not report success until both deployments are confirmed healthy AND performance has not regressed.

Read `references/deployment-verification.md` for the full verification strategy.

**Backend verification (Cloud Run):**
1. Hit `/health/live` — should return 200.
2. Hit `/health/connections` — should show Supabase + cache status "healthy".
3. Hit `/health/cache` — should show Redis status.
4. Hit `/health/workflows/readiness` — should show workflow engine ready.
5. If any health check fails, check Cloud Run logs: `gcloud run logs read pikar-ai --region us-central1 --limit 50`

**Frontend verification (Vercel):**
1. Hit the Vercel deployment URL — should return 200.
2. Check Vercel deployment status: `vercel inspect <deployment-url>` or `vercel ls --prod`.
3. If the page returns errors, check build logs: `vercel logs <deployment-url>`.

**Performance comparison:**
1. Hit the same health endpoints 3 times and record average response times.
2. Compare against Phase 10 baselines.
3. If any endpoint is >2x slower than baseline, flag it as a performance regression.
4. Performance regressions are warnings, not blockers — report them but don't roll back unless the endpoint is timing out.

**Post-deploy Supabase advisory re-check:**
If migrations were applied in Phase 4, run the advisory checks again:
- `mcp__plugin_supabase_supabase__get_advisors` with `type: "security"`
- `mcp__plugin_supabase_supabase__get_advisors` with `type: "performance"`
This catches any issues that emerged from the deployed code interacting with the new schema.

**Retry loop:**
If either deployment is unhealthy:
1. Diagnose the specific failure from logs and health checks.
2. Determine if it's a code issue or an infrastructure/config issue.
3. For code issues: fix, commit, push, re-deploy.
4. For infra issues: fix the config (env vars, secrets, scaling) and re-deploy.
5. Verify again after each fix.
6. Repeat until BOTH deployments are confirmed healthy.
7. Maximum retry attempts: 5 per platform. After 5 failures, trigger auto-rollback.

### Phase 13: Auto-Rollback (if needed)

If Phase 12 retries are exhausted and a deployment is still unhealthy, automatically rollback to protect production.

Read `references/deployment-verification.md` § Rollback Automation for exact commands.

**Backend rollback (Cloud Run):**
1. Get the previous known-good revision:
   ```
   gcloud run revisions list --service pikar-ai --region us-central1 --limit 5
   ```
2. Route 100% traffic to the previous revision:
   ```
   gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=<previous-revision>=100
   ```
3. Verify the rollback is healthy.

**Frontend rollback (Vercel):**
1. List recent deployments: `vercel ls --prod`
2. Promote the previous deployment: `vercel promote <previous-deployment-url>`
3. Verify the rollback is healthy.

After rollback:
- Report exactly what failed and why.
- Include logs, health check responses, and the specific error.
- Present a diagnosis to the user with recommended next steps.
- Do NOT attempt to re-deploy — the user needs to review the diagnosis first.

### Phase 14: Notification

After the pipeline completes (success or rollback), send a status notification.

1. **Console report** (always):
```
SHIP IT COMPLETE
================
Status: SUCCESS | PARTIAL (rollback on <platform>) | FAILED (rollback on both)

Backend (Cloud Run):  <service-url> — HEALTHY | ROLLED BACK to <revision>
Frontend (Vercel):    <deployment-url> — HEALTHY | ROLLED BACK to <deployment>
Database (Supabase):  <migration-count> migrations applied | NO MIGRATIONS

Performance:
  /health/live:        <new-time>ms (baseline: <old-time>ms) — OK | REGRESSION
  /health/connections: <new-time>ms (baseline: <old-time>ms) — OK | REGRESSION

Changes shipped:
- <summary of what was deployed>

PR: <pr-url>
Commit: <commit-hash>
Duration: <total-pipeline-time>
```

2. **Git tag** (on success): tag the commit with a deployment marker:
   ```
   git tag deploy/<date>-<short-hash> && git push origin deploy/<date>-<short-hash>
   ```

---

## Abort Conditions

Stop and ask the user before proceeding if:
- There are changes to `.env` files with secrets
- The changes touch auth/security code
- More than 30 files changed (confirm scope)
- Pre-existing test failures exist that might affect production
- Deployment timing guard warns about off-hours or merge freeze
- Supabase security advisories are found after migration

## Error Recovery Patterns

| Error | Diagnosis | Fix |
|-------|-----------|-----|
| `gcloud auth` expired | Token refresh needed | `gcloud auth login` then retry |
| Vercel not linked | Project not connected | `vercel link` then retry |
| Vercel CLI missing | CLI not installed | `npm i -g vercel` then retry |
| Build OOM | Container memory limit | Check for memory leaks, increase `--memory` |
| Health check timeout | Service still starting | Wait 30s and retry (cold start) |
| 503 on Cloud Run | Revision not ready | Check revision status, wait for ready |
| Merge conflict | Concurrent changes on main | Fetch, merge/rebase, resolve, push |
| CI check failed | Code quality issue | Read CI logs, fix, push again |
| Redis connection refused | Redis not available | Check REDIS_HOST/REDIS_PORT config |
| Supabase connection error | DB config wrong | Verify SUPABASE_URL and keys |
| Migration failed | SQL error | Read error, fix SQL, create corrective migration |
| RLS policy missing | Security advisory | Create migration to enable RLS, apply, re-check |
| Missing env var in prod | Env var diff detected | Set via `gcloud run services update` or `vercel env add` |
| Performance regression | Response time >2x baseline | Investigate code changes, check for N+1 queries |
| Canary errors at 10% | New revision has bugs | Rollback traffic to previous revision immediately |
