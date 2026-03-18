# Walkthrough: Safely Shipping a Large Changeset to Production

**Repository:** pikar-ai (Python/FastAPI backend + Next.js frontend)
**Branch:** main
**Scope:** 25+ modified files across backend agents, tools, frontend config, MCP integrations, and new service files

---

## Overview of Changes

Based on the git status, this changeset touches:

| Category | Files | Risk Level |
|----------|-------|------------|
| Agent definitions (10 agents) | `app/agents/{compliance,content,customer_support,data,financial,hr,marketing,operations,sales}/agent.py` | **HIGH** -- these are the core business logic routing layer |
| Executive orchestrator | `app/agent.py` | **HIGH** -- single entry point for all user interactions |
| Tool modules | `app/agents/tools/{agent_skills,configuration,integration_tools,social,tool_registry}.py` | **HIGH** -- tools are callable by agents at runtime |
| New tool module | `app/agents/tools/self_improve.py` (untracked) | **MEDIUM** -- new feature, no existing behavior to break |
| New services | `app/services/{interaction_logger,self_improvement_engine}.py` (untracked) | **MEDIUM** -- new feature, but touches Supabase tables |
| New skill files | `app/skills/professional_*.py` (4 files, untracked) | **LOW** -- additive skill definitions |
| Skills wiring | `app/skills/{__init__,library,loader}.py` | **MEDIUM** -- loading changes could break skill resolution |
| MCP integrations | `app/mcp/{config,integrations/email_service,tools/form_handler,tools/supabase_landing}.py` | **MEDIUM** |
| Backend config router | `app/routers/configuration.py` | **MEDIUM** -- API endpoint changes |
| Frontend config page | `frontend/src/app/dashboard/configuration/page.tsx` | **MEDIUM** |
| Frontend API route | `frontend/src/app/api/configuration/save-api-key/route.ts` | **MEDIUM** |
| Environment example | `app/.env.example` | **LOW** |
| Executive prompt | `app/prompts/executive_instruction.txt` | **LOW** -- prompt text only |
| Marketing workflow | `app/workflows/marketing.py` | **MEDIUM** |
| Social publisher | `app/social/publisher.py` | **MEDIUM** |
| Migration (untracked) | `supabase/migrations/20260318000000_self_improvement.sql` | **HIGH** -- schema change, but noted as "no migration files" in task context |

---

## Step-by-Step Procedure

### Phase 1: Pre-flight Inspection (Before Touching Anything)

#### Step 1.1 -- Full diff review

```bash
# See everything that will be committed (staged + unstaged modifications)
git diff

# See untracked files that need to be added
git status
```

**What I am looking for:**
- Any accidental debug code (`print()`, `debugger`, `console.log`)
- Hardcoded secrets, API keys, or localhost URLs that should not go to prod
- Any file that was changed by accident (e.g., lockfile churn, IDE config)
- The `.env.example` change -- verify it only adds new variable names, not actual values

**Simulation:** I would read through every hunk of the diff. With 25+ files, I would pay extra attention to the 10 agent files since they all follow the same factory pattern -- a mistake in one likely means the same mistake in all ten.

#### Step 1.2 -- Check for new environment variables

```bash
git diff app/.env.example
```

**What I am looking for:**
- If new env vars were added (likely for the self-improvement feature), they MUST be set in the Cloud Run deployment AND in Vercel before deploying, or the app will crash on startup.
- Cross-reference any new env vars against `app/config/settings.py` to confirm they have sensible defaults or `Optional` typing.

#### Step 1.3 -- Check the untracked migration file

```bash
cat supabase/migrations/20260318000000_self_improvement.sql
```

**Decision point:** The task context says "no migration files" but git status shows one. This is critical:
- If this migration creates tables that the new `self_improvement_engine.py` and `interaction_logger.py` depend on, those services will throw `relation does not exist` errors in production unless the migration is applied FIRST.
- I would read the migration SQL to understand what tables/columns it creates, then cross-reference with the new Python services.
- **If the migration is required:** It must be applied to the production Supabase instance before deploying the backend code. This means the deploy is a two-phase operation: (1) migrate DB, (2) deploy code.
- **If the migration is NOT needed yet:** Exclude it from the commit and ship separately when the feature is ready end-to-end.

