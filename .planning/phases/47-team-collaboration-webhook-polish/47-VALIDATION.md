---
phase: 47
slug: team-collaboration-webhook-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 47 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pytest.ini` / `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/unit/test_outbound_webhooks.py tests/unit/test_team_analytics.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/test_outbound_webhooks.py tests/unit/test_team_analytics.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 47-01-xx | 01 | 1 | TEAM-01–04 | unit | `uv run pytest tests/unit/test_team_analytics.py -x` | ❌ W0 | ⬜ pending |
| 47-02-xx | 02 | 1 | HOOK-01–05 | unit | `uv run pytest tests/unit/test_outbound_webhooks.py -x` | ❌ W0 | ⬜ pending |
| 47-03-xx | 03 | 2 | TEAM-01–04, HOOK-01–04 | unit | `uv run pytest tests/unit/ -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_outbound_webhooks.py` — stubs for HOOK-01 through HOOK-05
- [ ] `tests/unit/test_team_analytics.py` — stubs for TEAM-01 through TEAM-04

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Team member sees shared initiatives in UI | TEAM-01 | Requires multi-user frontend session | Create workspace, invite member, share initiative, verify member sees it |
| Zapier catch hook receives Pikar events | HOOK-03 | Requires live Zapier account | Create Zapier catch hook, configure Pikar webhook, trigger event, verify Zapier receives payload |
| Webhook delivery retry after endpoint failure | HOOK-04 | Requires simulated endpoint failure over time | Create endpoint pointing to failing URL, verify retry attempts in delivery log |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
