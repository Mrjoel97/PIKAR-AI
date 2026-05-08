---
phase: 108-hygiene-and-coverage
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - app/agents/content/agent.py
  - tests/unit/agents/test_content_agent_tools.py
autonomous: true
requirements: [HYGIENE-03]

must_haves:
  truths:
    - "ContentCreationAgent's tools list contains list_connected_accounts, publish_to_social, get_oauth_url, and disconnect_social_account — verified by inspecting agent.tools after create_content_agent() returns"
    - "ContentCreationAgent can publish content to social platforms WITHOUT delegating to MarketingAutomationAgent's SocialMedia sub-agent — the LLM tool registry contains the social functions directly"
    - "MarketingAutomationAgent's SocialMedia sub-agent (_SOCIAL_TOOLS_LIST at marketing/agent.py:369-378) is unchanged — no regression to the existing path; both agents may share the same tool functions (stateless module-level)"
    - "CONTENT_DIRECTOR_INSTRUCTION mentions the new direct social posting capability so the LLM understands it doesn't need to delegate for single-post requests"
  artifacts:
    - path: "app/agents/content/agent.py"
      provides: "Imports SOCIAL_TOOLS from app.agents.tools.social; spreads *SOCIAL_TOOLS into create_content_agent's tools list inside sanitize_tools(); CONTENT_DIRECTOR_INSTRUCTION updated with a 'Direct Social Posting' section"
      contains: "from app.agents.tools.social import SOCIAL_TOOLS"
    - path: "tests/unit/agents/test_content_agent_tools.py"
      provides: "Two tests: (1) ContentCreationAgent has all 4 social tools in its tool list; (2) MarketingAutomationAgent's SocialMedia sub-agent is unchanged (regression check)"
      contains: "test_content_agent_has_social_tools"
  key_links:
    - from: "app/agents/content/agent.py:create_content_agent (tools list)"
      to: "app/agents/tools/social.py:SOCIAL_TOOLS"
      via: "*SOCIAL_TOOLS spread inside sanitize_tools(...) tools list"
      pattern: "\\*SOCIAL_TOOLS"
    - from: "app/agents/content/agent.py:CONTENT_DIRECTOR_INSTRUCTION"
      to: "User-facing direct posting capability"
      via: "New 'DIRECT SOCIAL POSTING' subsection that names list_connected_accounts, publish_to_social, get_oauth_url, disconnect_social_account and explains when to delegate vs. post directly"
      pattern: "DIRECT SOCIAL POSTING"
---

<objective>
Eliminate the skill-bridge indirection: today, ContentCreationAgent (CMO/Creative Director) cannot post drafted content to social media without delegating to MarketingAutomationAgent → SocialMediaAgent. Add `*SOCIAL_TOOLS` directly to ContentCreationAgent's tool list and update its system prompt so it knows it can post directly for simple single-post requests. Marketing's SocialMedia sub-agent stays exactly as-is (regression-free) — both agents share the same stateless tool functions.

Purpose: Satisfy HYGIENE-03 ("ContentAgent has direct access to SOCIAL_TOOLS; LLM can post drafted content to social without delegating to a sub-agent"). The audit flagged this as a class-of-bug — the LLM frequently produces drafts and then has to context-switch through delegation just to publish them, dramatically lengthening turn counts and dropping accuracy.

Output: A two-line code change (import + tools list spread), a prompt update, and two test assertions. Smallest plan in the phase but high product value — every Content-Agent-driven social post avoids one delegation hop.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/108-hygiene-and-coverage/108-CONTEXT.md
@.planning/phases/108-hygiene-and-coverage/108-RESEARCH.md
@app/agents/content/agent.py
@app/agents/tools/social.py
@app/agents/marketing/agent.py
@app/agents/tools/base.py

<interfaces>
<!-- Key contracts the executor needs. -->

From app/agents/tools/social.py (current shape — keep stable):
```python
SOCIAL_TOOLS = [
    list_connected_accounts,    # def(user_id) -> list[dict]
    publish_to_social,          # def(user_id, platform, content, media_url=, media_urls=, media_type=, utm_params=, extra=) -> dict
    get_oauth_url,              # def(platform, user_id, redirect_uri=) -> dict
    disconnect_social_account,  # def(user_id, platform) -> dict
]
```

From app/agents/marketing/agent.py:368-378 (REFERENCE — DO NOT MODIFY in this plan):
```python
_SOCIAL_TOOLS_LIST = sanitize_tools([
    *SOCIAL_TOOLS,
    *SOCIAL_ANALYTICS_TOOLS,
    *SOCIAL_LISTENING_TOOLS,
    *PUBLISHING_STRATEGY_TOOLS,
    mcp_web_search,
    *CONTEXT_MEMORY_TOOLS,
])
```