---

### Phase 2: Automated Quality Gates

#### Step 2.1 -- Run the full lint suite

```bash
make lint
```

This runs:
1. `codespell` -- catches typos in code and docs
2. `ruff check . --diff` -- Python linting (E, W, F, I, N, D, UP, B, C4, SIM, ARG, PIE, PERF, RUF rules)
3. `ruff format . --check --diff` -- formatting compliance
4. `ty check .` -- type checking
5. `python scripts/verify/validate_workflow_templates.py` -- workflow template validation
6. `python scripts/verify/generate_workflow_baseline.py` -- workflow baseline generation

**Why this matters:** The pre-commit hooks include ruff, mypy, bandit security scanning, interrogate docstring coverage (80%+), and checks for bare excepts, print statements, and mutable defaults. Running `make lint` first catches the easy stuff before wasting time on test runs.

**Simulation:** Expected that this might surface:
- Missing docstrings on the new `self_improve.py` functions (interrogate requires 80%+ coverage)
- Import ordering issues in the new files
- Possibly unused imports in the modified agent files if tools were rearranged

I would fix any lint errors before proceeding.

#### Step 2.2 -- Run the full test suite

```bash
make test
```

This runs:
1. `uv sync --dev` -- ensure all dev dependencies are installed
2. `python scripts/verify/validate_workflow_templates.py` -- workflow template validation
3. `python scripts/verify/generate_workflow_baseline.py` -- baseline generation
4. `pytest tests/unit` -- unit tests
5. `pytest tests/integration` -- integration tests

**Key test files relevant to this changeset:**
- `tests/unit/test_agent_factories.py` -- verifies all 10 agent factory functions work correctly
- `tests/unit/test_tools.py` -- verifies tool registration and signatures
- `tests/unit/test_integration_tools.py` -- tests the integration_tools module directly
- `tests/unit/test_smoke.py` -- basic import/startup smoke test
- `tests/integration/test_verify_agents.py` -- verifies all agents can be instantiated
- `tests/integration/test_agent.py` -- tests the executive agent
- `tests/integration/test_multi_agent.py` -- tests cross-agent delegation
- `tests/unit/test_executive_prompt_tool_contract.py` -- verifies the executive agent's tool list matches expectations

**What I am looking for:**
- Any test failures in the agent factory tests (since all 10 agent files changed)
- Import errors from the new modules
- Tool contract violations (test_executive_prompt_tool_contract.py would catch if tool lists are inconsistent)

**Simulation:** If tests fail, I would fix them before proceeding. Common issues with this kind of changeset:
- A new tool was added to an agent but not to the test's expected tool list
- A renamed import causes an `ImportError` in one of the agent modules
- The skill loader changes break the skill registry initialization

#### Step 2.3 -- Run pre-commit hooks on all changed files

```bash
# Stage everything first to let pre-commit see the full picture
git add -A
pre-commit run --all-files
```

This runs the comprehensive `.pre-commit-config.yaml` hooks:
- File hygiene (trailing whitespace, line endings, large files, private key detection)
- Ruff lint + format
- mypy type checking
- interrogate docstring coverage
- bandit security scanning
- codespell
- hadolint for Dockerfiles
- Custom checks: bare excepts, print statements, mutable defaults

**Simulation:** The `no-commit-to-branch` hook will BLOCK a direct commit to main. This is important -- see Phase 3 for branching strategy.

---

### Phase 3: Branching Strategy

The pre-commit config includes a `no-commit-to-branch` hook that prevents direct commits to `main`. This is correct practice for a production deployment.

#### Step 3.1 -- Create a feature branch

```bash
git checkout -b feat/self-improvement-and-config-updates
```

#### Step 3.2 -- Stage files deliberately (not `git add -A`)

Given the large number of changes, I would stage files in logical groups to ensure nothing unintended gets committed:

