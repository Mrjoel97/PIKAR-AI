# Pipeline Commands Reference

Exact commands for each phase of the ship-it pipeline, specific to the pikar-ai project.

---

## Phase 1: Scan

```bash
git status
git diff
git diff --staged
git log --oneline -5
```

Categorize files by domain:
```bash
# Backend changes
git diff --name-only | grep -E '^app/'

# Frontend changes
git diff --name-only | grep -E '^frontend/'

# Migration changes
git diff --name-only | grep -E '^supabase/migrations/'

# Config changes
git diff --name-only | grep -E '(pyproject\.toml|package\.json|Makefile|Dockerfile|vercel\.json|\.env)'

# Test changes
git diff --name-only | grep -E '(^tests/|__tests__)'
```

---

## Phase 2: Timing Guard

```bash
# Check current time
date +"%H:%M %Z"

# Check if it's a weekend
date +"%u"  # 6=Saturday, 7=Sunday
```

Business hours: 7 AM - 10 PM local time, Monday-Friday.
Outside these hours, warn the user.

---

## Phase 3: Quality Gates (Parallel Execution)

### Parallel Execution Strategy

Backend and frontend quality gates are independent. Run them simultaneously to cut pipeline time in half.

**Option A: Parallel subagents** (preferred)
Spawn two Agent subagents — one for backend, one for frontend. Each runs its full quality gate independently and reports back.

**Option B: Background bash commands**
```bash
# Start backend quality gate in background
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
BACKEND_PID=$!

# Start frontend quality gate in background (only if frontend changed)
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
FRONTEND_PID=$!

# Wait for both
wait $BACKEND_PID
BACKEND_EXIT=$?
wait $FRONTEND_PID
FRONTEND_EXIT=$?

echo "Backend: exit $BACKEND_EXIT"
echo "Frontend: exit $FRONTEND_EXIT"
cat /tmp/backend-quality.log
cat /tmp/frontend-quality.log
```

### Backend Commands (Individual)

```bash
# Lint auto-fix
uv run ruff check app/ --fix

# Format
uv run ruff format app/

# Spell check
uv run codespell

# Type check
uv run ty check .

# Workflow validation
uv run python scripts/verify/validate_workflow_templates.py
uv run python scripts/verify/generate_workflow_baseline.py

# Unit tests
uv run pytest tests/unit -q

# Integration tests
uv run pytest tests/integration -q
```

Ruff config is in `pyproject.toml`:
- Rules: E, F, W, I, C, B, UP, RUF
- Ignored: E501 (line length), C901 (complexity), B006 (mutable defaults)
- Line length: 88
- Target: Python 3.10

### Frontend Commands (Individual)

```bash
# ESLint
cd frontend && npm run lint

# TypeScript type check
cd frontend && npx tsc --noEmit

# Tests
cd frontend && npm test

# Build verification
cd frontend && CI=1 NEXT_TELEMETRY_DISABLE=1 \
  NEXT_PUBLIC_API_URL=http://localhost:8000 \
  NEXT_PUBLIC_SUPABASE_URL=https://example.supabase.co \
  NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_test_key \
  npm run build
```

### CI-Specific Tests (what GitHub Actions runs)

```bash
# Backend trust gate
uv run python scripts/verify/check_migrations.py
uv run python scripts/verify/validate_workflow_templates.py
uv run python scripts/verify/validate_journey_workflow_references.py
uv run pytest tests/unit/test_product_truth_guards.py \
  tests/unit/test_workflow_execution_contracts.py \
  tests/unit/test_workflow_template_tool_resolution.py -q

# Frontend trust gate
cd frontend && npm ci
cd frontend && npm test -- src/__tests__/services/api.test.ts --run --pool=threads --maxWorkers=1
cd frontend && npm run build
```

---

## Phase 4: Supabase Migration

See `references/supabase-migrations.md` for the full MCP tool workflow.

Quick reference:
```
# 1. Find project ID
Tool: mcp__plugin_supabase_supabase__list_projects

# 2. Check current migrations
Tool: mcp__plugin_supabase_supabase__list_migrations { project_id }

# 3. Validate schema targets
Tool: mcp__plugin_supabase_supabase__list_tables { project_id, schemas: ["public"], verbose: true }

# 4. Dry-run validation
Tool: mcp__plugin_supabase_supabase__execute_sql { project_id, query: "<validation>" }

# 5. Apply migration
Tool: mcp__plugin_supabase_supabase__apply_migration { project_id, name, query }

# 6. Advisory scan (BOTH types)
Tool: mcp__plugin_supabase_supabase__get_advisors { project_id, type: "security" }
Tool: mcp__plugin_supabase_supabase__get_advisors { project_id, type: "performance" }

# 7. Check Postgres logs
Tool: mcp__plugin_supabase_supabase__get_logs { project_id, service: "postgres" }
```

---

## Phase 5: Environment Variable Diff

### Backend — Cloud Run

