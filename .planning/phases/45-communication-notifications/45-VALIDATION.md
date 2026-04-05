---
phase: 45
slug: communication-notifications
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 45 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/unit/services/test_slack_notification_service.py tests/unit/services/test_teams_notification_service.py tests/unit/services/test_notification_rule_service.py -x` |
| **Full suite command** | `uv run pytest tests/ -x --timeout=30` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/services/test_slack_notification_service.py tests/unit/services/test_teams_notification_service.py tests/unit/services/test_notification_rule_service.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x --timeout=30`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 45-01-01 | 01 | 1 | NOTIF-01 | unit | `uv run pytest tests/unit/services/test_slack_notification_service.py::test_token_stored_encrypted -x` | ❌ W0 | ⬜ pending |
| 45-01-02 | 01 | 1 | NOTIF-02 | unit | `uv run pytest tests/unit/services/test_teams_notification_service.py::test_webhook_url_stored -x` | ❌ W0 | ⬜ pending |
| 45-02-01 | 02 | 1 | NOTIF-03 | unit | `uv run pytest tests/unit/services/test_notification_rule_service.py -x` | ❌ W0 | ⬜ pending |
| 45-03-01 | 03 | 2 | NOTIF-04 | unit | `uv run pytest tests/unit/services/test_slack_notification_service.py::test_interact_approval -x` | ❌ W0 | ⬜ pending |
| 45-03-02 | 03 | 2 | NOTIF-05 | unit | `uv run pytest tests/unit/services/test_slack_notification_service.py::test_daily_briefing_blocks -x` | ❌ W0 | ⬜ pending |
| 45-03-03 | 03 | 2 | NOTIF-06 | unit | `uv run pytest tests/unit/services/test_slack_notification_service.py::test_block_kit_structure -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/services/test_slack_notification_service.py` — stubs for NOTIF-01, NOTIF-04, NOTIF-05, NOTIF-06
- [ ] `tests/unit/services/test_teams_notification_service.py` — stubs for NOTIF-02, NOTIF-06
- [ ] `tests/unit/services/test_notification_rule_service.py` — stubs for NOTIF-03

*Existing infrastructure covers framework setup — only test file stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Slack OAuth flow completes | NOTIF-01 | Requires live Slack workspace | Connect Slack in Settings, verify bot token stored |
| Teams webhook URL posts messages | NOTIF-02 | Requires live Teams channel | Paste webhook URL, trigger event, verify message posted |
| Slack interactive approval button works | NOTIF-04 | Requires live Slack with signing secret | Trigger approval, click button in Slack, verify approval processed |
| Daily briefing posts at scheduled time | NOTIF-05 | Requires scheduler + live channel | Wait for scheduled briefing or trigger manually, verify post |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
