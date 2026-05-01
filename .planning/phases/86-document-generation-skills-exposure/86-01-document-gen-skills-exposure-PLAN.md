---
phase: 86-document-generation-skills-exposure
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - app/agent.py
  - app/prompts/executive_instruction.txt
  - app/agents/content/agent.py
  - tests/unit/test_phase86_document_gen_wiring.py
  - .planning/phases/86-document-generation-skills-exposure/86-MANUAL-UAT.md
autonomous: true
requirements:
  - HOTFIX-04
nyquist_compliant: true
sc4_sc5_verification: unit_plus_manual_uat

must_haves:
  truths:
    - "SC1: Executive agent's `_EXECUTIVE_TOOLS` list (in `app/agent.py`) includes both `generate_pdf_report` and `generate_pitch_deck` callables (via `*DOCUMENT_GEN_TOOLS` spread)"
    - "SC2: `app/prompts/executive_instruction.txt` names `generate_pdf_report` and `generate_pitch_deck` and lists all 5 `VALID_TEMPLATES` (`financial_report`, `project_proposal`, `meeting_summary`, `competitive_analysis`, `sales_proposal`)"
    - "SC3: `CONTENT_DIRECTOR_INSTRUCTION` in `app/agents/content/agent.py` mentions `generate_pdf_report`, `generate_pitch_deck`, and the words 'PDF' and 'PowerPoint' (or 'pptx')"
    - "SC4 (mechanical proxy): `generate_pdf_report` returns a `{status: 'success', widget: {data: {fileType: 'pdf', ...}}}` shape — proven in unit test. Real-LLM portion (Gemini routes 'create a financial report PDF' → tool call) closed by manual UAT logged in 86-MANUAL-UAT.md."
    - "SC5 (mechanical proxy): `generate_pitch_deck` returns a `{status: 'success', widget: {data: {fileType: 'pptx', ...}}}` shape — proven in unit test. Real-LLM portion (Gemini routes 'build me a pitch deck' → tool call) closed by manual UAT logged in 86-MANUAL-UAT.md."
    - "Existing prompt-tool contract gate (`tests/unit/test_executive_prompt_tool_contract.py`) continues to pass — proves no orphaned tool references in either prompt"
  artifacts:
    - path: "tests/unit/test_phase86_document_gen_wiring.py"
      provides: "7-test wiring suite covering SC1-SC5 (mechanical proxy for SC4/SC5)"
      contains: "test_executive_tools_includes_document_gen, test_executive_instruction_names_doc_tools, test_executive_instruction_lists_pdf_templates, test_content_director_instruction_mentions_doc_gen, test_document_gen_tools_export_is_two_callables, test_generate_pdf_report_returns_widget, test_generate_pitch_deck_returns_widget"
    - path: "app/agent.py"
      provides: "Executive agent with DOCUMENT_GEN_TOOLS imported + spread into _EXECUTIVE_TOOLS"
      contains: "from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS, *DOCUMENT_GEN_TOOLS,"
    - path: "app/prompts/executive_instruction.txt"
      provides: "Numbered section 23 'Branded Document Generation' naming both tools and all 5 templates"
      contains: "generate_pdf_report, generate_pitch_deck, financial_report, project_proposal, meeting_summary, competitive_analysis, sales_proposal"
    - path: "app/agents/content/agent.py"
      provides: "CONTENT_DIRECTOR_INSTRUCTION with '## BRANDED DOCUMENT GENERATION (PDF + PowerPoint)' block"
      contains: "BRANDED DOCUMENT GENERATION, generate_pdf_report, generate_pitch_deck, PDF, PowerPoint"
    - path: ".planning/phases/86-document-generation-skills-exposure/86-MANUAL-UAT.md"
      provides: "Manual UAT log for SC4/SC5 real-Gemini routing closure"
      contains: "Two prompts (PDF + pitch deck), pass/fail outcomes, evidence"
  key_links:
    - from: "app/agent.py:_EXECUTIVE_TOOLS"
      to: "app.agents.tools.document_gen.DOCUMENT_GEN_TOOLS"
      via: "*DOCUMENT_GEN_TOOLS spread inside _sanitize(apply_timing([...]))"
      pattern: "\\*DOCUMENT_GEN_TOOLS,"
    - from: "app/prompts/executive_instruction.txt"
      to: "tools registered on _EXECUTIVE_TOOLS"
      via: "test_executive_prompt_references_only_accessible_tools (existing contract gate)"
      pattern: "generate_pdf_report.*generate_pitch_deck"
    - from: "app/agents/content/agent.py:CONTENT_DIRECTOR_INSTRUCTION"
      to: "DOCUMENT_GEN_TOOLS already wired at line 592"
      via: "test_all_specialist_agent_prompts_reference_only_available_tools (existing contract gate)"
      pattern: "BRANDED DOCUMENT GENERATION"
