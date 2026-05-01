---
phase: 86
plan: 01
subsystem: agent-tooling-and-prompts
tags: [hotfix, executive-agent, content-director, document-generation, tdd]
requirements: [HOTFIX-04]
dependency-graph:
  requires: [DOCUMENT_GEN_TOOLS export at app/agents/tools/document_gen.py:184, VALID_TEMPLATES at app/services/document_service.py:53-59, existing prompt-tool contract gate at tests/unit/test_executive_prompt_tool_contract.py]
  provides: [Executive Agent direct access to generate_pdf_report and generate_pitch_deck, named PDF/PPTX capability in executive prompt and Content Director prompt]
  affects: [_EXECUTIVE_TOOLS list in app/agent.py, executive_instruction.txt section 23, CONTENT_DIRECTOR_INSTRUCTION block before DELEGATION STRATEGY]
tech-stack:
  added: []
  patterns: [verbatim-prose-from-research, RED-GREEN-TDD, alphabetically-sorted-imports]
key-files:
  created:
    - tests/unit/test_phase86_document_gen_wiring.py
    - .planning/phases/86-document-generation-skills-exposure/86-MANUAL-UAT.md
  modified:
    - app/agent.py
    - app/prompts/executive_instruction.txt
    - app/agents/content/agent.py
decisions:
  - Doc-gen import alphabetical placement: document_gen falls AFTER deep_research alphabetically — ruff I001 surfaced this and was auto-fixed
  - Tool spread placement: between DECISION_JOURNAL_TOOLS and ONBOARDING_NUDGE_TOOLS (groups doc-gen with other artifact-producing tools)
  - sales_proposal docstring fix DEFERRED — flagged in research Open Question Q3, requires separate phase per scope discipline
  - SC4/SC5 verification: unit (mechanical proxy via {status, widget, fileType} shape) + manual UAT (real Gemini routing) — LLM-mocked integration tests rejected as brittle
metrics:
  duration_minutes: 9
  completed_date: 2026-05-01
  task_count: 2
  test_count: 7
  files_changed: 5
---

# Phase 86 Plan 01: Document Generation Skills Exposure Summary

**HOTFIX-04 closed:** Executive Agent and Content Director can now invoke `generate_pdf_report` and `generate_pitch_deck` from natural-language prompts; both tools are named in their respective instruction prompts and all 5 PDF templates (`financial_report`, `project_proposal`, `meeting_summary`, `competitive_analysis`, `sales_proposal`) are listed.

## File Edits with Line Numbers

This is the canonical location list for the 3 source edits — a future reader can locate each insertion without re-running diff.

### 1. `app/agent.py`

**a) New import block — lines 83-84** (placed AFTER `deep_research` import block at lines 80-81, alphabetically correct):

```python
# Import document generation tools (PDF reports, PowerPoint pitch decks)
from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS
```

Note: original plan suggested placement between `decision_journal` (line 78) and `deep_research` (line 81), but ruff I001 (autofix applied) moved it to the alphabetically correct slot AFTER `deep_research`. Diff is identical in semantics.

**b) New tool spread — line 285** (placed AFTER `*DECISION_JOURNAL_TOOLS,` at line 284, BEFORE `*ONBOARDING_NUDGE_TOOLS,` at line 286, inside `_EXECUTIVE_TOOLS = _sanitize(apply_timing([...]))`):

```python
            *DOCUMENT_GEN_TOOLS,
```

### 2. `app/prompts/executive_instruction.txt`

**New numbered capability block — section 23, ~12 lines inserted after line 211** (last line of section 22 "Onboarding Nudges"), BEFORE the `## AUTO-INITIATIVE DETECTION` heading.

Verbatim copy from `86-RESEARCH.md` § Recommended Implementation / Change 2. Names both tools and all 5 `VALID_TEMPLATES`. References section 19 to disambiguate from Google Workspace tools.

### 3. `app/agents/content/agent.py`

**New `## BRANDED DOCUMENT GENERATION (PDF + PowerPoint)` block — ~9 lines inserted after line 367** (last line of `## CONTENT TYPES YOU SUPPORT` block), BEFORE the `## DELEGATION STRATEGY` heading. Now lives at line 369.

Verbatim copy from `86-RESEARCH.md` § Recommended Implementation / Change 3. Mentions `generate_pdf_report`, `generate_pitch_deck`, "PDF", and "PowerPoint" — satisfies all assertions in `test_content_director_instruction_mentions_doc_gen`.

**Untouched:** `*DOCUMENT_GEN_TOOLS,` at line 602 (was line 592 pre-edit; shifted down by 10 lines from new prose insertion). Line 602 already wires the tools — only the prose was missing.

## Test Outcome

**Phase 86 wiring suite — 7/7 GREEN:**

```
tests\unit\test_phase86_document_gen_wiring.py .......     [100%]
7 passed in 10.01s
```

