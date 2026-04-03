---
phase: 32-feature-gating-foundation
plan: "03"
subsystem: backend-middleware
tags: [feature-gating, middleware, fastapi, persona-tiers, security]
dependency_graph:
  requires: [32-01]
  provides: [backend-feature-enforcement, require-feature-dependency]
  affects: [workflows-router, compliance-router, sales-router, reports-router, approvals-router]
tech_stack:
  added: []
  patterns: [fastapi-router-dependencies, dependency-injection, tier-hierarchy-check]
key_files:
  created:
    - app/config/feature_gating.py
    - app/middleware/feature_gate.py
  modified:
    - app/routers/workflows.py
    - app/routers/compliance.py
    - app/routers/sales.py
    - app/routers/reports.py
    - app/routers/approvals.py
decisions:
  - "Router-level dependencies chosen over per-endpoint — ensures every endpoint in a gated router is covered without risk of missing individual endpoints"
  - "Unknown persona falls back to solopreneur (lowest tier) — fail-closed security posture"
  - "Unknown feature keys are ungated (return True) — allows gradual rollout of new gates without breaking unlisted features"
  - "approvals.py router had no prefix in APIRouter() constructor; dependency added inline without changing existing route path structure"
metrics:
  duration: "11 min"
  completed: "2026-04-03"
  tasks_completed: 2
  files_changed: 7
requirements: [GATE-02]
---

# Phase 32 Plan 03: Backend Feature Gate Middleware Summary

Backend enforcement layer for persona tier gating — HTTP 403 before handler runs, structured upgrade JSON, router-level dependencies covering all endpoints.

## What Was Built

### app/config/feature_gating.py

Python-side mirror of `frontend/src/config/featureGating.ts`. Exports:

- `TIER_ORDER` — ordered list `["solopreneur", "startup", "sme", "enterprise"]`
- `FEATURE_ACCESS` — dict mapping 8 feature keys to `{label, description, min_tier}`
- `is_feature_allowed(feature_key, user_tier) -> bool` — tier hierarchy check
- `get_required_tier(feature_key) -> str | None` — minimum tier lookup

Access matrix (mirrors frontend exactly):

| Feature | Min Tier |
|---|---|
| workflows | startup |
| sales | startup |
| reports | startup |
| approvals | startup |
| compliance | sme |
| finance-forecasting | sme |
| custom-workflows | enterprise |
| governance | enterprise |

### app/middleware/feature_gate.py

`require_feature(feature_key)` dependency factory. Returns an async FastAPI dependency that:

1. Calls `get_current_user_id` to verify JWT (deduped by FastAPI if endpoint also declares it)
2. Calls `resolve_effective_persona(user_id, request)` — checks cookie/header first, then DB profile
3. Falls back to `"solopreneur"` if no persona resolved (fail-closed)
4. Raises `HTTPException(status_code=403)` with structured body if tier check fails

403 response body:
```json
{
  "error": "feature_gated",
  "message": "Compliance Suite requires sme tier or higher. Your current tier is startup.",
  "feature": "compliance",
  "current_tier": "startup",
  "required_tier": "sme",
  "upgrade_url": "/dashboard/billing"
}
```

### Gated Routers

All five target routers updated with router-level `dependencies=[Depends(require_feature(...))]`:

| Router | Feature Key | Min Tier | Method |
|---|---|---|---|
| app/routers/workflows.py | workflows | startup | router constructor |
| app/routers/compliance.py | compliance | sme | router constructor |
| app/routers/sales.py | sales | startup | router constructor |
| app/routers/reports.py | reports | startup | router constructor |
| app/routers/approvals.py | approvals | startup | router constructor (no prefix) |

## Verification Results

All plan assertions passed:

- `is_feature_allowed('workflows', 'solopreneur')` → `False`
- `is_feature_allowed('workflows', 'startup')` → `True`
- `is_feature_allowed('compliance', 'startup')` → `False`
- `is_feature_allowed('compliance', 'sme')` → `True`
- `is_feature_allowed('governance', 'enterprise')` → `True`
- `is_feature_allowed('unknown-feature', 'solopreneur')` → `True` (ungated)
- `is_feature_allowed('workflows', 'unknown-tier')` → `False` (unknown tier = no access)
- All 8 frontend feature keys present in `FEATURE_ACCESS`
- `ruff check app/config/feature_gating.py app/middleware/feature_gate.py` → All checks passed

## Success Criteria Status

1. Solopreneur API call to /workflows returns 403 with upgrade message — enforced via `require_feature("workflows")` at router level
2. Startup API call to /workflows returns 200 — `is_feature_allowed("workflows", "startup")` returns True
3. Startup API call to /compliance returns 403 with upgrade message — `is_feature_allowed("compliance", "startup")` returns False
4. SME API call to /compliance returns 200 — `is_feature_allowed("compliance", "sme")` returns True
5. Gating config mirrors frontend config exactly — same 8 feature keys, same tier requirements
6. Adding a new gated feature requires only adding an entry to `FEATURE_ACCESS` dict — architecture confirmed

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|---|---|---|
| Task 1 | 785221b | feat(32-03): add backend feature gating config and require_feature dependency |
| Task 2 | 1676b85 | feat(32-03): apply require_feature gate to all restricted API routers |

## Self-Check: PASSED
