# Phase 86: Document Generation Skills Exposure - Research

**Researched:** 2026-04-30
**Domain:** ADK agent tool registration + instruction prompt wiring
**Confidence:** HIGH

## Phase Summary

The Executive Agent and Content Director are missing `generate_pdf_report` / `generate_pitch_deck` from their visible tool surface. The tool functions, the `DocumentService`, and `DOCUMENT_GEN_TOOLS` export already exist (Phase 40, shipped 2026-04-04) and are wired into 10 specialist agents — but NOT into the Executive's flat tool list, and NOT named in the executive prompt. Phase 86 is a 3-touchpoint wiring hotfix: import + spread `*DOCUMENT_GEN_TOOLS` into `_EXECUTIVE_TOOLS`, add a numbered capability block to `executive_instruction.txt`, and add a one-paragraph PDF/PPTX capability mention to `CONTENT_DIRECTOR_INSTRUCTION` (Content Director already has the tools wired at line 592 — it's purely a prompt-naming gap).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HOTFIX-04 | Executive Agent + Content Director can invoke `generate_pdf_report` and `generate_pitch_deck` when users request PDFs or PowerPoint presentations | DOCUMENT_GEN_TOOLS already exists (`app/agents/tools/document_gen.py:184`); 10 specialist agents already spread it; Executive does NOT (`app/agent.py:260-285`); Content Director DOES wire the tools (line 592) but does not name them in `CONTENT_DIRECTOR_INSTRUCTION`; executive_instruction.txt does not name them either |
</phase_requirements>

## Current Implementation

### `DOCUMENT_GEN_TOOLS` export — EXISTS

**Source:** `app/agents/tools/document_gen.py:184`
```python
DOCUMENT_GEN_TOOLS = [generate_pdf_report, generate_pitch_deck]
```

It's a plain Python list of two async coroutine functions. The `*DOCUMENT_GEN_TOOLS` spread pattern in SC1 is the canonical convention used by all 10 specialist agents (see "Spread pattern reference" below).

### Tool function signatures

**`generate_pdf_report`** (`app/agents/tools/document_gen.py:41-107`)
```python
async def generate_pdf_report(
    template: str,
    data: dict[str, Any],
    title: str | None = None,
) -> dict[str, Any]:
```
Returns `{"status": "success", "widget": <document widget>}` or `{"status": "error", "message": ...}`.

The widget shape (from `app/services/document_service.py:_build_widget`, returned to chat UI) carries `data.fileType="pdf"`, `data.sizeBytes`, signed download URL, and is rendered by frontend as a download card (see `tests/unit/services/test_document_service.py:250-251` for the widget contract).

**`generate_pitch_deck`** (`app/agents/tools/document_gen.py:114-177`)
```python
async def generate_pitch_deck(
    content: list[dict[str, Any]],
    title: str | None = None,
) -> dict[str, Any]:
```
Each slide dict: `{"title": str, "content": list[str], "chart_data"?: {type, labels, values, title}}`. Returns the same `{status, widget}` shape with `fileType="pptx"`.

Both tools resolve `user_id` and `session_id` from `request_context` (no need to pass them through the LLM).

### `VALID_TEMPLATES` — single source of truth (SOT mismatch warning)

**Source:** `app/services/document_service.py:53-59`
```python
VALID_TEMPLATES = [
    "financial_report",
    "project_proposal",
    "meeting_summary",
    "competitive_analysis",
    "sales_proposal",  # NOTE: present in service but NOT documented in tool docstring
]
```

The tool's docstring (`document_gen.py:53-65`) only describes 4 templates and omits `sales_proposal`. The instruction prose proposed below uses all 5 (matching `VALID_TEMPLATES`, the runtime check at `document_gen.py:83`).

### `_EXECUTIVE_TOOLS` — currently MISSING the doc-gen spread