```bash
# Group 1: Agent modifications (core business logic)
git add app/agent.py
git add app/agents/compliance/agent.py
git add app/agents/content/agent.py
git add app/agents/customer_support/agent.py
git add app/agents/data/agent.py
git add app/agents/financial/agent.py
git add app/agents/hr/agent.py
git add app/agents/marketing/agent.py
git add app/agents/operations/agent.py
git add app/agents/sales/agent.py

# Group 2: Tool modules
git add app/agents/tools/agent_skills.py
git add app/agents/tools/configuration.py
git add app/agents/tools/integration_tools.py
git add app/agents/tools/social.py
git add app/agents/tools/tool_registry.py
git add app/agents/tools/self_improve.py

# Group 3: New services
git add app/services/interaction_logger.py
git add app/services/self_improvement_engine.py

# Group 4: Skills
git add app/skills/__init__.py
git add app/skills/library.py
git add app/skills/loader.py
git add app/skills/professional_finance_legal.py
git add app/skills/professional_marketing_sales.py
git add app/skills/professional_operations_data.py
git add app/skills/professional_pm_productivity_content.py

# Group 5: MCP / integrations
git add app/mcp/config.py
git add app/mcp/integrations/email_service.py
git add app/mcp/tools/form_handler.py
git add app/mcp/tools/supabase_landing.py

# Group 6: Backend API
git add app/routers/configuration.py

# Group 7: Frontend
git add frontend/src/app/api/configuration/save-api-key/route.ts
git add frontend/src/app/dashboard/configuration/page.tsx

# Group 8: Supporting files
git add app/.env.example
git add app/prompts/executive_instruction.txt
git add app/social/publisher.py
git add app/workflows/marketing.py
```

**Explicitly NOT staged:**
- `.next/` -- build artifact, should be in .gitignore
- `.playwright-cli/` -- local tooling
- `output/` -- generated output directory
- `skills/` -- this appears to be the ship-it eval workspace, not production code
- `tiktok-demo.mp4` -- binary media file, too large for git
- `supabase/migrations/20260318000000_self_improvement.sql` -- **deferred** unless confirmed that the migration must ship with this release (see Phase 1, Step 1.3)
- `antigravity-awesome-skills` -- submodule change, needs separate handling

#### Step 3.3 -- Commit

```bash
git commit -m "$(cat <<'EOF'
feat: add self-improvement engine, professional skills, and config page updates

- Add autonomous self-improvement system (interaction logger + evaluation engine)
- Wire 62 professional skills across 4 domain modules
- Update all 10 agent definitions for new skill and tool integration
- Enhance configuration page UI and backend API route
- Update MCP integration configs and social publisher

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Phase 4: Frontend Verification

#### Step 4.1 -- Frontend build check

```bash
cd frontend && npm run build
```

**Why:** The Next.js build is the single most reliable way to catch TypeScript errors, broken imports, and SSR issues in the frontend. The configuration page (`page.tsx`) and API route (`route.ts`) both changed -- a build failure here would mean a broken Vercel deployment.

**What I am looking for:**
- TypeScript compilation errors in the changed files
- Missing imports (new Lucide icons, changed component props)
- API route handler signature issues

#### Step 4.2 -- Frontend lint check

```bash
cd frontend && npm run lint
```

Catches ESLint issues specific to the Next.js/React codebase.

---

### Phase 5: Local Integration Test (Smoke Test the Full Stack)

#### Step 5.1 -- Start backend + Redis locally

```bash
docker compose up --build
```

The `--build` flag forces a fresh image build, which validates:
- The Dockerfile can install all Python dependencies (catches missing deps)
- The FastAPI app starts without import errors
- The health check at `/health/live` passes within 90 seconds

#### Step 5.2 -- Hit health endpoints

```bash
# Liveness (no deps)
curl http://localhost:8000/health/live

# Supabase + cache connectivity
curl http://localhost:8000/health/connections

# Redis + circuit breaker
curl http://localhost:8000/health/cache
```

**What I am looking for:** All endpoints return 200. If `/health/connections` fails, the self-improvement tables might not exist yet (migration not applied).

#### Step 5.3 -- Test the configuration endpoint

```bash
# Get MCP tool status (the endpoint that the frontend config page calls)
curl http://localhost:8000/configuration/tools-status

