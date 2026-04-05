---
phase: 43
slug: ad-platform-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/unit/services/test_ad_platform.py -x -q` |
| **Full suite command** | `uv run pytest tests/unit/services/test_ad_platform.py tests/unit/tools/test_ad_tools.py -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/services/test_ad_platform.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/unit/services/test_ad_platform.py tests/unit/tools/test_ad_tools.py -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 43-01-01 | 01 | 1 | ADS-01 | unit | `uv run pytest tests/unit/services/test_ad_platform.py -k "google_ads_provider"` | ❌ W0 | ⬜ pending |
| 43-01-02 | 01 | 1 | ADS-02 | unit | `uv run pytest tests/unit/services/test_ad_platform.py -k "meta_ads_provider"` | ❌ W0 | ⬜ pending |
| 43-01-03 | 01 | 1 | ADS-06 | unit | `uv run pytest tests/unit/services/test_ad_platform.py -k "budget_cap"` | ❌ W0 | ⬜ pending |
| 43-02-01 | 02 | 1 | ADS-03 | unit | `uv run pytest tests/unit/services/test_ad_platform.py -k "approval_gate"` | ❌ W0 | ⬜ pending |
| 43-02-02 | 02 | 1 | ADS-04 | unit | `uv run pytest tests/unit/services/test_ad_platform.py -k "performance_sync"` | ❌ W0 | ⬜ pending |
| 43-02-03 | 02 | 1 | ADS-05 | unit | `uv run pytest tests/unit/services/test_ad_platform.py -k "pacing_alert"` | ❌ W0 | ⬜ pending |
| 43-03-01 | 03 | 2 | ADS-03 | unit | `uv run pytest tests/unit/tools/test_ad_tools.py -k "agent_tools"` | ❌ W0 | ⬜ pending |
| 43-03-02 | 03 | 2 | ADS-07 | unit | `uv run pytest tests/unit/tools/test_ad_tools.py -k "ad_copy_generation"` | ❌ W0 | ⬜ pending |
| 43-03-03 | 03 | 2 | ADS-01, ADS-02 | manual | Frontend verification | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/services/test_ad_platform.py` — stubs for ADS-01 through ADS-06
- [ ] `tests/unit/tools/test_ad_tools.py` — stubs for ADS-03, ADS-07
- [ ] Fixtures: mock httpx transport for Google Ads + Meta Ads API responses

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OAuth popup flow in browser | ADS-01, ADS-02 | Requires browser interaction with Google/Meta consent screens | Open configuration page → Click "Connect" on Google Ads card → Verify popup opens → Complete OAuth → Verify connected status |
| Budget cap input during connect | ADS-06 | Frontend form interaction | Connect Google Ads → Verify budget cap input required → Set cap → Verify stored |
| Approval card rendering in chat | ADS-03 | Frontend SSE rendering | Ask agent to activate a campaign → Verify confirmation card appears with budget details + approve/reject buttons |

*All backend logic has automated verification; manual items are frontend UX flows.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