---

<objective>
Expose `generate_pdf_report` and `generate_pitch_deck` to the Executive Agent and name them in both the Executive and Content Director instruction prompts so the LLM can route user requests like "create a financial report PDF" or "build me a pitch deck" to the correct tool.

**Purpose:** Production hotfix HOTFIX-04. The DocumentService and tool functions have shipped (Phase 40, 2026-04-04) and 10 specialist agents already have the tools wired — but the Executive Agent has neither the import nor the prompt naming, and the Content Director has the tools wired but never names them in its instruction. This 3-touchpoint wiring fix closes the gap so users can actually invoke document generation through chat.

**Output:** 3 file edits + 1 new test file + 1 new manual UAT log. Single Wave 0 (TDD pattern: RED test commit → GREEN implementation commit).

**SC4/SC5 verification approach (LOCKED):** unit (mechanical proxy: tool returns `{status, widget, fileType}` shape + wiring presence) + manual UAT (real Gemini routes the natural-language prompt). LLM-mocked integration tests were considered and rejected as brittle — see 86-RESEARCH.md § Validation Architecture.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/86-document-generation-skills-exposure/86-RESEARCH.md
@.planning/phases/86-document-generation-skills-exposure/86-VALIDATION.md

# Files this plan modifies (read for current state before editing)
@app/agent.py
@app/prompts/executive_instruction.txt
@app/agents/content/agent.py

# Read-only context (signatures, exports, contract gate)
@app/agents/tools/document_gen.py
@app/services/document_service.py
@tests/unit/test_executive_prompt_tool_contract.py

<interfaces>
<!-- Key contracts the executor needs. Embedded so executor does not have to grep the codebase. -->

From `app/agents/tools/document_gen.py:184` (already exists, do NOT modify):
```python
DOCUMENT_GEN_TOOLS = [generate_pdf_report, generate_pitch_deck]
```

From `app/agents/tools/document_gen.py:41` (signature, do NOT modify):
```python
async def generate_pdf_report(
    template: str,
    data: dict[str, Any],
    title: str | None = None,
) -> dict[str, Any]:
    """Returns {"status": "success", "widget": {...}} or {"status": "error", "message": ...}.

    Widget shape carries data.fileType="pdf", data.sizeBytes, signed download URL.
    """
```

From `app/agents/tools/document_gen.py:114` (signature, do NOT modify):
```python
async def generate_pitch_deck(
    content: list[dict[str, Any]],
    title: str | None = None,
) -> dict[str, Any]:
    """Returns {status, widget} with data.fileType="pptx".

    Each slide dict: {"title": str, "content": list[str], "chart_data"?: {...}}.
    """
```

From `app/services/document_service.py:53-59` (single source of truth, do NOT modify):
```python
VALID_TEMPLATES = [
    "financial_report",
    "project_proposal",
    "meeting_summary",
    "competitive_analysis",
    "sales_proposal",
]
```

From `app/agent.py:60-105` (current import block — `decision_journal` at line 78, `deep_research` at line 81; new import slots between them on line 79-80):
```python
# Import decision journal tools for logging and querying past decisions
from app.agents.tools.decision_journal import DECISION_JOURNAL_TOOLS

# Import Deep Research tools for intelligent research behavior
from app.agents.tools.deep_research import DEEP_RESEARCH_TOOLS
```

From `app/agent.py:260-285` (current `_EXECUTIVE_TOOLS` — DECISION_JOURNAL_TOOLS at line 281, ONBOARDING_NUDGE_TOOLS at line 282; new spread slots between them):
```python
_EXECUTIVE_TOOLS = _sanitize(
    apply_timing(
        [
            search_business_knowledge,
            ...
            *DECISION_JOURNAL_TOOLS,
            *ONBOARDING_NUDGE_TOOLS,
        ]
    )
)
```