From app/agents/content/agent.py — current tools list (lines 594-623):
```python
tools=sanitize_tools([
    simple_create_content,
    suggest_and_schedule_content,
    learn_brand_voice,
    get_content_performance,
    search_knowledge,
    process_brain_dump,
    process_brainstorm_conversation,
    get_braindump_document,
    *BRAND_PROFILE_TOOLS,
    *CREATIVE_BRIEF_TOOLS,
    *ART_DIRECTION_TOOLS,
    *CONTENT_PIPELINE_TOOLS,
    *CONTEXT_MEMORY_TOOLS,
    *CONT_IMPROVE_TOOLS,
    *GRAPH_TOOLS,
    search_system_knowledge,
    *DOCUMENT_GEN_TOOLS,
    *DOCUMENT_EDITOR_TOOLS,
])
```

From app/agents/tools/base.py:sanitize_tools (REFERENCE):
- Accepts a list of callables/agent objects; deduplicates by name; returns the deduplicated list.
- Already handles tool overlap if any tool in SOCIAL_TOOLS happened to share a name with an existing Content Agent tool (none do today).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add SOCIAL_TOOLS to ContentCreationAgent + update prompt + test</name>
  <files>
    app/agents/content/agent.py,
    tests/unit/agents/test_content_agent_tools.py
  </files>
  <behavior>
    **RED — tests/unit/agents/test_content_agent_tools.py (NEW file, 2 tests):**

    1. `test_content_agent_has_social_tools`:
       ```python
       from app.agents.content.agent import create_content_agent

       def test_content_agent_has_social_tools():
           agent = create_content_agent()
           tool_names = set()
           for t in agent.tools:
               # ADK tool may be a function or an object with a `.name` attribute
               name = getattr(t, "__name__", None) or getattr(t, "name", None)
               if name:
                   tool_names.add(name)
           assert "publish_to_social" in tool_names, f"Missing publish_to_social. Got: {sorted(tool_names)}"
           assert "list_connected_accounts" in tool_names
           assert "get_oauth_url" in tool_names
           assert "disconnect_social_account" in tool_names
       ```

    2. `test_marketing_social_subagent_unchanged_regression`:
       Import `_SOCIAL_TOOLS_LIST` directly from `app.agents.marketing.agent` (it's a module-level constant). Assert its function names are the union of `SOCIAL_TOOLS + SOCIAL_ANALYTICS_TOOLS + SOCIAL_LISTENING_TOOLS + PUBLISHING_STRATEGY_TOOLS + [mcp_web_search] + CONTEXT_MEMORY_TOOLS`. This is a guardrail against accidental refactors that pull SOCIAL_TOOLS out of the Marketing path:
       ```python
       def test_marketing_social_subagent_unchanged_regression():
           from app.agents.marketing.agent import _SOCIAL_TOOLS_LIST
           from app.agents.tools.social import SOCIAL_TOOLS
           tool_names = {getattr(t, "__name__", None) or getattr(t, "name", None) for t in _SOCIAL_TOOLS_LIST}
           tool_names.discard(None)
           # All 4 SOCIAL_TOOLS must still be in the marketing list
           for fn in SOCIAL_TOOLS:
               assert fn.__name__ in tool_names, f"Marketing path lost {fn.__name__}"
       ```

    Run `uv run pytest tests/unit/agents/test_content_agent_tools.py -x` — confirm test 1 fails (RED, agent doesn't have social tools) and test 2 passes (regression baseline already correct).

    Commit: `test(108-03): add ContentAgent social-tools assertion + marketing regression guard (HYGIENE-03)`.

    **GREEN — implementation:**

    1. **`app/agents/content/agent.py` — add import** (alphabetical placement among the `app.agents.tools.*` imports, between `self_improve` at line 86 and `system_knowledge` at line 87):
       ```python
       from app.agents.tools.social import SOCIAL_TOOLS
       ```

    2. **Spread `*SOCIAL_TOOLS` into the tools list** at `create_content_agent` (around line 615, after `*GRAPH_TOOLS` and before `search_system_knowledge`):
       ```python
       tools=sanitize_tools([
           # ... existing tools ...
           *GRAPH_TOOLS,
           # HYGIENE-03: direct social posting (no Marketing delegation needed
           # for single-platform single-post requests)
           *SOCIAL_TOOLS,
           # Phase 12.1: system knowledge
           search_system_knowledge,
           # ...
       ]),
       ```

    3. **Update `CONTENT_DIRECTOR_INSTRUCTION`** (the prompt is around lines 311-465). Add a new subsection. Recommended insertion point: AFTER any existing "Delegation strategy" or capabilities block, BEFORE the closing instructions. Search for a stable anchor (e.g., the current text that talks about delegating to sub-agents) and insert this block:

       ```
       ## DIRECT SOCIAL POSTING

       You can publish directly to connected social accounts WITHOUT delegating to MarketingAgent for single-post requests:

       - Use `list_connected_accounts(user_id)` to check which platforms the user has connected before posting.
       - Use `get_oauth_url(platform, user_id)` if the user wants to connect a NEW platform — return the URL for them to visit.
       - Use `publish_to_social(user_id, platform, content, media_url=..., media_type='image'|'video'|'text', extra=...)` to publish.
         - For Pinterest: pass `extra={"board_id": "<board>"}` (required).
         - For Threads: media_type can be 'text', 'image', or 'video'.
         - For Instagram: media is required (text-only is rejected by the API).
       - Use `disconnect_social_account(user_id, platform)` to revoke a connection.

       DELEGATE to MarketingAgent's SocialMediaAgent sub-agent ONLY when:
       - The user wants a multi-platform campaign requiring per-platform copy variations.
       - Posting strategy / scheduling / hashtag optimization matters more than the post itself.
       - Analytics or competitor listening is requested alongside the post.

       For "post this draft to Twitter" or "create a pin from this image on board X", post directly — no delegation needed.
       ```

       The exact insertion point is the executor's discretion; the prompt is long and the audit doesn't pin a single line. Pick a location that's adjacent to other capability descriptions, not buried inside an unrelated subsection.

    Run `uv run pytest tests/unit/agents/test_content_agent_tools.py -x` — both tests GREEN.

    Lint: `uv run ruff check app/agents/content/agent.py --fix && uv run ruff format app/agents/content/agent.py && uv run ty check app/agents/content/agent.py`.

    Run a wider sanity check to confirm no regression of other agent tests:
    ```
    uv run pytest tests/unit/agents/ -x 2>&1 | tail -10
    ```

    Commit: `feat(108-03): wire SOCIAL_TOOLS directly into ContentCreationAgent + prompt update (HYGIENE-03)`.
  </behavior>
  <action>
    Implement RED tests first, run, then implement.

    **Edge case:** `create_content_agent()` reads from `os.environ` for the model config and may fail under test if env isn't set. Check whether existing tests in `tests/unit/agents/test_agent_factories.py` already invoke this; if they need monkeypatching to avoid network calls, mirror that pattern. If `get_model()` requires a `GOOGLE_API_KEY`, the test should `monkeypatch.setenv("GOOGLE_API_KEY", "test-key")` so the constructor returns a real Agent object without calling out.

    **Edge case for prompt insertion:** the prompt is shared across personas (persona blocks are appended after the base instruction). The DIRECT SOCIAL POSTING block lives in the BASE prompt, so it's seen by all personas. That's correct — Solopreneur, SME, Enterprise all benefit from direct posting capability.

    Linters as in 108-01.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/agents/test_content_agent_tools.py -x 2>&amp;1 | tail -20 &amp;&amp; uv run pytest tests/unit/agents/ -x --no-header -q 2>&amp;1 | tail -10</automated>
  </verify>
  <done>
    Both tests in `tests/unit/agents/test_content_agent_tools.py` GREEN. `app/agents/content/agent.py` imports `SOCIAL_TOOLS` and spreads it into `create_content_agent`'s tools list. `CONTENT_DIRECTOR_INSTRUCTION` has a `DIRECT SOCIAL POSTING` subsection naming the four tool functions and explaining when to delegate vs post directly. Marketing's `_SOCIAL_TOOLS_LIST` is unchanged (regression test passes). Existing `tests/unit/agents/` tests are NOT regressed. Ruff + ty clean. Commit lands.
  </done>
</task>

</tasks>

<verification>
End-to-end verification for plan 108-03:

```
uv run pytest tests/unit/agents/test_content_agent_tools.py -x 2>&1 | tail -10
uv run pytest tests/unit/agents/ -x --no-header -q 2>&1 | tail -10  # broader regression check
```

Both new tests GREEN. No existing agent test regressions.

Manual smoke (deferred to phase-level UAT): in `make playground`, ask ContentCreationAgent (or run via the chat with `agent: ContentCreationAgent` routing) to "post 'hello world' to Twitter" — verify it calls `publish_to_social` directly (no `transfer_to_agent` call to MarketingAgent in the trace).
</verification>

<success_criteria>
- `app/agents/content/agent.py` imports `SOCIAL_TOOLS` from `app.agents.tools.social`.
- `create_content_agent()`'s `tools` argument includes `*SOCIAL_TOOLS` (visible via grep).
- `CONTENT_DIRECTOR_INSTRUCTION` contains a `DIRECT SOCIAL POSTING` subsection naming all four tool functions and explaining the direct vs. delegated post boundary.
- `tests/unit/agents/test_content_agent_tools.py` exists with at least 2 tests:
  - `test_content_agent_has_social_tools` — asserts all 4 social tool names appear in the agent's tools.
  - `test_marketing_social_subagent_unchanged_regression` — asserts Marketing's `_SOCIAL_TOOLS_LIST` still contains the 4 SOCIAL_TOOLS functions.
- All existing `tests/unit/agents/` tests still pass.
- `uv run ruff check app/agents/content/agent.py` clean; `uv run ty check app/agents/content/agent.py` clean.
</success_criteria>

<output>
After completion, create `.planning/phases/108-hygiene-and-coverage/108-03-content-agent-social-wiring-SUMMARY.md` documenting:
- Exact line numbers of the import and the `*SOCIAL_TOOLS` spread in `create_content_agent`
- Where the DIRECT SOCIAL POSTING block was inserted in `CONTENT_DIRECTOR_INSTRUCTION`
- Test count: 2 new
- Confirmation that `_SOCIAL_TOOLS_LIST` in marketing/agent.py was untouched
- Any deviations from this plan
</output>