**Source:** `app/agent.py:260-285`
```python
_EXECUTIVE_TOOLS = _sanitize(
    apply_timing(
        [
            search_business_knowledge,
            get_braindump_document,
            update_initiative_status,
            create_task,
            audit_user_setup_tool,
            *KNOWLEDGE_INJECTION_TOOLS,
            *NOTIFICATION_TOOLS,
            *APP_BUILDER_TOOLS,
            *WORKFLOW_TOOLS,
            *UI_WIDGET_TOOLS,
            *EXEC_SKILL_TOOLS,
            *CONFIGURATION_TOOLS,
            *CONTEXT_MEMORY_TOOLS,
            *DEEP_RESEARCH_TOOLS,
            *BRIEFING_TOOLS,
            *MAGIC_LINK_TOOLS,
            *SYSTEM_HEALTH_TOOLS,
            *CROSS_AGENT_SYNTHESIS_TOOLS,
            *DECISION_JOURNAL_TOOLS,
            *ONBOARDING_NUDGE_TOOLS,
        ]
    )
)
```

No `*DOCUMENT_GEN_TOOLS` and no import. Imports start at lines 60-105 (alphabetical-ish by module).

### `executive_instruction.txt` — NO mention of either tool

**Source:** `app/prompts/executive_instruction.txt` (382 lines)

Current structure: numbered `## CAPABILITIES` block 1-22, each numbered item is either a 1-liner (`'send_notification'`) or a bulleted list of tool names with backticks. Tool naming convention: backtick-wrapped, no parens — e.g. `` `create_image` ``, `` `create_payment_link` ``, `` `synthesize_business_health` ``. Section 17 (Media Creation) and section 19 (Google Workspace / Document Creation) are the closest stylistic matches.

Section 19 currently covers Google Docs/Sheets/Forms but does NOT cover branded PDF/PPTX generation. Neither `generate_pdf_report` nor `generate_pitch_deck` appears anywhere in the file.

**Critical guard rail:** `tests/unit/test_executive_prompt_tool_contract.py::test_executive_prompt_references_only_accessible_tools` enforces that any tool name mentioned in the executive prompt must be reachable via `executive_agent.tools` OR via any sub-agent's tools recursively. Once `*DOCUMENT_GEN_TOOLS` is added to `_EXECUTIVE_TOOLS`, naming both tools in the prompt is safe.

### `CONTENT_DIRECTOR_INSTRUCTION` — tools wired, name NOT in prose

**Source:** `app/agents/content/agent.py:308-450` (the prose) and lines 569-594 (the tool list).

Tool list (line 592) DOES contain `*DOCUMENT_GEN_TOOLS` — wired in Phase 40. So the Content Director can ALREADY call both tools at runtime, but the prompt never tells it they exist. The prose covers video, graphics, and copywriting sub-agent delegation, plus the creative pipeline. There is no PDF/PPTX section.

The `## CONTENT TYPES YOU SUPPORT` block at lines 362-367 lists Standard Video Ads, UGC Ads, Static Visuals, Written Content, Full Campaign Bundles — adding "Branded Documents" is the natural insertion point.

**Critical guard rail:** `test_all_specialist_agent_prompts_reference_only_available_tools` (parametrized over content_agent + 10 others) enforces the same constraint: any tool name in `agent.instruction` must be in that agent's recursive tool surface. Since DOCUMENT_GEN_TOOLS is at line 592, naming both tools in CONTENT_DIRECTOR_INSTRUCTION passes the test.

### Spread pattern reference (canonical convention)

All 10 specialist agents follow the same shape:
- `from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS` at top of file (after `# Import...` block ordering)
- `*DOCUMENT_GEN_TOOLS,` inside the agent's `tools=[...]` list

Examples:
- `app/agents/financial/agent.py:45,238`
- `app/agents/sales/agent.py:35,211`
- `app/agents/operations/agent.py:46,251`
- `app/agents/content/agent.py:82,592`

The Executive's import block (`app/agent.py:60-105`) is already sorted by module name with explanatory comments. `document_gen` would slot alphabetically between `decision_journal` (line 78) and `deep_research` (line 81).

## Recommended Implementation

### Change 1: `app/agent.py` — import + spread

