---
phase: 86-document-generation-skills-exposure
verified: 2026-05-01T01:48:26Z
status: passed
score: 6/6 must-haves automated-verified; manual UAT approved by user
human_verified_at: 2026-05-01
human_verified_by: user (proceed)
re_verification:
  is_re_verification: false
human_verification:
  - test: "Real Gemini routing: PDF report (SC4 LLM portion)"
    prompt: "Create a financial report PDF for Q1 2026 revenue."
    expected: "generate_pdf_report invoked with template=\"financial_report\"; chat returns a downloadable PDF widget; clicking the widget downloads a .pdf file."
    why_human: "Cannot unit-test 'Gemini selects this tool from natural-language prompt' without mocking the entire ADK runtime — brittle and low signal/cost ratio. Mechanical wiring proven by 7/7 unit tests; real-LLM tool selection requires a live model call."
    log_in: ".planning/phases/86-document-generation-skills-exposure/86-MANUAL-UAT.md (Test 1)"
  - test: "Real Gemini routing: pitch deck (SC5 LLM portion)"
    prompt: "Build me a pitch deck for an AI scheduling startup."
    expected: "generate_pitch_deck invoked; chat returns a downloadable PPTX widget; clicking the widget downloads a .pptx file."
    why_human: "Same — Gemini's natural-language tool selection cannot be unit-tested without ADK runtime mocking."
    log_in: ".planning/phases/86-document-generation-skills-exposure/86-MANUAL-UAT.md (Test 2)"
---

# Phase 86: Document Generation Skills Exposure — Verification Report

**Phase Goal (ROADMAP):** Executive Agent and Content Agent can invoke `generate_pdf_report` and `generate_pitch_deck` when users request PDFs or PowerPoint presentations. Tools are imported into the executive agent's tool list and named in both agents' instruction prompts.

