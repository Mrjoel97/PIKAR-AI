---
phase: 40
slug: data-i-o-document-generation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), vitest (frontend) |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `uv run pytest tests/unit/test_data_import.py tests/unit/test_data_export.py tests/unit/test_document_generator.py -x -q` |
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
| 40-01-01 | 01 | 1 | DATA-01..05 | unit | `uv run pytest tests/unit/test_data_import.py tests/unit/test_data_export.py -x -q` | ❌ W0 | ⬜ pending |
| 40-02-01 | 02 | 1 | DOC-01..04 | unit | `uv run pytest tests/unit/test_document_generator.py -x -q` | ❌ W0 | ⬜ pending |
| 40-03-01 | 03 | 2 | DATA-06, DOC-05 | unit | `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30` | ✅ | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/unit/test_data_import.py` — stubs for CSV parsing, mapping, validation
- [ ] `tests/unit/test_data_export.py` — stubs for CSV generation and signed URL return
- [ ] `tests/unit/test_document_generator.py` — stubs for PDF and PPTX generation

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CSV column mapping UI | DATA-01 | Visual component rendering | Upload a CSV, verify column mapping suggestions appear |
| PDF branded output | DOC-02 | Visual rendering quality | Generate a PDF report, verify logo and brand colors appear correctly |
| PPTX slide quality | DOC-03 | Visual rendering quality | Generate a pitch deck, open in PowerPoint/Google Slides, verify formatting |
| Document widget in chat | DOC-05 | Widget rendering | Ask agent to generate a report, verify download widget appears in chat |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