# Verify the response shape matches what the frontend expects
```

**Why:** Both the backend router (`app/routers/configuration.py`) and the frontend page (`configuration/page.tsx`) changed. If the API contract changed (field names, response shape), the frontend will break silently -- no build error, just a runtime failure.

#### Step 5.4 -- Start frontend locally

```bash
cd frontend && npm run dev
```

Then manually navigate to `http://localhost:3000/dashboard/configuration` and verify:
- The page loads without a white screen
- API key configuration UI renders correctly
- Social media connection cards appear
- No console errors in browser dev tools

#### Step 5.5 -- Test agent instantiation via ADK playground

```bash
make playground
```

Navigate to `http://localhost:8501`, select the `app` folder, and send a simple message like "Hello, what can you do?" to verify:
- The ExecutiveAgent starts without errors
- All 10 sub-agents are registered correctly
- Tool lists are populated (no `ImportError` from changed tool modules)
- The self-improvement tools appear in the tool list

---

### Phase 6: Push and Deploy

#### Step 6.1 -- Push the feature branch

```bash
git push -u origin feat/self-improvement-and-config-updates
```

#### Step 6.2 -- Create a Pull Request

```bash
gh pr create \
  --title "feat: self-improvement engine, professional skills, config updates" \
  --body "$(cat <<'EOF'
## Summary
- Add autonomous self-improvement system (interaction logger, evaluation engine, agent tools)
- Wire 62 professional skills across 4 domain modules (finance/legal, marketing/sales, operations/data, PM/productivity/content)
- Update all 10 specialized agent definitions for new tool and skill integration
- Enhance frontend configuration page and backend configuration API
- Update MCP integration configs, social publisher, and marketing workflow

## Changed file categories
- **10 agent files** -- updated tool lists and instructions
- **5 tool modules** -- new self_improve tools, updated configuration/integration/social/registry
- **4 new skill files** -- professional skill definitions
- **2 new service files** -- interaction_logger.py, self_improvement_engine.py
- **Frontend config** -- page.tsx + API route
- **MCP/integrations** -- config, email, forms, landing pages

## Risk assessment
- HIGH: All 10 agents changed -- verified via test_agent_factories and test_verify_agents
- HIGH: Executive agent tool list changed -- verified via test_executive_prompt_tool_contract
- MEDIUM: Frontend config page -- verified via `npm run build` and manual smoke test
- NOTE: Migration file (self_improvement tables) deferred to separate PR

## Test plan
- [ ] `make lint` passes
- [ ] `make test` passes (unit + integration)
- [ ] `npm run build` succeeds in frontend/
- [ ] Local Docker Compose startup succeeds
- [ ] Health endpoints return 200
- [ ] Configuration page loads and renders correctly
- [ ] ADK playground agent responds without errors
- [ ] All 10 sub-agents reachable via delegation

Generated with Claude Code
EOF
)"
```

#### Step 6.3 -- Wait for CI (if configured)

If the repo has CI/CD pipelines (GitHub Actions, Cloud Build), wait for all checks to pass on the PR before merging.

#### Step 6.4 -- Database migration (if applicable)

**BEFORE deploying the backend**, if the self-improvement migration is required:

```bash
# Apply to production Supabase
supabase db push --linked
```

Or via the Supabase dashboard: run the SQL in `supabase/migrations/20260318000000_self_improvement.sql` against the production database.

**Critical ordering:** Database schema must exist BEFORE the new backend code deploys, because the `interaction_logger.py` and `self_improvement_engine.py` services will attempt to query those tables on startup or first use. If the services are designed to be fire-and-forget (as the `InteractionLogger` docstring suggests), a missing table would log warnings but not crash the app. However, it is still better to migrate first.

#### Step 6.5 -- Deploy backend to Cloud Run

```bash
make deploy
```

This runs:
```bash
gcloud beta run deploy pikar-ai \
  --source . \
  --memory "4Gi" \
  --project $PROJECT_ID \
  --region "us-central1" \
  --no-allow-unauthenticated \
  --no-cpu-throttling \
  ...
```

**Post-deploy verification:**

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")

# Get an identity token for authenticated requests
TOKEN=$(gcloud auth print-identity-token)

# Health checks
curl -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
curl -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/connections"
curl -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/cache"

