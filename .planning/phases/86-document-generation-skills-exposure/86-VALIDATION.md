---
phase: 86
slug: document-generation-skills-exposure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
sc4_sc5_verification: unit_plus_manual_uat
sc4_sc5_rationale: "LLM-routing (real Gemini selecting the tool from natural-language prompts) cannot be unit-tested without mocking the entire ADK runtime — poor signal/cost ratio. Unit tests cover wiring (SC1/SC2/SC3) and tool-shape contract (SC4/SC5 mechanical proxy). Manual UAT closes the LLM-routing portion against real Gemini in /dashboard/chat or ADK playground."
---

# Phase 86 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source of truth: `86-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Pytest 8.x with pytest-asyncio (already in `pyproject.toml`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py tests/unit/test_executive_prompt_tool_contract.py -x -q` |
| **Full suite command** | `uv run pytest tests/unit -x -q` |
| **Estimated runtime** | ~3–8s focused · ~30–90s full suite |

---

## Sampling Rate

- **After every task commit:** Run focused command above
- **After every plan wave:** `uv run pytest tests/unit -x -q`
- **Before `/gsd:verify-work`:** Full suite green + manual UAT log entry (one PDF prompt, one pitch-deck prompt)
- **Max feedback latency:** ~10 seconds for the focused run

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 86-01-01 | 01 | 0 | HOTFIX-04 SC1 | unit | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_executive_tools_includes_document_gen -x` | ❌ W0 | ⬜ pending |
| 86-01-02 | 01 | 0 | HOTFIX-04 SC2 (names) | unit (string) | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_executive_instruction_names_doc_tools -x` | ❌ W0 | ⬜ pending |
| 86-01-03 | 01 | 0 | HOTFIX-04 SC2 (templates) | unit (string) | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_executive_instruction_lists_pdf_templates -x` | ❌ W0 | ⬜ pending |
| 86-01-04 | 01 | 0 | HOTFIX-04 SC3 | unit (string) | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_content_director_instruction_mentions_doc_gen -x` | ❌ W0 | ⬜ pending |
| 86-01-05 | 01 | 0 | HOTFIX-04 SC2/SC3 (contract gate) | unit | `uv run pytest tests/unit/test_executive_prompt_tool_contract.py -x` | ✅ existing | ⬜ pending |
| 86-01-06 | 01 | 0 | HOTFIX-04 SC4 (tool shape) | unit | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_generate_pdf_report_returns_widget -x` | ❌ W0 | ⬜ pending |
| 86-01-07 | 01 | 0 | HOTFIX-04 SC5 (tool shape) | unit | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_generate_pitch_deck_returns_widget -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_phase86_document_gen_wiring.py` — NEW file. Covers SC1 (executive tools list), SC2 (executive instruction names + templates), SC3 (content director mentions), SC4/SC5 (tool returns `{status, widget}` shape with `fileType in {"pdf","pptx"}`). Test skeleton in research § Validation Architecture / Wave 0 Gaps.

*No new framework or fixtures needed — `pytest`, `pytest-asyncio`, file-read fixtures already standard.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real LLM routes "create a financial report PDF" → `generate_pdf_report` → downloadable PDF | HOTFIX-04 SC4 (real-LLM portion) | Cannot unit-test Gemini's tool-selection without mocking the entire ADK runtime — brittle and low signal | (1) `make local-backend` + frontend dev. (2) Open `/dashboard/chat`. (3) Prompt: "Create a financial report PDF for Q1 2026 revenue." (4) Wait for tool call. (5) **Expected:** `generate_pdf_report` invoked with `template="financial_report"`; chat returns a downloadable PDF widget; clicking the widget downloads a `.pdf` file. (6) Log result in MANUAL-UAT.md (success/failure + screenshot if available). |
| Real LLM routes "build me a pitch deck" → `generate_pitch_deck` → downloadable PPTX | HOTFIX-04 SC5 (real-LLM portion) | Same | (1) Same setup. (2) Prompt: "Build me a pitch deck for an AI scheduling startup." (3) Wait for tool call. (4) **Expected:** `generate_pitch_deck` invoked; chat returns a downloadable PPTX widget; clicking downloads a `.pptx` file. (5) Log result in MANUAL-UAT.md. |
| ADK playground sanity check (alt UAT path) | HOTFIX-04 SC4/SC5 | Same | (1) `make playground` (port 8501, select 'app' folder). (2) Run both prompts above. (3) Verify tool calls in the trace pane. (4) Log results. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`test_phase86_document_gen_wiring.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s for focused run
- [ ] `nyquist_compliant: true` set in frontmatter (flip after planner & checker confirm coverage)
- [ ] Manual UAT executed and logged before `/gsd:verify-work`
- [ ] Existing prompt-tool contract tests still pass after instruction changes (no orphaned tool refs)

**Approval:** pending
