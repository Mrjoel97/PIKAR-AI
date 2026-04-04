---
phase: 41
slug: financial-integrations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/unit/test_stripe_sync.py tests/unit/test_shopify_service.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~20 seconds (quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 41-01-01 | 01 | 1 | FIN-01..05 | unit | `uv run pytest tests/unit/test_stripe_sync.py -x -q` | ❌ W0 | ⬜ pending |
| 41-02-01 | 02 | 1 | SHOP-01..05 | unit | `uv run pytest tests/unit/test_shopify_service.py -x -q` | ❌ W0 | ⬜ pending |
| 41-03-01 | 03 | 2 | FIN/SHOP agent tools | unit | `uv run pytest tests/unit/test_stripe_sync.py tests/unit/test_shopify_service.py -x -q` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/unit/test_stripe_sync.py` — stubs for import, categorization, webhook processing, idempotency
- [ ] `tests/unit/test_shopify_service.py` — stubs for order/product sync, inventory alerts, webhook processing

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stripe OAuth connect flow | FIN-05 | Requires real Stripe account | Connect Stripe from /dashboard/configuration, verify transactions appear |
| Shopify OAuth connect flow | SHOP-01 | Requires real Shopify store | Connect Shopify store, verify products and orders sync |
| Revenue dashboard with real data | FIN-02 | Visual rendering | Open /dashboard/finance after Stripe sync, verify real revenue numbers |
| Inventory alert notification | SHOP-04 | End-to-end flow | Set low threshold on a product, trigger inventory update, verify notification |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