# Verify configuration endpoint
curl -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/configuration/tools-status"
```

#### Step 6.6 -- Deploy frontend to Vercel

The frontend deploys via Vercel. If Vercel is connected to the GitHub repo, merging the PR to `main` will trigger an automatic deployment. Otherwise:

```bash
cd frontend && vercel --prod
```

**Pre-deploy checklist for Vercel:**
- Verify `NEXT_PUBLIC_API_URL` environment variable in Vercel project settings points to the Cloud Run service URL
- Verify `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set
- If any new env vars were added in `app/.env.example`, add them to Vercel project settings

**Post-deploy verification:**
- Navigate to the production URL `/dashboard/configuration`
- Verify the page loads, API key forms render, social connections display
- Open browser dev tools, check for failed network requests or console errors

---

### Phase 7: Post-Deploy Monitoring

#### Step 7.1 -- Watch Cloud Run logs for errors

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=pikar-ai AND severity>=ERROR" \
  --limit=50 \
  --format="table(timestamp, textPayload)" \
  --freshness=15m
```

**What I am looking for:**
- `ImportError` or `ModuleNotFoundError` -- indicates a missing dependency or broken import chain
- `relation "interaction_logs" does not exist` -- indicates the migration was not applied
- `AttributeError` -- indicates a broken tool or agent reference
- Any stack traces from the agent factory functions

#### Step 7.2 -- Verify agent delegation works end-to-end

Send a test message through the production SSE endpoint (or via the frontend chat) that exercises cross-agent delegation:

> "Give me a financial summary and then create a marketing plan for Q2"

This tests:
- ExecutiveAgent routes to FinancialAgent (one of the 10 modified agents)
- ExecutiveAgent routes to MarketingAgent (another modified agent)
- Tool invocations work correctly
- The response streams back via SSE without errors

#### Step 7.3 -- Check Vercel deployment logs

```bash
vercel logs --prod
```

Or check the Vercel dashboard for the latest deployment's function logs.

---

## Rollback Plan

If something breaks in production:

### Backend rollback

```bash
# List recent Cloud Run revisions
gcloud run revisions list --service pikar-ai --region us-central1

# Route 100% traffic to the previous revision
gcloud run services update-traffic pikar-ai \
  --region us-central1 \
  --to-revisions=PREVIOUS_REVISION_NAME=100
```

Cloud Run keeps previous revisions, so rollback is near-instant (no rebuild required).

### Frontend rollback

In the Vercel dashboard, navigate to Deployments, find the previous successful deployment, and click "Promote to Production". This is also near-instant.

### Database rollback

If the self-improvement migration was applied and needs reverting:
```sql
DROP TABLE IF EXISTS improvement_actions;
DROP TABLE IF EXISTS skill_scores;
DROP TABLE IF EXISTS coverage_gaps;
DROP TABLE IF EXISTS interaction_logs;
```

**Caution:** Only do this if no production data has been written to these tables.

---

## Summary of Safety Checks

| Check | Command | Blocks Deploy? |
|-------|---------|----------------|
| Python lint (ruff, codespell, ty) | `make lint` | YES |
| Python tests (unit + integration) | `make test` | YES |
| Frontend TypeScript build | `cd frontend && npm run build` | YES |
| Frontend lint | `cd frontend && npm run lint` | YES |
| Pre-commit hooks | `pre-commit run --all-files` | YES |
| Docker Compose startup | `docker compose up --build` | YES |
| Health endpoint verification | `curl /health/*` | YES |
| Configuration page manual test | Browser check | YES |
| ADK playground smoke test | `make playground` | Recommended |
| New env vars in prod | Check Cloud Run + Vercel settings | YES |
| Migration applied (if needed) | `supabase db push --linked` | YES (if services depend on new tables) |
| Post-deploy log monitoring | `gcloud logging read ...` | N/A (post-deploy) |
| Post-deploy E2E agent test | Send test messages | N/A (post-deploy) |

**Bottom line:** With 25+ files changed across both backend and frontend, the key risks are (1) broken imports in the agent chain causing a cascade failure, (2) API contract mismatches between the frontend config page and backend router, and (3) missing database tables for the new self-improvement feature. The automated test suite (`make test`) covers risk #1 thoroughly with agent factory tests and tool contract tests. Risk #2 requires a manual smoke test of the configuration page against the running backend. Risk #3 requires confirming whether the migration should ship with this release and, if so, applying it before the backend deploy.