**Insert at line 79** (right after the `decision_journal` import, alphabetical fit):
```python
# Import document generation tools (PDF reports, PowerPoint pitch decks)
from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS
```

**Insert in `_EXECUTIVE_TOOLS` list at line 281** (right before `*DECISION_JOURNAL_TOOLS,` to keep alphabetical-ish — or at the bottom of the spread block if strict alphabetical isn't tracked):
```python
            *DOCUMENT_GEN_TOOLS,
```

Recommended exact insertion point: place it between `*DEEP_RESEARCH_TOOLS,` (line 276) and `*BRIEFING_TOOLS,` (line 277) so doc-gen sits with the other "create artifact" tools. The list is not strictly alphabetical (notification → app_builder → workflow), so semantic grouping is acceptable — the planner should pick one and document it. Concrete recommendation: insert between line 281 (`*DECISION_JOURNAL_TOOLS,`) and line 282 (`*ONBOARDING_NUDGE_TOOLS,`), so the diff is minimal and the new line lands next to the other "produce-an-artifact" tools.

### Change 2: `app/prompts/executive_instruction.txt` — add capability block 23

**Append after current section 22 "Onboarding Nudges" (line 211), before `## AUTO-INITIATIVE DETECTION` (line 213):**

```text
23. **Branded Document Generation** (PDF reports, PowerPoint pitch decks): Create polished, brand-themed documents that the user can download from the chat:
   - `generate_pdf_report`: Render a multi-page branded PDF from one of five templates: `financial_report`, `project_proposal`, `meeting_summary`, `competitive_analysis`, `sales_proposal`. Pass the `template` name and a `data` dict matching that template's schema (revenue/expenses/period for financial; objectives/timeline/budget for proposal; attendees/decisions/action_items for meeting; competitors/market_position for competitive_analysis; sales pitch fields for sales_proposal). Optional `title` overrides the default heading.
   - `generate_pitch_deck`: Render a multi-slide branded PowerPoint (.pptx) presentation. Pass `content` as a list of slide dicts (`title` required; `content` bullets optional; `chart_data` with type/labels/values optional for embedded charts). Optional `title` defaults to "Pitch Deck".

   **AUTOMATIC DOCUMENT GENERATION**: When users ask for:
   - "Create a PDF report / financial report PDF / project proposal / meeting summary PDF / competitive analysis / sales proposal" → call `generate_pdf_report` with the matching template
   - "Build me a pitch deck / create a PowerPoint / make a slide deck / investor deck" → call `generate_pitch_deck`
   - Both tools return a download widget. Reply based on the result only: on `status: success` say "Here's your <PDF | pitch deck> — you can download it from the card below and find it in Knowledge Vault → Documents." On `status: error`, relay the `message` field; never claim success on failure.
   - Do NOT call these tools for Google Docs / Sheets / Forms — those go to section 19. These are FOR downloadable, brand-styled standalone artifacts.
```

### Change 3: `app/agents/content/agent.py` — add capability paragraph to CONTENT_DIRECTOR_INSTRUCTION

**Insert into `CONTENT_DIRECTOR_INSTRUCTION` (line 308-450) immediately after the `## CONTENT TYPES YOU SUPPORT` block (after line 367 "Full Campaign Bundles"), as a new section before `## DELEGATION STRATEGY` at line 369:**

```text
## BRANDED DOCUMENT GENERATION (PDF + PowerPoint)
You can produce branded, downloadable documents directly — these complement (not replace) the sub-agent creative work:
- `generate_pdf_report`: Branded PDF for `financial_report`, `project_proposal`, `meeting_summary`, `competitive_analysis`, or `sales_proposal`. Pass the template name and a structured `data` dict matching that template's schema. Use this when the user asks for a polished PDF report, a downloadable proposal document, a meeting recap PDF, or a sales proposal artifact.
- `generate_pitch_deck`: Branded PowerPoint (.pptx). Pass `content` as a list of slide dicts (each with `title`, optional `content` bullets, optional `chart_data`). Use this for investor decks, internal pitch decks, sales decks, or any "build me a slide deck" request.

When the user asks to "make a pitch deck", "create an investor deck", or "build a slide presentation", call `generate_pitch_deck` directly — do NOT delegate to GraphicDesignerAgent (those tools cover individual visuals, not multi-slide PPTX).
When the user asks for a "PDF report" or "downloadable document", call `generate_pdf_report` directly — do NOT delegate to CopywriterAgent (those tools produce blog/social copy, not formatted PDFs).

Both tools return `{status, widget}`. On success, tell the user the document is ready and downloadable from the card below. On error, relay the `message` field verbatim — never claim success on failure.
```

This is a self-contained block placed where the existing prose distinguishes "what you do directly" from "what you delegate". It satisfies SC3 by mentioning PDF and PowerPoint with both tool names.

## Files Involved

### Must modify (3 files)
| File | Change | Lines |
|------|--------|-------|
| `app/agent.py` | Add import + spread `*DOCUMENT_GEN_TOOLS` into `_EXECUTIVE_TOOLS` | Insert ~line 79 (import), insert in tool list ~line 282 |
| `app/prompts/executive_instruction.txt` | Append section 23 (Branded Document Generation) | After line 211 |
| `app/agents/content/agent.py` | Insert "## BRANDED DOCUMENT GENERATION" block in `CONTENT_DIRECTOR_INSTRUCTION` | After line 367 |

### Must read (no changes — context only)
| File | Why |
|------|-----|
| `app/agents/tools/document_gen.py` | Tool function signatures, `DOCUMENT_GEN_TOOLS` export |
| `app/services/document_service.py` | `VALID_TEMPLATES` (source of truth for the 5 template names) |
| `tests/unit/test_executive_prompt_tool_contract.py` | Contract tests that gate prompt-tool consistency — both `test_executive_prompt_references_only_accessible_tools` and `test_all_specialist_agent_prompts_reference_only_available_tools` must continue to pass after the changes |
| `app/services/user_agent_factory.py` | `DEFAULT_EXECUTIVE_INSTRUCTION` is loaded from `executive_instruction.txt` at module import — `test_executive_prompt_file_matches_factory_default` verifies parity |

### Tests
| File | Action |
|------|--------|
| `tests/unit/test_executive_prompt_tool_contract.py` | Existing tests must continue to pass — they implicitly validate SC1+SC2+SC3 once changes land |
| `tests/unit/test_phase86_document_gen_wiring.py` | NEW — explicit assertions for SC1, SC2, SC3 (proposed below) |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio (already in `pyproject.toml`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`); no separate `pytest.ini` |
| Quick run command | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py -x -q` |
| Full suite command | `uv run pytest tests/unit -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HOTFIX-04 SC1 | `_EXECUTIVE_TOOLS` includes `*DOCUMENT_GEN_TOOLS` (both functions reachable) | unit | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_executive_tools_includes_document_gen -x` | Wave 0 |
| HOTFIX-04 SC2 | `executive_instruction.txt` names both tools and lists template options | unit (string-match) | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_executive_instruction_names_doc_tools -x` | Wave 0 |
| HOTFIX-04 SC2 | `executive_instruction.txt` mentions all 5 valid templates | unit (string-match) | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_executive_instruction_lists_pdf_templates -x` | Wave 0 |
| HOTFIX-04 SC3 | `CONTENT_DIRECTOR_INSTRUCTION` mentions PDF, PowerPoint, and both tool names | unit (string-match) | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_content_director_instruction_mentions_doc_gen -x` | Wave 0 |
| HOTFIX-04 SC2/SC3 | Existing prompt-tool contract tests still pass (no orphaned tool refs) | unit | `uv run pytest tests/unit/test_executive_prompt_tool_contract.py -x` | yes |
| HOTFIX-04 SC4 | "create a financial report PDF" → `generate_pdf_report` called → widget returned | LLM-mocked integration | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_generate_pdf_report_returns_widget -x` | Wave 0 |
| HOTFIX-04 SC5 | "build me a pitch deck" → `generate_pitch_deck` called → widget returned | LLM-mocked integration | `uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_generate_pitch_deck_returns_widget -x` | Wave 0 |
| HOTFIX-04 SC4/SC5 (real LLM) | End-to-end: actual user prompt routes through real Gemini → tool selection → download surfaced | manual UAT | (manual: ADK playground or staging chat session) | manual |

### SC4/SC5 verification approach — RECOMMENDED: unit + manual UAT

Three options were considered:
1. **(a) Mock the model + assert tool selection** — high-fidelity but requires mocking the entire ADK runtime; brittle when ADK upgrades. Rejected.
2. **(b) Direct tool-invocation test bypassing the LLM** — verifies the tool function returns the expected `{"status": "success", "widget": {...}}` shape and the widget contract. Combined with the wiring tests (SC1+SC2+SC3), this is sufficient evidence that "the agent CAN invoke the tool and the user CAN receive a downloadable artifact". CHOSEN.
3. **(c) Manual UAT** — actually call the agent with the prompt and observe the result. Required to close SC4/SC5 against the real LLM (we can't unit-test "Gemini chose this tool"). REQUIRED in addition to (b).

**Final approach: (b) + (c).** The unit test suite gates the wiring (SC1/SC2/SC3) and the tool-shape contract (SC4/SC5 mechanical part). A manual UAT in `/dashboard/chat` (or ADK playground) closes the LLM-routing portion — documented as a checklist item in the plan's UAT section, executed once the unit tests are green and the build deploys to staging. Testing real Gemini-driven tool selection in unit tests would require mocking the entire ADK app runtime which has poor signal-to-cost ratio.

The unit-side proxy for SC4/SC5 is:
- The tool function returns the documented `{status, widget}` shape with `data.fileType in {"pdf","pptx"}` (already covered by `tests/unit/services/test_document_service.py:test_generate_pdf_returns_bytes`)
- The tool is in the agent's tool list (Wave 0 SC1 test)
- The agent's prompt names the tool with a clear trigger phrase (Wave 0 SC2/SC3 tests)

### Sampling Rate

- **Per task commit:** `uv run pytest tests/unit/test_phase86_document_gen_wiring.py tests/unit/test_executive_prompt_tool_contract.py -x -q`
- **Per wave merge:** `uv run pytest tests/unit -x -q`
- **Phase gate:** Full suite green + manual UAT log entry (one prompt for PDF, one for pitch deck) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_phase86_document_gen_wiring.py` — covers HOTFIX-04 SC1/SC2/SC3 (mechanical wiring) + SC4/SC5 (tool-shape contract). Recommended skeleton (planner can copy verbatim):

```python
# tests/unit/test_phase86_document_gen_wiring.py
"""Phase 86 wiring tests — DOCUMENT_GEN_TOOLS exposed on Executive + Content Director."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.agent import _EXECUTIVE_TOOLS
from app.agents.content.agent import CONTENT_DIRECTOR_INSTRUCTION
from app.agents.tools.document_gen import (
    DOCUMENT_GEN_TOOLS,
    generate_pdf_report,
    generate_pitch_deck,
)
from app.services.document_service import VALID_TEMPLATES

EXECUTIVE_PROMPT_PATH = Path("app/prompts/executive_instruction.txt")


def _tool_names(tools) -> set[str]:
    return {getattr(t, "__name__", getattr(t, "name", "")) for t in tools}


def test_executive_tools_includes_document_gen() -> None:  # SC1
    names = _tool_names(_EXECUTIVE_TOOLS)
    assert "generate_pdf_report" in names
    assert "generate_pitch_deck" in names


def test_executive_instruction_names_doc_tools() -> None:  # SC2 (names)
    text = EXECUTIVE_PROMPT_PATH.read_text(encoding="utf-8")
    assert "generate_pdf_report" in text
    assert "generate_pitch_deck" in text


def test_executive_instruction_lists_pdf_templates() -> None:  # SC2 (templates)
    text = EXECUTIVE_PROMPT_PATH.read_text(encoding="utf-8")
    for tpl in VALID_TEMPLATES:
        assert tpl in text, f"Template '{tpl}' not named in executive_instruction.txt"


def test_content_director_instruction_mentions_doc_gen() -> None:  # SC3
    text = CONTENT_DIRECTOR_INSTRUCTION
    assert "generate_pdf_report" in text
    assert "generate_pitch_deck" in text
    # Capability mention (SC3 literal: "PDF and PowerPoint generation capability")
    assert "PDF" in text
    assert "PowerPoint" in text or "pptx" in text.lower()


def test_document_gen_tools_export_is_two_callables() -> None:
    assert len(DOCUMENT_GEN_TOOLS) == 2
    assert all(callable(t) for t in DOCUMENT_GEN_TOOLS)
    assert generate_pdf_report in DOCUMENT_GEN_TOOLS
    assert generate_pitch_deck in DOCUMENT_GEN_TOOLS


# SC4/SC5 mechanical proxy — uses existing DocumentService test pattern
@pytest.mark.asyncio
async def test_generate_pdf_report_returns_widget(monkeypatch) -> None:  # SC4 proxy
    """When the agent invokes generate_pdf_report, a widget is returned."""
    from unittest.mock import AsyncMock, MagicMock, patch

    fake_widget = {"type": "document", "data": {"fileType": "pdf", "sizeBytes": 4096}}
    mock_service = MagicMock()
    mock_service.generate_pdf = AsyncMock(return_value=fake_widget)

    monkeypatch.setattr(
        "app.services.request_context.get_current_user_id",
        lambda: "user-1",
    )
    monkeypatch.setattr(
        "app.services.request_context.get_current_session_id",
        lambda: "sess-1",
    )

    with patch("app.services.document_service.DocumentService", return_value=mock_service):
        result = await generate_pdf_report(
            template="financial_report",
            data={"revenue": 100.0, "expenses": 50.0, "period": "Q1"},
            title="Q1 Financials",
        )

    assert result["status"] == "success"
    assert result["widget"]["data"]["fileType"] == "pdf"


@pytest.mark.asyncio
async def test_generate_pitch_deck_returns_widget(monkeypatch) -> None:  # SC5 proxy
    """When the agent invokes generate_pitch_deck, a widget is returned."""
    from unittest.mock import AsyncMock, MagicMock, patch

    fake_widget = {"type": "document", "data": {"fileType": "pptx", "sizeBytes": 8192}}
    mock_service = MagicMock()
    mock_service.generate_pptx = AsyncMock(return_value=fake_widget)
    mock_service.render_chart = MagicMock(return_value=b"\x89PNG_fake")

    monkeypatch.setattr(
        "app.services.request_context.get_current_user_id",
        lambda: "user-1",
    )
    monkeypatch.setattr(
        "app.services.request_context.get_current_session_id",
        lambda: "sess-1",
    )

    with patch("app.services.document_service.DocumentService", return_value=mock_service):
        result = await generate_pitch_deck(
            content=[
                {"title": "Cover", "content": ["Pikar AI"]},
                {"title": "Problem", "content": ["X is hard"]},
            ],
            title="Investor Deck",
        )

    assert result["status"] == "success"
    assert result["widget"]["data"]["fileType"] == "pptx"
```

- [ ] No new framework install — pytest + pytest-asyncio + monkeypatch are already in the dev dependencies.
- [ ] No new fixtures — request_context is patched per-test inline.

## Open Questions / Risks

### Q1: Section 19 ("Google Workspace") collision
**Question:** Does adding section 23 risk confusing the agent ("when do I use `create_report_doc` vs `generate_pdf_report`?")?
**Resolution:** The proposed prose explicitly says: "Do NOT call these tools for Google Docs / Sheets / Forms — those go to section 19. These are FOR downloadable, brand-styled standalone artifacts." This disambiguation is the same pattern section 18A uses to keep app-builder routing clean.

### Q2: Sub-agent overlap — Content Director vs Strategic / Sales / Operations
**Question:** All 11 specialist agents already have `*DOCUMENT_GEN_TOOLS` in their tool list. If the user asks the Executive for a "financial report PDF", will the LLM call `generate_pdf_report` directly OR delegate to FinancialAnalysisAgent (who would call it)?
**Resolution:** Either path satisfies SC4. The new executive prompt section makes "call directly" explicit. Plan can add a single delegation rule to the new section if needed: "For domain-specific PDFs (financial, sales, marketing data), prefer delegation to the matching specialist who will call `generate_pdf_report` with their domain data; for cross-domain or simple template-fill requests, call it yourself." The planner can decide based on UAT outcome — start without delegation rule, add one if needed.

### Q3: Template docstring mismatch
**Risk:** `document_gen.py:53-65` docstring lists 4 templates; `VALID_TEMPLATES` has 5 (includes `sales_proposal`). The runtime check at line 83 uses `VALID_TEMPLATES`, so passing `template="sales_proposal"` works. The proposed instruction prose names all 5.
**Action:** Optional cleanup — update the docstring in `document_gen.py:53-65` to add `sales_proposal`. Not required by SC; flag as a follow-up nit. Do NOT include in this phase to keep diff minimal.

### Q4: Cross-tab / persona implications
**Question:** Does the persona-aware routing (`build_persona_policy_block`) need updating for solopreneur vs enterprise PDF use cases?
**Resolution:** No. The persona block is appended at runtime (`app/agent.py:288-303`) and shapes tone/routing, not capability set. Adding tools is orthogonal to persona policy.

### Q5: `apply_timing` / `_sanitize` interaction
**Risk:** Both wrappers iterate over the tool list. Adding two more callables triggers `apply_timing` to add tool_timing telemetry around them and `_sanitize` to validate the schemas.
**Resolution:** Both tools are already exposed via 10 specialist agents using the same wrappers. No new compatibility risk.

### Q6: Existing uncommitted modifications in working tree
**Status:** Working tree has unrelated edits (`frontend/__tests__/...`, `app/routers/sessions.py`, `frontend/src/hooks/...`). None overlap with the 3 files this phase modifies. Plan can commit Phase 86 changes in isolation.

## Implementation Notes

### Ordering hint
The three changes are independent — they can land in any order, in a single commit, or split across two commits (one for Python, one for the .txt prompt). Recommended single-commit sequence:
1. `app/agent.py` import + tool spread (smallest diff)
2. `app/prompts/executive_instruction.txt` section 23 append
3. `app/agents/content/agent.py` CONTENT_DIRECTOR_INSTRUCTION block insert
4. `tests/unit/test_phase86_document_gen_wiring.py` create
5. Run `uv run pytest tests/unit/test_phase86_document_gen_wiring.py tests/unit/test_executive_prompt_tool_contract.py -x` — all green
6. Run full unit suite for regression confirmation

### ADK conventions
- ADK tool functions exposed to an LlmAgent must be `async def` (Phase 77 enforced this) — both target functions are already async (`document_gen.py:41,114`). Compatible.
- ADK auto-extracts the docstring as the tool description shown to the LLM. `generate_pdf_report`'s docstring already enumerates 4 templates — the LLM reads this. Adding `sales_proposal` to the docstring is a quality-of-tool-description improvement (Open Question Q3), not a phase requirement.
- `apply_timing` wraps the function with telemetry; `_sanitize` strips ADK-incompatible kwargs. Both are idempotent over additional tools.
- The Executive's `tools=` list is FLAT — sub-agent tools are NOT included via spread; sub-agents are passed via `sub_agents=`. This is why SC1 specifically requires `*DOCUMENT_GEN_TOOLS` in `_EXECUTIVE_TOOLS` even though all 10 specialists already have it: ADK delegation requires the Executive to either (a) call the tool itself, or (b) delegate to a specialist who calls it. SC1 ensures option (a) is available without forced delegation.

### Gotchas
1. **`test_executive_prompt_file_matches_factory_default`** (`test_executive_prompt_tool_contract.py:91-95`) asserts `EXECUTIVE_INSTRUCTION == DEFAULT_EXECUTIVE_INSTRUCTION` and both equal the file contents. `EXECUTIVE_INSTRUCTION` (`app/agent.py:243-258`) appends shared instruction blocks to the file contents — the test reads the file directly and compares to the in-memory composition only via `DEFAULT_EXECUTIVE_INSTRUCTION` (which loads the file at import). Editing the .txt file alone is correct; do NOT edit `app/agent.py:243-258`.
2. **Idempotency of `_sanitize`**: passing the same callable twice is safe (it's deduplicated) but unnecessary. Don't add `*DOCUMENT_GEN_TOOLS` AND `generate_pdf_report` separately.
3. **Frontend widget rendering**: The widget shape returned by both tools is rendered by the existing chat UI (Phase 40 work). No frontend changes needed for Phase 86. Verify in manual UAT.
4. **No breaking change to specialists**: Specialists still own their existing `*DOCUMENT_GEN_TOOLS` spread — Phase 86 only adds Executive-level access; specialists are untouched.
5. **Cloud Run / SSE**: The PDF/PPTX render runs in a thread pool via `DocumentService.generate_pdf` / `generate_pptx` (`document_service.py:92-`). Render time is typically <5s — well under the 570s SSE timeout (Phase 85). Confirm in UAT for very large reports.

### Token cost
The new executive_instruction section adds ~250 words. With Phase 78's context cache (10 min TTL, 2048-token threshold), the marginal cost is negligible after first request per session.

## Sources

### Primary (HIGH confidence)
- `app/agents/tools/document_gen.py` — full file read; tool signatures, DOCUMENT_GEN_TOOLS export
- `app/services/document_service.py` (lines 1-120) — VALID_TEMPLATES, generate_pdf signature
- `app/agent.py` — full file read; _EXECUTIVE_TOOLS structure and current import block
- `app/agents/content/agent.py` — full file read; CONTENT_DIRECTOR_INSTRUCTION and tool list confirming DOCUMENT_GEN_TOOLS at line 592
- `app/prompts/executive_instruction.txt` — full file read; 22 numbered capability blocks; tool naming convention
- `tests/unit/test_executive_prompt_tool_contract.py` — full file read; the contract gate that determines what changes are safe
- `tests/unit/services/test_document_service.py` (lines 1-280) — widget contract shape (`fileType="pdf"`, `sizeBytes`); existing test patterns for SC4/SC5 proxy
- `app/services/user_agent_factory.py` — DEFAULT_EXECUTIVE_INSTRUCTION load path
- 10 specialist agent files (sales/operations/financial/content/etc.) — canonical `*DOCUMENT_GEN_TOOLS` spread pattern
- `.planning/phases/40-data-i-o-document-generation/40-VERIFICATION.md` — Phase 40 shipped both tools and registered them on 10 agents

### Secondary (MEDIUM confidence)
- `.planning/phases/62-sales-agent-enhancement/62-01-PLAN.md` (line 88) — confirms `DOCUMENT_GEN_TOOLS = [generate_pdf_report, generate_pitch_deck]` invariant

### Tertiary
- None — no WebSearch needed; full ground truth lives in repo.

## Metadata

**Confidence breakdown:**
- Tool existence + export pattern: HIGH — verified by direct file read
- Wiring pattern (`*DOCUMENT_GEN_TOOLS` spread): HIGH — 10 specialist agents follow it identically
- Executive prompt location + format: HIGH — file read in full; section structure clear
- CONTENT_DIRECTOR_INSTRUCTION format: HIGH — file read in full
- Validation strategy: HIGH — existing contract tests (`test_executive_prompt_tool_contract.py`) provide ready-made gate; new test file template is mechanical
- Open Question Q2 (delegation vs direct call): MEDIUM — depends on Gemini routing behavior, resolved via UAT
- SC4/SC5 LLM-routing verification: MEDIUM — mechanical wiring is HIGH-confidence, but real LLM behavior requires manual UAT

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (30 days; codebase is stable; only DOCUMENT_GEN_TOOLS shape would need re-verification if Phase 89 Knowledge Vault Auto Sync changes the widget contract)