From `app/prompts/executive_instruction.txt` lines 206-213 (insertion point — new section 23 lands between line 211 and line 213):
```text
22. **Onboarding Nudges**: Help new users get started:
   - `check_onboarding_nudges`: ...
   ...
   - Example: "By the way, I noticed you haven't tried [feature] yet ..."

## AUTO-INITIATIVE DETECTION
```

From `app/agents/content/agent.py:362-369` (insertion point — new "## BRANDED DOCUMENT GENERATION" block lands between line 367 and line 369):
```text
## CONTENT TYPES YOU SUPPORT
- **Standard Video Ads**: ...
- **Full Campaign Bundles**: Video + graphics + copy for a complete campaign

## DELEGATION STRATEGY
```

From `app/agents/content/agent.py` line 592 (already exists — Content Director ALREADY has DOCUMENT_GEN_TOOLS wired; Phase 86 only adds the prose):
```python
*DOCUMENT_GEN_TOOLS,
```

From `tests/unit/test_executive_prompt_tool_contract.py` (existing contract gate — must continue passing):
- `test_executive_prompt_references_only_accessible_tools` — any tool name in executive_instruction.txt MUST be reachable via `executive_agent.tools` recursively
- `test_all_specialist_agent_prompts_reference_only_available_tools` — same for content_agent + 10 others
- `test_executive_prompt_file_matches_factory_default` — file content equals `DEFAULT_EXECUTIVE_INSTRUCTION` loaded at import. Editing the .txt is correct; do NOT edit `app/agent.py:243-258` (the EXECUTIVE_INSTRUCTION composition).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED): Write Phase 86 wiring test suite + manual UAT scaffold, commit RED</name>
  <files>tests/unit/test_phase86_document_gen_wiring.py, .planning/phases/86-document-generation-skills-exposure/86-MANUAL-UAT.md</files>

  <behavior>
    All 7 tests in `tests/unit/test_phase86_document_gen_wiring.py` must run; AT MINIMUM the wiring tests must FAIL because Task 2's edits are not yet applied:
    - `test_executive_tools_includes_document_gen` → FAILS (no `*DOCUMENT_GEN_TOOLS` in `_EXECUTIVE_TOOLS` yet)
    - `test_executive_instruction_names_doc_tools` → FAILS (executive_instruction.txt does not contain `generate_pdf_report` or `generate_pitch_deck` yet)
    - `test_executive_instruction_lists_pdf_templates` → FAILS (templates not yet listed)
    - `test_content_director_instruction_mentions_doc_gen` → FAILS (CONTENT_DIRECTOR_INSTRUCTION does not mention `generate_pdf_report`/`generate_pitch_deck` yet)

    These tests MAY pass-by-coincidence (acceptable, not required to fail):
    - `test_document_gen_tools_export_is_two_callables` — DOCUMENT_GEN_TOOLS already exists at `document_gen.py:184` and already contains the two callables. This test will pass-green from RED commit. That is fine — it is a regression guard, not a wiring proof.
    - `test_generate_pdf_report_returns_widget` and `test_generate_pitch_deck_returns_widget` — depend on monkeypatching the DocumentService class; may pass if the existing tool already returns the documented shape. Pass-by-coincidence is fine; the wiring tests above are the proof of work for Task 2.

    `86-MANUAL-UAT.md` exists with the two-prompt checklist (PDF + pitch deck) but is unchecked.
  </behavior>

  <action>
    **Step 1.1 — Create `tests/unit/test_phase86_document_gen_wiring.py`:**

    Copy the test file VERBATIM from `86-RESEARCH.md` § Validation Architecture / Wave 0 Gaps (the code block starting `# tests/unit/test_phase86_document_gen_wiring.py`). Do NOT paraphrase. Do NOT reorder tests. Do NOT change variable names.

    Concretely the file contents are:

    ```python
    # tests/unit/test_phase86_document_gen_wiring.py
    """Phase 86 wiring tests -- DOCUMENT_GEN_TOOLS exposed on Executive + Content Director."""
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


    # SC4/SC5 mechanical proxy -- uses existing DocumentService test pattern
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

    **Step 1.2 — Create `.planning/phases/86-document-generation-skills-exposure/86-MANUAL-UAT.md`:**

    ```markdown
    # Phase 86 Manual UAT — SC4/SC5 (real Gemini routing)

    **Phase:** 86 — Document Generation Skills Exposure
    **Requirement:** HOTFIX-04 SC4 + SC5 (LLM-routing portion)
    **Why manual:** Cannot unit-test "Gemini selects this tool from natural-language prompt" without mocking the entire ADK runtime — brittle, low signal/cost ratio.
    **Run after:** Task 2 GREEN + lint + deploy to staging (or `make local-backend` + frontend dev for local UAT).

    ## Setup
    - [ ] Backend running (`make local-backend` OR staging deploy)
    - [ ] Frontend dev running (`cd frontend && npm run dev`) OR ADK playground (`make playground`, port 8501, select 'app' folder)
    - [ ] Logged in as a test user with at least one initiative/session

    ## Test 1: PDF report routing (SC4)

    **Prompt:** `Create a financial report PDF for Q1 2026 revenue.`

    **Expected:**
    - [ ] `generate_pdf_report` tool call appears in the trace (frontend network tab OR ADK playground trace pane)
    - [ ] Tool call uses `template="financial_report"`
    - [ ] Chat response surfaces a downloadable PDF widget (download card)
    - [ ] Clicking the widget downloads a `.pdf` file

    **Result:** ⬜ PASS / ⬜ FAIL
    **Notes:**
    **Screenshot / log link:**

    ## Test 2: Pitch deck routing (SC5)

    **Prompt:** `Build me a pitch deck for an AI scheduling startup.`

    **Expected:**
    - [ ] `generate_pitch_deck` tool call appears in the trace
    - [ ] Chat response surfaces a downloadable PPTX widget
    - [ ] Clicking the widget downloads a `.pptx` file

    **Result:** ⬜ PASS / ⬜ FAIL
    **Notes:**
    **Screenshot / log link:**

    ## Sign-off

    - [ ] Both tests PASS → SC4 and SC5 LLM-routing portion closed
    - [ ] Date executed:
    - [ ] Executed by:
    - [ ] Build / deploy under test (commit SHA or staging URL):
    ```

    **Step 1.3 — Run the focused test suite to confirm RED:**

    ```bash
    uv run pytest tests/unit/test_phase86_document_gen_wiring.py -x -q
    ```

    At MINIMUM these four tests must FAIL (proves Task 2's edits are still missing):
    - `test_executive_tools_includes_document_gen`
    - `test_executive_instruction_names_doc_tools`
    - `test_executive_instruction_lists_pdf_templates`
    - `test_content_director_instruction_mentions_doc_gen`

    Pass-by-coincidence on `test_document_gen_tools_export_is_two_callables`, `test_generate_pdf_report_returns_widget`, and `test_generate_pitch_deck_returns_widget` is acceptable (DOCUMENT_GEN_TOOLS already exists; the proxy tests use monkeypatching).

    **Step 1.4 — Commit RED:**

    ```bash
    node "$HOME/.claude/get-shit-done/bin/gsd-tools.cjs" commit "test(86-01): add Phase 86 wiring test suite + manual UAT scaffold (RED)" --files tests/unit/test_phase86_document_gen_wiring.py .planning/phases/86-document-generation-skills-exposure/86-MANUAL-UAT.md
    ```
  </action>

  <verify>
    <automated>uv run pytest tests/unit/test_phase86_document_gen_wiring.py -x -q 2>&1 | grep -E "test_executive_tools_includes_document_gen|test_executive_instruction_names_doc_tools|test_executive_instruction_lists_pdf_templates|test_content_director_instruction_mentions_doc_gen" | grep -E "FAIL|fail"</automated>
  </verify>

  <done>
    - `tests/unit/test_phase86_document_gen_wiring.py` exists with 7 tests (verbatim from research)
    - `86-MANUAL-UAT.md` exists with two-prompt checklist (PDF + pitch deck)
    - At least the 4 wiring tests above FAIL when the focused suite is run
    - RED commit landed referencing `test(86-01): ... RED`
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2 (GREEN): Apply 3 file edits (verbatim prose from research) → all 7 tests + contract gate green → commit GREEN</name>
  <files>app/agent.py, app/prompts/executive_instruction.txt, app/agents/content/agent.py</files>

  <behavior>
    All 7 tests in `tests/unit/test_phase86_document_gen_wiring.py` GREEN.
    Existing prompt-tool contract gate `tests/unit/test_executive_prompt_tool_contract.py` continues to pass (no orphaned tool refs in either prompt).
    `make lint` (codespell + ruff check + ruff format + ty check + workflow validation) clean.

    Specifically:
    - SC1: `_EXECUTIVE_TOOLS` contains both `generate_pdf_report` and `generate_pitch_deck` callables
    - SC2: `executive_instruction.txt` names both tools and contains all 5 `VALID_TEMPLATES` strings
    - SC3: `CONTENT_DIRECTOR_INSTRUCTION` contains `generate_pdf_report`, `generate_pitch_deck`, `PDF`, and `PowerPoint`
    - SC4/SC5 proxies pass; SC4/SC5 real-LLM portion is closed by manually executing 86-MANUAL-UAT.md (logged outside this commit)
  </behavior>

  <action>
    **CRITICAL: Use VERBATIM prose from `86-RESEARCH.md` § Recommended Implementation. Do NOT paraphrase, do NOT reword, do NOT reorder bullets.**

    ---

    **Step 2.1 — `app/agent.py`: import + spread `*DOCUMENT_GEN_TOOLS`**

    **2.1a — Add import.** Insert AFTER the existing `decision_journal` import block at line 78 and BEFORE the `deep_research` import block at line 80. Concretely, insert these two lines as a NEW block at line 79-80 (after the blank line that follows `from app.agents.tools.decision_journal import DECISION_JOURNAL_TOOLS`):

    ```python
    # Import document generation tools (PDF reports, PowerPoint pitch decks)
    from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS
    ```

    Result (lines 77-83 after edit):
    ```python
    # Import decision journal tools for logging and querying past decisions
    from app.agents.tools.decision_journal import DECISION_JOURNAL_TOOLS

    # Import document generation tools (PDF reports, PowerPoint pitch decks)
    from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS

    # Import Deep Research tools for intelligent research behavior
    from app.agents.tools.deep_research import DEEP_RESEARCH_TOOLS
    ```

    **2.1b — Add tool spread.** Inside `_EXECUTIVE_TOOLS` (currently lines 260-285), insert `*DOCUMENT_GEN_TOOLS,` BETWEEN `*DECISION_JOURNAL_TOOLS,` (line 281) and `*ONBOARDING_NUDGE_TOOLS,` (line 282) — keeps doc-gen next to other "produce-an-artifact" tools, smallest possible diff. Match the existing 12-space indentation.

    Result (the relevant tail of the list after edit):
    ```python
                *CROSS_AGENT_SYNTHESIS_TOOLS,
                *DECISION_JOURNAL_TOOLS,
                *DOCUMENT_GEN_TOOLS,
                *ONBOARDING_NUDGE_TOOLS,
            ]
        )
    )
    ```

    Do NOT touch `EXECUTIVE_INSTRUCTION` composition at lines 243-258 (it's a string concat — unrelated; modifying it would break `test_executive_prompt_file_matches_factory_default`).

    ---

    **Step 2.2 — `app/prompts/executive_instruction.txt`: append numbered section 23**

    Insert the following block AFTER line 211 (the `Example: "By the way, ..."` line — last line of section 22) and BEFORE line 213 (`## AUTO-INITIATIVE DETECTION`). Leave one blank line above and one blank line below to match the spacing pattern between sections 21/22 and 22/AUTO-INITIATIVE.

    **Verbatim prose (copy exactly from `86-RESEARCH.md` § Recommended Implementation / Change 2 — do NOT paraphrase):**

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

    Note: this prose mentions all 5 `VALID_TEMPLATES` (`financial_report`, `project_proposal`, `meeting_summary`, `competitive_analysis`, `sales_proposal`) as required by `test_executive_instruction_lists_pdf_templates`.

    ---

    **Step 2.3 — `app/agents/content/agent.py`: insert "## BRANDED DOCUMENT GENERATION" block**

    Inside `CONTENT_DIRECTOR_INSTRUCTION` (the prose triple-quoted string spanning lines 308-450), insert the following block AFTER line 367 (`- **Full Campaign Bundles**: Video + graphics + copy for a complete campaign`) and BEFORE line 369 (`## DELEGATION STRATEGY`). Match indentation of surrounding sections (no leading whitespace inside the triple-quote — it's flush left in the existing prose).

    **Verbatim prose (copy exactly from `86-RESEARCH.md` § Recommended Implementation / Change 3 — do NOT paraphrase):**

    ```text
    ## BRANDED DOCUMENT GENERATION (PDF + PowerPoint)
    You can produce branded, downloadable documents directly — these complement (not replace) the sub-agent creative work:
    - `generate_pdf_report`: Branded PDF for `financial_report`, `project_proposal`, `meeting_summary`, `competitive_analysis`, or `sales_proposal`. Pass the template name and a structured `data` dict matching that template's schema. Use this when the user asks for a polished PDF report, a downloadable proposal document, a meeting recap PDF, or a sales proposal artifact.
    - `generate_pitch_deck`: Branded PowerPoint (.pptx). Pass `content` as a list of slide dicts (each with `title`, optional `content` bullets, optional `chart_data`). Use this for investor decks, internal pitch decks, sales decks, or any "build me a slide deck" request.

    When the user asks to "make a pitch deck", "create an investor deck", or "build a slide presentation", call `generate_pitch_deck` directly — do NOT delegate to GraphicDesignerAgent (those tools cover individual visuals, not multi-slide PPTX).
    When the user asks for a "PDF report" or "downloadable document", call `generate_pdf_report` directly — do NOT delegate to CopywriterAgent (those tools produce blog/social copy, not formatted PDFs).

    Both tools return `{status, widget}`. On success, tell the user the document is ready and downloadable from the card below. On error, relay the `message` field verbatim — never claim success on failure.
    ```

    Note: the words "PDF" and "PowerPoint" both appear in this block, satisfying `test_content_director_instruction_mentions_doc_gen`.

    Do NOT modify the tool list at line 592 — it already contains `*DOCUMENT_GEN_TOOLS`. Only the prose is missing.

    ---

    **Step 2.4 — Run focused test suite, expect GREEN:**

    ```bash
    uv run pytest tests/unit/test_phase86_document_gen_wiring.py tests/unit/test_executive_prompt_tool_contract.py -x -q
    ```

    All 7 wiring tests + all existing contract tests must pass. If any fail:
    - `test_executive_tools_includes_document_gen` red → check Step 2.1b spread is inside `_EXECUTIVE_TOOLS` and within `_sanitize(apply_timing([...]))`
    - `test_executive_instruction_names_doc_tools` / `test_executive_instruction_lists_pdf_templates` red → re-check Step 2.2 verbatim copy; both tool names + all 5 templates must be exact-string matches
    - `test_content_director_instruction_mentions_doc_gen` red → re-check Step 2.3 verbatim copy; both tool names + 'PDF' + 'PowerPoint' must be exact-string matches
    - `test_executive_prompt_references_only_accessible_tools` red → means Step 2.2 named a tool that is NOT in `_EXECUTIVE_TOOLS`. Verify Step 2.1b landed correctly.
    - `test_executive_prompt_file_matches_factory_default` red → likely means `app/agent.py:243-258` was modified accidentally. Revert and re-edit only the .txt.

    **Step 2.5 — Run full unit suite for regression confirmation:**

    ```bash
    uv run pytest tests/unit -x -q
    ```

    No new failures. Pre-existing failures (if any documented in STATE.md or deferred-items.md) are out of scope.

    **Step 2.6 — Run lint:**

    ```bash
    make lint
    ```

    Must be clean (codespell, ruff check, ruff format, ty check, workflow validation). The .txt prompt file is not lint-targeted; the two .py edits are minimal and follow existing patterns so lint should be quiet.

    **Step 2.7 — Update STATE.md, ROADMAP.md, write SUMMARY:**

    Write `.planning/phases/86-document-generation-skills-exposure/86-01-document-gen-skills-exposure-SUMMARY.md` with:
    - One-sentence outcome (HOTFIX-04 closed; Executive + Content Director can now invoke `generate_pdf_report` and `generate_pitch_deck`)
    - **REQUIRED section: "File Edits with Line Numbers"** listing exactly:
      1. `app/agent.py` — added import at line 79-80 (`from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS`); added `*DOCUMENT_GEN_TOOLS,` spread inside `_EXECUTIVE_TOOLS` between `*DECISION_JOURNAL_TOOLS,` (line ~281) and `*ONBOARDING_NUDGE_TOOLS,` (line ~282)
      2. `app/prompts/executive_instruction.txt` — appended numbered section 23 "Branded Document Generation" (~12 lines) after line 211, before `## AUTO-INITIATIVE DETECTION`
      3. `app/agents/content/agent.py` — inserted `## BRANDED DOCUMENT GENERATION (PDF + PowerPoint)` block (~9 lines) inside `CONTENT_DIRECTOR_INSTRUCTION` after line 367, before `## DELEGATION STRATEGY`
    - Test outcome: 7/7 wiring tests GREEN; existing prompt-tool contract gate continues to pass
    - Manual UAT status: scaffolded in `86-MANUAL-UAT.md` — execute against staging or local before `/gsd:verify-work`
    - Out-of-scope nit: `sales_proposal` missing from `document_gen.py:53-65` docstring (Open Question Q3 in research) — deferred to a follow-up; do NOT bundle into this phase

    Update `.planning/STATE.md` `stopped_at` and `last_activity` lines.
    Update `.planning/ROADMAP.md` Phase 86 entry: mark plan 86-01 as `[x]`, set "Plans: 1/1 plans complete".

    **Step 2.8 — Commit GREEN:**

    ```bash
    node "$HOME/.claude/get-shit-done/bin/gsd-tools.cjs" commit "feat(86-01): wire DOCUMENT_GEN_TOOLS into Executive Agent + name in both prompts (HOTFIX-04 GREEN)" --files app/agent.py app/prompts/executive_instruction.txt app/agents/content/agent.py .planning/phases/86-document-generation-skills-exposure/86-01-document-gen-skills-exposure-SUMMARY.md .planning/STATE.md .planning/ROADMAP.md
    ```
  </action>

  <verify>
    <automated>uv run pytest tests/unit/test_phase86_document_gen_wiring.py tests/unit/test_executive_prompt_tool_contract.py -x -q</automated>
  </verify>

  <done>
    - `app/agent.py` contains `from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS` and `*DOCUMENT_GEN_TOOLS,` inside `_EXECUTIVE_TOOLS` (verbatim spread placement between DECISION_JOURNAL_TOOLS and ONBOARDING_NUDGE_TOOLS)
    - `app/prompts/executive_instruction.txt` contains numbered section 23 with both tool names + all 5 `VALID_TEMPLATES` strings (verbatim from research § Change 2)
    - `app/agents/content/agent.py` `CONTENT_DIRECTOR_INSTRUCTION` contains `## BRANDED DOCUMENT GENERATION (PDF + PowerPoint)` block with both tool names, "PDF", and "PowerPoint" (verbatim from research § Change 3)
    - All 7 tests in `tests/unit/test_phase86_document_gen_wiring.py` GREEN
    - `tests/unit/test_executive_prompt_tool_contract.py` continues to pass (proves no orphaned tool references)
    - `make lint` clean
    - SUMMARY written with the 3-edit file-and-line-number list
    - STATE.md `stopped_at` updated; ROADMAP.md Phase 86 marked `1/1 plans complete`
    - GREEN commit landed
    - `86-MANUAL-UAT.md` remains UNCHECKED — execution against real Gemini happens AFTER this plan completes, before `/gsd:verify-work`
  </done>
</task>

</tasks>

<verification>
**Phase-level checks (run after Task 2 GREEN, before sign-off):**

1. **SC1 — wiring presence:**
   ```bash
   uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_executive_tools_includes_document_gen -x
   ```
   Pass = both `generate_pdf_report` and `generate_pitch_deck` reachable on `_EXECUTIVE_TOOLS`.

2. **SC2 — executive prompt names + templates:**
   ```bash
   uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_executive_instruction_names_doc_tools tests/unit/test_phase86_document_gen_wiring.py::test_executive_instruction_lists_pdf_templates -x
   ```
   Pass = both tool names + all 5 `VALID_TEMPLATES` strings present.

3. **SC3 — content director prompt:**
   ```bash
   uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_content_director_instruction_mentions_doc_gen -x
   ```
   Pass = both tool names + "PDF" + "PowerPoint" present.

4. **SC4/SC5 mechanical proxy:**
   ```bash
   uv run pytest tests/unit/test_phase86_document_gen_wiring.py::test_generate_pdf_report_returns_widget tests/unit/test_phase86_document_gen_wiring.py::test_generate_pitch_deck_returns_widget -x
   ```
   Pass = both tools return `{status: 'success', widget: {data: {fileType in {pdf,pptx}}}}` shape.

5. **Existing contract gate (sanity):**
   ```bash
   uv run pytest tests/unit/test_executive_prompt_tool_contract.py -x
   ```
   Pass = no orphaned tool references in either edited prompt.

6. **Full unit suite (regression):**
   ```bash
   uv run pytest tests/unit -x -q
   ```
   Pass = no new failures.

7. **Lint:**
   ```bash
   make lint
   ```
   Clean.

8. **SC4/SC5 LLM-routing portion (manual UAT, AFTER plan completion, BEFORE `/gsd:verify-work`):**
   - Start backend (`make local-backend`) + frontend (`cd frontend && npm run dev`) OR ADK playground (`make playground`).
   - Open `/dashboard/chat`. Run prompt 1: "Create a financial report PDF for Q1 2026 revenue." Verify `generate_pdf_report` is called with `template="financial_report"` and a downloadable PDF widget surfaces. Log result in `86-MANUAL-UAT.md`.
   - Run prompt 2: "Build me a pitch deck for an AI scheduling startup." Verify `generate_pitch_deck` is called and a downloadable PPTX widget surfaces. Log result in `86-MANUAL-UAT.md`.
   - Both prompts must PASS to close SC4/SC5.
</verification>

<success_criteria>
1. **SC1 (mechanical):** `_EXECUTIVE_TOOLS` includes `*DOCUMENT_GEN_TOOLS` — both `generate_pdf_report` and `generate_pitch_deck` callables present. Verified by `test_executive_tools_includes_document_gen`.
2. **SC2 (mechanical):** `executive_instruction.txt` names both tools and lists all 5 `VALID_TEMPLATES`. Verified by `test_executive_instruction_names_doc_tools` + `test_executive_instruction_lists_pdf_templates`.
3. **SC3 (mechanical):** `CONTENT_DIRECTOR_INSTRUCTION` mentions both tool names + "PDF" + "PowerPoint" (or "pptx"). Verified by `test_content_director_instruction_mentions_doc_gen`.
4. **SC4 (mechanical proxy):** `generate_pdf_report` returns the documented `{status, widget, data.fileType="pdf"}` shape. Verified by `test_generate_pdf_report_returns_widget`. **LLM-routing portion verified by manual UAT** (`86-MANUAL-UAT.md` Test 1).
5. **SC5 (mechanical proxy):** `generate_pitch_deck` returns the documented `{status, widget, data.fileType="pptx"}` shape. Verified by `test_generate_pitch_deck_returns_widget`. **LLM-routing portion verified by manual UAT** (`86-MANUAL-UAT.md` Test 2).
6. **Contract gate intact:** `test_executive_prompt_tool_contract.py` continues to pass — proves zero orphaned tool references in either prompt.
7. **No regressions:** Full unit suite green; `make lint` clean.
8. **Out-of-scope confirmed deferred:** `sales_proposal` missing from `document_gen.py:53-65` docstring — flagged in research Open Question Q3, deferred to a follow-up PR. NOT bundled into this phase.
</success_criteria>

<output>
After completion, create `.planning/phases/86-document-generation-skills-exposure/86-01-document-gen-skills-exposure-SUMMARY.md` (Step 2.7 above produces it).

The SUMMARY MUST include a "File Edits with Line Numbers" section listing the 3 edits with their exact insertion points so a future reader can locate them without re-running diff.
</output>
