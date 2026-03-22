---
phase: 11
slug: external-integrations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 11 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), manual browser (frontend) |
| **Quick run command** | `uv run pytest tests/unit/admin/test_integrations*.py -x -q` |
| **Full suite command** | `uv run pytest tests/unit/admin/ -v` |
| **Estimated runtime** | ~15 seconds |

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Max feedback latency:** 15 seconds

## Wave 0 Requirements

- [ ] `tests/unit/admin/test_integrations_api.py` — stubs for integration CRUD + proxy
- [ ] `tests/unit/admin/test_integration_tools.py` — stubs for agent tools

## Manual-Only Verifications

| Behavior | Requirement | Why Manual |
|----------|-------------|------------|
| Integration cards render | INTG-01 | Visual UI |
| API key masked after save | INTG-02 | Visual + security |
| Sentry issues display in chat | INTG-03 | End-to-end agent + external API |
| PostHog events in chat | INTG-04 | End-to-end agent + external API |
| GitHub PRs in chat | INTG-05 | End-to-end agent + external API |
| Response caching works | INTG-06 | Timing behavior |

**Approval:** pending
