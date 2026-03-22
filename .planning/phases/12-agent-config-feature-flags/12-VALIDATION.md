---
phase: 12
slug: agent-config-feature-flags
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/unit/admin/test_config_tools.py -x` |
| **Full suite command** | `uv run pytest tests/unit/admin/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/admin/test_config_tools.py -x`
- **After every plan wave:** Run `uv run pytest tests/unit/admin/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | CONF-01 | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_diff_generation -x` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | CONF-01 | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_injection_validation -x` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | CONF-02 | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_get_config_history -x` | ❌ W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | CONF-02 | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_rollback_config -x` | ❌ W0 | ⬜ pending |
| 12-01-05 | 01 | 1 | CONF-03 | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_toggle_feature_flag -x` | ❌ W0 | ⬜ pending |
| 12-01-06 | 01 | 1 | CONF-03 | unit | `uv run pytest tests/unit/admin/test_config_service.py::test_flag_cache_hit -x` | ❌ W0 | ⬜ pending |
| 12-01-07 | 01 | 1 | CONF-04 | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_update_autonomy -x` | ❌ W0 | ⬜ pending |
| 12-01-08 | 01 | 1 | CONF-05 | unit | `uv run pytest tests/unit/admin/test_config_api.py -x` | ❌ W0 | ⬜ pending |
| 12-01-09 | 01 | 1 | SKIL-07 | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_assess_impact -x` | ❌ W0 | ⬜ pending |
| 12-01-10 | 01 | 1 | SKIL-08 | unit | `uv run pytest tests/unit/admin/test_config_tools.py::test_rollback_recommendation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/admin/test_config_tools.py` — 10 tool tests (CONF-01 through SKIL-08)
- [ ] `tests/unit/admin/test_config_service.py` — `get_flag()` Redis/DB fallback logic
- [ ] `tests/unit/admin/test_config_api.py` — REST endpoint auth + response shape tests

*Existing infrastructure in `tests/unit/admin/conftest.py` with mock_supabase_client and admin_user_dict fixtures covers all new test files — no framework changes needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Config diff visual rendering in frontend | CONF-01 | Browser-rendered UI diff component | Open `/admin/config`, edit agent instruction, verify before/after diff is visible |
| Feature flag propagation within 60s | CONF-03 | Timing-dependent runtime behavior | Toggle flag in admin UI, verify new session picks up change within 60 seconds |
| Frontend config version history timeline | CONF-02 | UI layout/interaction verification | Open agent config, check version list, click rollback, confirm restoration |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