| Task ID  | Test | Result |
|----------|------|--------|
| 86-01-01 | `test_executive_tools_includes_document_gen` (SC1) | GREEN |
| 86-01-02 | `test_executive_instruction_names_doc_tools` (SC2 names) | GREEN |
| 86-01-03 | `test_executive_instruction_lists_pdf_templates` (SC2 templates) | GREEN |
| 86-01-04 | `test_content_director_instruction_mentions_doc_gen` (SC3) | GREEN |
| 86-01-05 | `test_document_gen_tools_export_is_two_callables` (regression guard) | GREEN |
| 86-01-06 | `test_generate_pdf_report_returns_widget` (SC4 proxy) | GREEN |
| 86-01-07 | `test_generate_pitch_deck_returns_widget` (SC5 proxy) | GREEN |

**Existing prompt-tool contract gate:** `tests/unit/test_executive_prompt_tool_contract.py` — same 4 pre-existing failures before AND after Phase 86 edits (verified by stash/test/unstash cycle):

- `test_executive_prompt_file_matches_factory_default` — pre-existing, .txt prompt missing the `## SKILLS REGISTRY ACCESS` shared block that `EXECUTIVE_INSTRUCTION` appends in-memory
- `test_executive_prompt_references_only_accessible_tools` — pre-existing, prompt names Google Workspace tools (`create_document`, `send_email`, etc.) not in `_EXECUTIVE_TOOLS`
- `test_all_specialist_agent_prompts_reference_only_available_tools[DataReportingAgent]` — pre-existing, references unaccessible skill tools
- `test_specialist_agents_with_skill_tools_document_skill_usage[ContentCreationAgent]` — pre-existing, exposes skill tools without naming them

**Zero new failures introduced** — Phase 86 edits add new tools to `_EXECUTIVE_TOOLS` (strengthens the contract gate) and add tool names to a Content Director prompt that already wires the tools (also strengthens). Pre-existing failures explicitly noted in plan-level `<known_risks>` and STATE.md.

## Manual UAT Status

`86-MANUAL-UAT.md` scaffolded with two prompts (PDF + pitch deck). Awaiting execution against staging or local backend before `/gsd:verify-work`. Not a CI gate — closes the SC4/SC5 LLM-routing portion against real Gemini.

## Lint

`uv run ruff check app/agent.py app/agents/content/agent.py tests/unit/test_phase86_document_gen_wiring.py`:
- 1 new I001 introduced by import addition → autofixed by ruff (deep_research moved before document_gen).
- 2 pre-existing errors in content/agent.py (1 I001 in pre-existing import block, 1 RUF013 on line 544) — not caused by Phase 86, not fixed (out of scope per scope-boundary rule).

`uv run ruff format`:
- Applied to `tests/unit/test_phase86_document_gen_wiring.py` (split a long `with patch(...)` into multi-line per Pikar style).
- `app/agent.py` and `content/agent.py` already clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ruff I001 import unsorted in app/agent.py**
- **Found during:** Task 2 Step 2.6 (lint)
- **Issue:** Plan specified inserting `document_gen` import between `decision_journal` (line 78) and `deep_research` (line 81). Ruff sorts the `app.agents.tools.*` block alphabetically — `deep_research` < `document_gen`, so the correct slot is AFTER `deep_research`.
- **Fix:** `uv run ruff check app/agent.py --fix` autofixed it. Final position is alphabetically correct (lines 83-84 after `deep_research` lines 80-81).
- **Files modified:** `app/agent.py` only
- **Commit:** GREEN commit (this one)

**2. [Rule 3 - Blocking] ruff format on test file**
- **Found during:** Task 2 Step 2.6 (lint)
- **Issue:** Verbatim test code from research had a `with patch("app.services.document_service.DocumentService", return_value=mock_service):` line exceeding the project's line-length config.
- **Fix:** `uv run ruff format` split it into a multi-line call. No semantic change.
- **Files modified:** `tests/unit/test_phase86_document_gen_wiring.py`
- **Commit:** GREEN commit (this one)

### Out-of-scope items (deferred per scope discipline)

- **`sales_proposal` missing from `app/agents/tools/document_gen.py:53-65` docstring** — Researcher Open Question Q3 flagged this. The runtime list at `app/services/document_service.py:53-59` includes `sales_proposal`, so it works at runtime; only the tool-description docstring is stale. Fix would touch a 4th file outside the plan's `files_modified` list. Defer to a follow-up phase or quick docs PR.
- **4 pre-existing `test_executive_prompt_tool_contract.py` failures** — confirmed pre-existing across Phases 83-85 per STATE.md and plan known-risks. Out of scope.

## Authentication Gates

None.

## Self-Check: PASSED

Verified post-write:
- `tests/unit/test_phase86_document_gen_wiring.py` — FOUND
- `.planning/phases/86-document-generation-skills-exposure/86-MANUAL-UAT.md` — FOUND
- RED commit `547760fe` — FOUND
- GREEN commit (this) — pending creation
- `*DOCUMENT_GEN_TOOLS,` at `app/agents/content/agent.py:602` — UNCHANGED (only the prose block above was added; line shifted from 592 → 602 due to insertion)
- `app/agent.py` import order — alphabetically clean (ruff GREEN on touched-file scope)
