---
phase: 38
slug: solopreneur-unlock-tool-honesty
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), jest/vitest (frontend) |
| **Config file** | pyproject.toml (pytest section), frontend/jest.config.ts |
| **Quick run command** | `uv run pytest tests/unit/test_feature_gating.py tests/unit/test_persona_policy.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds (quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/test_feature_gating.py tests/unit/test_persona_policy.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 38-01-01 | 01 | 1 | SOLO-01..06 | unit | `uv run pytest tests/unit/test_feature_gating.py -x -q` | ✅ | ⬜ pending |
| 38-01-02 | 01 | 1 | SOLO-06 | unit | `cd frontend && npx jest --testPathPattern featureGating` | ❌ W0 | ⬜ pending |
| 38-02-01 | 02 | 2 | TOOL-01..07 | unit | `uv run pytest tests/unit/test_enhanced_tools.py -x -q` | ❌ W0 | ⬜ pending |
| 38-02-02 | 02 | 2 | TOOL-01..07 | grep | `grep -r "manage_hubspot\|run_security_audit\|deploy_container" app/` | N/A | ⬜ pending |
| 38-03-01 | 03 | 3 | SOLO-04 | unit | `uv run pytest tests/unit/test_persona_policy.py -x -q` | ✅ | ⬜ pending |
| 38-03-02 | 03 | 3 | TOOL-08 | manual | Visit /org-chart, inspect agent node | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_feature_gating.py` — update existing assertions for solopreneur tier access
- [ ] `tests/unit/test_enhanced_tools.py` — stub if not present, verify renamed tool functions exist

*Existing infrastructure covers most phase requirements — only assertion updates needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Billing page shows solopreneur checkmarks | SOLO-06 | Visual layout verification | Open /dashboard/billing as solopreneur, verify checkmarks for workflows, sales, reports, approvals, compliance, finance-forecasting, custom-workflows |
| Org chart badges render correctly | TOOL-08 | Visual badge rendering | Open /org-chart, click any agent node, verify [ACTION]/[GUIDE] badges appear |
| GatedPage components no longer show upgrade prompts | SOLO-01..03 | Route-level UI behavior | Navigate to /dashboard/workflows, /dashboard/sales, /dashboard/compliance as solopreneur — no upgrade prompt |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