```bash
# Get current production env vars
gcloud run services describe pikar-ai \
  --region us-central1 \
  --format="yaml(spec.template.spec.containers[0].env)"

# Compare with .env.example
diff <(grep -E '^[A-Z_]+=' .env.example | cut -d= -f1 | sort) \
     <(gcloud run services describe pikar-ai --region us-central1 \
       --format="json(spec.template.spec.containers[0].env[].name)" 2>/dev/null | \
       python3 -c "import sys,json; [print(e['name']) for e in json.load(sys.stdin)]" | sort) \
     || true
```

### Frontend — Vercel

```bash
# List Vercel env vars
cd frontend && vercel env ls

# Check expected vars
grep -E '^NEXT_PUBLIC_' frontend/.env.example 2>/dev/null | cut -d= -f1 | sort
```

### Setting Missing Vars

```bash
# Cloud Run — non-secret env var
gcloud run services update pikar-ai \
  --region us-central1 \
  --update-env-vars "VAR_NAME=value"

# Vercel — interactive (asks for value)
cd frontend && vercel env add VAR_NAME production
```

---

## Phase 6: Git Operations

### Stage specific files (never blind git add)

```bash
# Stage Python changes
git add app/**/*.py

# Stage frontend changes
git add frontend/src/**/*.{ts,tsx}

# Stage config changes (review first)
git add pyproject.toml frontend/package.json

# Stage migration changes
git add supabase/migrations/*.sql
```

### Commit

```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <description>

<body if needed>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 7: PR Creation

```bash
# Create branch if on main
git checkout -b ship/<description>

# Push
git push -u origin <branch-name>

# Create PR
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
- <changes>

## Quality Gates
- [x] Lint (ruff check + format + codespell)
- [x] Type check (ty + tsc)
- [x] Tests (pytest + vitest)
- [x] Build verification (next build)
- [x] Migration validation (Supabase MCP)
- [x] Security advisory check (Supabase)
- [x] Env var diff (Cloud Run + Vercel)

## Deployment Plan
- Database: Supabase migrations (if applicable)
- Backend: Cloud Run (canary: 10% → 50% → 100%)
- Frontend: Vercel (atomic deploy)

## Test plan
- [ ] Backend health checks pass at each canary stage
- [ ] Frontend loads correctly
- [ ] Performance within baseline thresholds
- [ ] No new security advisories
EOF
)"

# Monitor CI
gh pr checks <pr-number> --watch
```

---

## Phase 8: Merge

```bash
# Check merge readiness
gh pr checks <pr-number>

# Merge
gh pr merge <pr-number> --merge --delete-branch

# Update local
git checkout main && git pull origin main
```

---

## Phase 10: Performance Baselines

```bash
SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")
TOKEN=$(gcloud auth print-identity-token)

# Collect 3 samples per endpoint (discard first for cold start)
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

---

## Phase 11: Deploy

### Backend — Cloud Run (Canary)

```bash
# Step 1: Deploy without traffic
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

# Step 2: Get new revision name
NEW_REV=$(gcloud run revisions list --service pikar-ai --region us-central1 --limit 1 --format="value(REVISION)")

# Step 3: Canary at 10%
gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=$NEW_REV=10

# Step 4: Verify, then ramp to 50%
gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=$NEW_REV=50

# Step 5: Verify, then ramp to 100%
gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=$NEW_REV=100
```

### Backend — Cloud Run (Direct, if canary not needed)

```bash
make deploy
```

### Frontend — Vercel

```bash
# Install CLI if needed
npm i -g vercel

# Link project if needed
cd frontend && vercel link

# Deploy to production
cd frontend && vercel --prod
```

---

## Phase 12: Verify

### Backend health checks

```bash
SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")
TOKEN=$(gcloud auth print-identity-token)

curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/connections"
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/cache"
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/workflows/readiness"
```

### Frontend verification

```bash
vercel ls --prod
curl -s -o /dev/null -w "%{http_code}" <vercel-url>
```

### Cloud Run error check

```bash
gcloud run logs read pikar-ai --region us-central1 --limit 20 --log-filter="severity>=ERROR"
```

---

## Phase 13: Rollback

### Cloud Run

```bash
# Find previous revision
gcloud run revisions list --service pikar-ai --region us-central1 --limit 5

# Route all traffic to previous
gcloud run services update-traffic pikar-ai --region us-central1 --to-revisions=<previous-revision>=100

# Verify
TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
```

### Vercel

```bash
# Rollback to previous deployment
vercel rollback

# Or promote a specific deployment
vercel promote <previous-deployment-url>

# Verify
curl -s -o /dev/null -w "%{http_code}" <production-url>
```

---

## Phase 14: Notification

### Git deployment tag

```bash
# Tag the deployment
TAG="deploy/$(date +%Y%m%d)-$(git rev-parse --short HEAD)"
git tag $TAG
git push origin $TAG
```

### Rollback tag (if rolled back)

```bash
TAG="rollback/$(date +%Y%m%d)-$(git rev-parse --short HEAD)"
git tag $TAG
git push origin $TAG
```