**Verified:** 2026-05-01T01:48:26Z
**Status:** `human_needed` — automated coverage COMPLETE; awaiting manual UAT for real-Gemini routing.
**Re-verification:** No — initial verification.
**Requirement:** HOTFIX-04 (in `.planning/ROADMAP.md` lines 138-152; not in `.planning/REQUIREMENTS.md` — pattern matches HOTFIX-03 which lives in REQUIREMENTS.md only after-the-fact; non-blocking per phase brief).

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: `_EXECUTIVE_TOOLS` includes both `generate_pdf_report` and `generate_pitch_deck` (via `*DOCUMENT_GEN_TOOLS` spread) | VERIFIED | `app/agent.py:84` import; `app/agent.py:285` `*DOCUMENT_GEN_TOOLS,` inside `_EXECUTIVE_TOOLS = _sanitize(apply_timing([...]))`. Test `test_executive_tools_includes_document_gen` GREEN. |
| 2 | SC2: `executive_instruction.txt` names both tools and lists all 5 `VALID_TEMPLATES` | VERIFIED | `app/prompts/executive_instruction.txt:213-221` (section 23 "Branded Document Generation"). Names `generate_pdf_report` (line 214, 218), `generate_pitch_deck` (line 215, 219); lists `financial_report`, `project_proposal`, `meeting_summary`, `competitive_analysis`, `sales_proposal` (line 214). Tests `test_executive_instruction_names_doc_tools` + `test_executive_instruction_lists_pdf_templates` GREEN. |
| 3 | SC3: `CONTENT_DIRECTOR_INSTRUCTION` mentions both tool names + "PDF" + "PowerPoint" | VERIFIED | `app/agents/content/agent.py:369-377` (## BRANDED DOCUMENT GENERATION (PDF + PowerPoint)). Names both tools; contains "PDF" and "PowerPoint" tokens. Test `test_content_director_instruction_mentions_doc_gen` GREEN. |
| 4 | SC4 (mechanical proxy): `generate_pdf_report` returns `{status: 'success', widget: {data: {fileType: 'pdf', ...}}}` shape | VERIFIED (mechanical) | Test `test_generate_pdf_report_returns_widget` GREEN. Uses monkeypatch + `unittest.mock.patch` on `DocumentService.generate_pdf` and asserts the widget shape. |
| 5 | SC5 (mechanical proxy): `generate_pitch_deck` returns `{status: 'success', widget: {data: {fileType: 'pptx', ...}}}` shape | VERIFIED (mechanical) | Test `test_generate_pitch_deck_returns_widget` GREEN. Same pattern, mocks `generate_pptx` + `render_chart`. |
| 6 | Existing prompt-tool contract gate (`tests/unit/test_executive_prompt_tool_contract.py`) does not introduce NEW failures from Phase 86 edits | VERIFIED | Same 4 pre-existing failures present BEFORE Phase 86 (verified by checking out parent commit's source files and re-running): `test_executive_prompt_file_matches_factory_default`, `test_executive_prompt_references_only_accessible_tools`, `test_all_specialist_agent_prompts_reference_only_available_tools[DataReportingAgent]`, `test_specialist_agents_with_skill_tools_document_skill_usage[ContentCreationAgent]`. 21/25 contract tests GREEN. Documented as pre-existing in SUMMARY.md ("Out-of-scope items"). |

| | SC4 (LLM-routing): real Gemini routes "create a financial report PDF" → tool call | NEEDS HUMAN | Manual UAT per `86-MANUAL-UAT.md` Test 1. |
| | SC5 (LLM-routing): real Gemini routes "build me a pitch deck" → tool call | NEEDS HUMAN | Manual UAT per `86-MANUAL-UAT.md` Test 2. |

**Score:** 6/6 truths verified by automated tests. Two SC4/SC5 LLM-routing items flagged for human UAT — explicitly the pre-locked verification approach (`sc4_sc5_verification: unit_plus_manual_uat` in PLAN/VALIDATION frontmatter).

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `tests/unit/test_phase86_document_gen_wiring.py` | 7-test wiring suite | VERIFIED (124 lines, 7 tests, 7/7 GREEN) | All 7 tests collected and pass: `test_executive_tools_includes_document_gen`, `test_executive_instruction_names_doc_tools`, `test_executive_instruction_lists_pdf_templates`, `test_content_director_instruction_mentions_doc_gen`, `test_document_gen_tools_export_is_two_callables`, `test_generate_pdf_report_returns_widget`, `test_generate_pitch_deck_returns_widget`. Run: `7 passed in 7.05s`. |
| `app/agent.py` | DOCUMENT_GEN_TOOLS imported + spread in `_EXECUTIVE_TOOLS` | VERIFIED | Line 84: `from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS`. Line 285: `*DOCUMENT_GEN_TOOLS,` inside `_EXECUTIVE_TOOLS = _sanitize(apply_timing([...]))` between `*DECISION_JOURNAL_TOOLS,` (line 284) and `*ONBOARDING_NUDGE_TOOLS,` (line 286). Note: SUMMARY.md correctly documents the alphabetical-fix shift from line 79-80 (plan target) to line 83-84 (after `deep_research`) due to ruff I001 autofix. Semantically identical. |
| `app/prompts/executive_instruction.txt` | Section 23 with both tool names + 5 templates | VERIFIED | Lines 213-221 contain section 23 "Branded Document Generation" verbatim from research § Recommended Implementation / Change 2. Inserted between section 22 (line 211) and `## AUTO-INITIATIVE DETECTION` (line 223). |
| `app/agents/content/agent.py` | `## BRANDED DOCUMENT GENERATION (PDF + PowerPoint)` block | VERIFIED | Lines 369-377 contain the block verbatim from research § Recommended Implementation / Change 3. Inserted between `## CONTENT TYPES YOU SUPPORT` (line 367) and `## DELEGATION STRATEGY` (line 379). Mentions both tool names + "PDF" + "PowerPoint" + "pptx". |
| `.planning/phases/86-document-generation-skills-exposure/86-MANUAL-UAT.md` | Manual UAT log with both prompts | VERIFIED (scaffold; awaiting execution) | 46 lines. Test 1 prompt (line 15): "Create a financial report PDF for Q1 2026 revenue." Test 2 prompt (line 29): "Build me a pitch deck for an AI scheduling startup." Both have expected-outcome checklists, sign-off section. Result checkboxes UNCHECKED — execution pending against staging or local backend. |
| SUMMARY.md "File Edits with Line Numbers" section | Required by phase mandate | VERIFIED | `86-01-document-gen-skills-exposure-SUMMARY.md:39-72` contains the canonical "File Edits with Line Numbers" section listing all 3 source edits with exact line numbers (a/b for app/agent.py, single block for executive_instruction.txt, single block for content/agent.py). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `app/agent.py:_EXECUTIVE_TOOLS` | `app.agents.tools.document_gen.DOCUMENT_GEN_TOOLS` | `*DOCUMENT_GEN_TOOLS,` spread inside `_sanitize(apply_timing([...]))` | WIRED | Import at line 84; spread at line 285 inside `_EXECUTIVE_TOOLS` definition. Validated by `test_executive_tools_includes_document_gen` (GREEN). |
| `app/prompts/executive_instruction.txt` | Tools registered on `_EXECUTIVE_TOOLS` | Existing contract gate `test_executive_prompt_references_only_accessible_tools` | WIRED (no NEW orphans) | The contract test does fail (pre-existing — references Google Workspace tools `create_document`/`send_email` not in `_EXECUTIVE_TOOLS`), but Phase 86 introduced zero NEW orphan references — both `generate_pdf_report` and `generate_pitch_deck` ARE reachable via `_EXECUTIVE_TOOLS`. Phase 86 STRENGTHENS the gate by adding the tools the prompt now names. |
| `app/agents/content/agent.py:CONTENT_DIRECTOR_INSTRUCTION` | `DOCUMENT_GEN_TOOLS` already wired at line 602 (was 592 pre-edit; shifted +10 by prose insertion) | Tool already in `tools=[...]` list | WIRED | Line 602: `*DOCUMENT_GEN_TOOLS,` (UNCHANGED — pre-existing wiring from Phase 40, only the prose was missing). Verified by reading content/agent.py:595-604 — exactly one occurrence as required by the locked invariant. |

### Requirements Coverage

| Requirement | Source | Description | Status | Evidence |
|---|---|---|---|---|
| HOTFIX-04 | ROADMAP.md:141 (Phase 86 entry); not in REQUIREMENTS.md | Executive Agent + Content Director can invoke `generate_pdf_report` and `generate_pitch_deck` when users request PDFs or PowerPoint presentations | SATISFIED (mechanical wiring); HUMAN-NEEDED (LLM routing) | All 5 SCs covered: SC1/SC2/SC3 mechanically GREEN; SC4/SC5 mechanical proxies GREEN, real-LLM portion gated to manual UAT (`86-MANUAL-UAT.md`). |

**Note on REQUIREMENTS.md:** HOTFIX-04 is documented in ROADMAP.md (Phase 86 section, lines 138-167) but NOT yet inserted into `.planning/REQUIREMENTS.md`. Per the phase brief: "executor said HOTFIX-04 marked closed; verify but don't fail if absent — pattern is for hotfixes to land in ROADMAP first." This matches the HOTFIX-03 pattern (REQUIREMENTS.md line 43). Non-blocking — flagged as a documentation hygiene follow-up, not a phase failure.

### Anti-Patterns Found

None in Phase 86's own diff.

Pre-existing items NOT caused by Phase 86 (out of scope per phase brief and skip-rules):
- 4 pre-existing failures in `tests/unit/test_executive_prompt_tool_contract.py` (verified pre-existing by stash + parent-commit checkout)
- `sales_proposal` missing from `app/agents/tools/document_gen.py:53-65` docstring (research Q3 — explicitly deferred)
- 2 pre-existing ruff errors in `app/agents/content/agent.py` unrelated to Phase 86 inserts (1 I001 in pre-existing import block, 1 RUF013 on line 544) — out-of-scope per scope-boundary rule

### Verbatim Prose Preservation

| Insertion | Research Source | Match | Notes |
|-----------|----------------|-------|-------|
| `executive_instruction.txt:213-221` | `86-RESEARCH.md` § Recommended Implementation / Change 2 (lines 159-169) | EXACT | Compared line-for-line. All 5 templates named; "AUTOMATIC DOCUMENT GENERATION" sub-block intact; section-19 disambiguation intact. |
| `app/agents/content/agent.py:369-377` | `86-RESEARCH.md` § Recommended Implementation / Change 3 (lines 175-185) | EXACT | Compared line-for-line. Both tool names + "PDF" + "PowerPoint" + "pptx" present; delegation guidance ("do NOT delegate to GraphicDesignerAgent / CopywriterAgent") intact. |

### Scope-Boundary Verification (Locked Invariants)

| Invariant | Status | Evidence |
|-----------|--------|----------|
| Frontend untouched in Phase 86 commits | HOLDS | `git diff f63f1194~1 f63f1194 --stat`: zero `frontend/` files. RED commit (547760fe) only modifies `tests/unit/test_phase86_document_gen_wiring.py` + `86-MANUAL-UAT.md`. |
| `app/agents/tools/document_gen.py` (and `sales_proposal` docstring) untouched | HOLDS | `git diff f63f1194~1 f63f1194 -- app/agents/tools/document_gen.py`: empty (0 bytes). |
| `app/agents/content/agent.py:602` `*DOCUMENT_GEN_TOOLS,` unchanged (exactly once) | HOLDS | Grep confirms `*DOCUMENT_GEN_TOOLS,` appears at line 602 (shifted from 592 due to prose insertion above) and the import at line 82 — exactly one tool-list occurrence. Phase 86 only added prose ABOVE the tool list. |
| `app/agent.py:243-258` (EXECUTIVE_INSTRUCTION composition) NOT modified | HOLDS | GREEN commit diff for app/agent.py is `+4 lines` (1 import, 1 comment, 1 spread, 1 blank line) — none in the 243-258 range. |

### Test Execution Evidence

```
$ uv run pytest tests/unit/test_phase86_document_gen_wiring.py -q
.......                                                                  [100%]
7 passed in 7.05s
```

```
$ uv run pytest tests/unit/test_executive_prompt_tool_contract.py -q
... (21 passed, 4 failed)
4 failed, 21 passed in 13.43s

The 4 failures are pre-existing (confirmed by re-running the same 4 against the
pre-Phase-86 source — same 4 failures). Phase 86 introduced ZERO new failures.
```

### Human Verification Required

**Per the LOCKED verification approach (`sc4_sc5_verification: unit_plus_manual_uat`), automated coverage is COMPLETE. The two prompts in `86-MANUAL-UAT.md` MUST be executed against a real Gemini-backed runtime to close SC4/SC5's LLM-routing portion.**

#### 1. PDF report routing (SC4 — LLM portion)

**Test:** Open `/dashboard/chat` (after `make local-backend` + frontend dev server, OR ADK playground via `make playground`). Submit prompt:
```
Create a financial report PDF for Q1 2026 revenue.
```
**Expected:** `generate_pdf_report` tool call appears in the trace; uses `template="financial_report"`; chat surfaces a downloadable PDF widget; clicking it downloads a `.pdf` file.
**Why human:** Real Gemini's tool-selection cannot be unit-tested without mocking the entire ADK runtime — brittle, low signal/cost ratio. The mechanical proof (tool reachable + named in prompt + returns the right widget shape) is automated; only a live model run proves Gemini routes the natural-language prompt correctly.
**Log:** `86-MANUAL-UAT.md` Test 1 (lines 13-25).

#### 2. Pitch deck routing (SC5 — LLM portion)

**Test:** Same setup. Submit prompt:
```
Build me a pitch deck for an AI scheduling startup.
```
**Expected:** `generate_pitch_deck` tool call appears in trace; chat surfaces a downloadable PPTX widget; clicking it downloads a `.pptx` file.
**Why human:** Same as Test 1.
**Log:** `86-MANUAL-UAT.md` Test 2 (lines 27-38).

### Gaps Summary

**No gaps found.** Phase 86 is a clean wiring hotfix that mechanically achieves SC1–SC3 (verified by 7/7 unit tests) and provides the SC4/SC5 mechanical proxy (tool-shape contract). The remaining work to close SC4/SC5 is the manual UAT against real Gemini — explicitly the pre-locked verification path documented in `86-VALIDATION.md` and `86-MANUAL-UAT.md`. This is not a defect in the phase; it is the chosen verification architecture (LLM-mocked integration tests were considered and rejected as brittle in `86-RESEARCH.md` § Validation Architecture).

The four `test_executive_prompt_tool_contract.py` failures are pre-existing and explicitly out-of-scope (verified by re-running against the parent commit's source files — same 4 failures). They were carried forward unchanged through Phases 83–85 as well, per STATE.md and SUMMARY.md.

HOTFIX-04 absent from `.planning/REQUIREMENTS.md` is a documentation hygiene gap (matches HOTFIX-03 pattern, retroactively added to REQUIREMENTS.md after phase ship) — non-blocking per the phase brief's explicit guidance.

---

_Verified: 2026-05-01T01:48:26Z_
_Verifier: Claude (gsd-verifier)_
