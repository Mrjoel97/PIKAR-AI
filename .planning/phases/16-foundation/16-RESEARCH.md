# Phase 16: Foundation - Research

**Researched:** 2026-03-21
**Domain:** Stitch MCP subprocess singleton, Supabase schema + Storage, Gemini prompt enhancement
**Confidence:** HIGH for mcp SDK API (verified from installed source); HIGH for Supabase Storage (verified from installed source); HIGH for FastAPI lifespan pattern (verified from existing code); MEDIUM for Stitch MCP tool surface (sparse external docs)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUN-01 | Stitch MCP Server runs as a persistent singleton in FastAPI lifespan (Node.js subprocess, not per-request) | mcp 1.25.0 `stdio_client` + `ClientSession` API verified from installed package; lifespan pattern verified from `fast_api_app.py` |
| FOUN-02 | DB schema: app_projects, app_screens, screen_variants, design_systems, build_sessions tables | Schema DDL fully designed in ARCHITECTURE.md; migration file naming convention verified from existing migrations |
| FOUN-03 | Prompt enhancer transforms vague input to Stitch-optimized prompts using Gemini + design vocabulary | Gemini call pattern available via existing `google-genai` SDK; design mappings defined from stitch-skills research |
| FOUN-04 | Stitch signed URLs downloaded immediately and stored in Supabase Storage | Storage upload API verified from `storage3` installed package; download pattern verified from `brain_dump.py` |

</phase_requirements>

---

## Summary

Phase 16 lays four independent infrastructure pieces that every subsequent phase depends on. The pieces can be built in parallel waves: (1) the MCP subprocess singleton, (2) the DB schema migration, (3) the prompt enhancer, and (4) the asset persistence helper.

The most important discovery from this research is that the architecture document's `StitchMCPService.start()` pattern — which calls `.__aenter__()` manually on the `stdio_client` context manager — is subtly wrong for `mcp` 1.25.0. In this version `stdio_client` is an `@asynccontextmanager` that yields `(read_stream, write_stream)` directly, and `ClientSession` manages the receive loop via its own `__aenter__`/`__aexit__`. The correct singleton approach holds both context managers open with `anyio.CancelScope` or via an `anyio.create_task_group` running in a background task. The recommended pattern is an `anyio.Event` plus a background task that runs the two nested `async with` blocks for the lifetime of the FastAPI process.

The second key finding is that the existing sync Supabase client is used for storage operations throughout the project (see `brain_dump.py`). The pattern `get_service_client().storage.from_(bucket).upload(path, bytes, options)` followed by `.get_public_url(path)` is the correct approach. The `stitch-assets` bucket must be created in Supabase Storage before the service can upload to it.

**Primary recommendation:** Build the MCP service as an anyio background task that bridges into FastAPI's asyncio lifespan; never call `.__aenter__()` manually on `stdio_client`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp` | 1.25.0 (transitive via google-adk) | MCP client SDK — `ClientSession`, `StdioServerParameters`, `stdio_client` | Already in lockfile as transitive dep of google-adk; no new install needed |
| `anyio` | 4.12.0 (transitive) | Async primitives used internally by `mcp`; task groups, events | Already in lockfile; required by mcp internals |
| `google-genai` | >=0.2.0 (already in pyproject.toml) | Gemini API calls for prompt enhancement | Existing project dependency; same SDK used by all agents |
| `supabase` | 2.27.2 | DB inserts + Storage uploads | Already installed; `storage3` sync API verified |
| `httpx` | 0.28.1 (transitive) | Download Stitch temporary URLs | Already in lockfile |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio` | stdlib | Windows event loop policy | Only at startup guard for Windows dev |
| `anyio.from_thread` | stdlib in anyio | Bridge sync Supabase client calls from async context | Only if using async Supabase client; project uses sync client, so ThreadPoolExecutor approach applies |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| anyio background task for singleton | `asyncio.create_task` directly | anyio is what mcp's internals use; mixing event loop backends causes issues. Use anyio throughout. |
| Sync Supabase client in thread | Async Supabase client | Project uses sync client everywhere. Keep consistent. Thread executor is fine for one-shot upload calls. |
| Gemini Flash for prompt enhancement | Gemini Pro | Flash is cheaper and faster for structured output generation; Pro reserved for complex reasoning tasks |

**Installation:** No new packages required. `mcp` 1.25.0 is already a transitive dependency of `google-adk>=1.16.0`.

---

## Architecture Patterns

### Recommended Project Structure

New files for Phase 16:

```
app/
├── services/
│   ├── stitch_mcp.py          # StitchMCPService singleton + background task
│   └── prompt_enhancer.py     # Gemini-powered prompt expansion
├── agents/
│   └── tools/
│       └── app_builder.py     # ADK tool functions (generate_screen, persist_screen)
supabase/
└── migrations/
    └── 20260321400000_app_builder_schema.sql   # All 4 tables + RLS
```

Modified files:

```
app/fast_api_app.py            # Register StitchMCPService startup/shutdown in lifespan
app/mcp/tools/stitch.py        # Strip broken REST auth; delegate to StitchMCPService
app/mcp/agent_tools.py         # Remove mcp_stitch_landing_page sync wrapper
```

### Pattern 1: MCP Singleton via anyio Background Task

**What:** Run `stdio_client` + `ClientSession` in a persistent anyio task group that lives for the entire FastAPI process lifetime.

**When to use:** Any long-lived MCP subprocess that must not restart per-call.

**Critical API facts (verified from mcp 1.25.0 installed source):**

- `stdio_client(server: StdioServerParameters)` is an `@asynccontextmanager` that yields `(read_stream, write_stream)` — it is NOT a class and has no `.__aenter__()` method you can call manually.
- `ClientSession(read_stream, write_stream)` IS an async context manager — `__aenter__` starts the receive loop task group; `__aexit__` cancels it.
- `ClientSession.call_tool(name, arguments)` returns `types.CallToolResult` (not `dict`). The content is in `.content` which is a list of `types.TextContent` items.
- `StdioServerParameters` fields: `command` (str), `args` (list[str]), `env` (dict[str,str] | None), `cwd` (str | Path | None).

**Correct singleton pattern:**

```python
# app/services/stitch_mcp.py
import asyncio
import logging
import os
import sys
from typing import Any

import anyio
from anyio.abc import TaskGroup
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.types import CallToolResult

logger = logging.getLogger(__name__)


class StitchMCPService:
    """Singleton owning the Stitch MCP subprocess for the FastAPI process lifetime.

    Uses an anyio background task to keep stdio_client + ClientSession alive.
    Individual tool calls serialize via asyncio.Lock.
    """

    def __init__(self) -> None:
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()
        self._ready = anyio.Event()
        self._tg: TaskGroup | None = None

    async def start(self) -> None:
        """Start background task that holds the MCP session open."""
        # Run as a fire-and-forget anyio task; the task keeps the
        # stdio_client context manager alive until stop() is called.
        asyncio.get_event_loop().create_task(self._run())
        await self._ready.wait()  # block until session is initialized

    async def _run(self) -> None:
        """Background coroutine — holds stdio_client + ClientSession open."""
        params = StdioServerParameters(
            command="npx",
            args=["@_davideast/stitch-mcp", "proxy"],
            env={**os.environ, "STITCH_API_KEY": os.environ["STITCH_API_KEY"]},
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                self._session = session
                self._ready.set()
                # Hang here until cancelled (FastAPI shutdown)
                await anyio.sleep_forever()

    async def stop(self) -> None:
        """Signal shutdown — called from FastAPI lifespan shutdown."""
        # Cancelling the task that holds the context managers causes them to exit.
        if hasattr(self, "_task") and self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        """Call a Stitch MCP tool. Serialized via lock; session is shared."""
        if self._session is None:
            raise RuntimeError("StitchMCPService not initialized")
        async with self._lock:
            return await self._session.call_tool(name, arguments)


_stitch_service: StitchMCPService | None = None


def get_stitch_service() -> StitchMCPService:
    """Dependency injection accessor."""
    if _stitch_service is None:
        raise RuntimeError("StitchMCPService not initialized — lifespan not run")
    return _stitch_service
```

**Important:** The `_run()` coroutine must hold both context managers open. The `anyio.sleep_forever()` at the end is what keeps them from exiting. When the asyncio task is cancelled (at shutdown), the `async with` cleanup runs automatically.

**Lifespan registration:**

```python
# In fast_api_app.py, inside the existing lifespan() context manager:

@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    # ... existing Redis prewarm code ...

    # Start Stitch MCP singleton
    global _stitch_service
    if not BYPASS_IMPORT and os.environ.get("STITCH_API_KEY"):
        from app.services.stitch_mcp import StitchMCPService, _stitch_service as _svc
        import app.services.stitch_mcp as _stitch_module
        _stitch_module._stitch_service = StitchMCPService()
        _stitch_task = asyncio.create_task(
            _stitch_module._stitch_service._run()
        )
        await _stitch_module._stitch_service._ready.wait()
    else:
        _stitch_task = None

    # ... existing A2A init code ...
    yield

    # Shutdown
    if _stitch_task and not _stitch_task.done():
        _stitch_task.cancel()
        try:
            await _stitch_task
        except asyncio.CancelledError:
            pass
```

### Pattern 2: Windows Event Loop Policy Guard

**What:** Set `WindowsProactorEventLoopPolicy` at module top of `fast_api_app.py` before Uvicorn configures the loop.

**When to use:** Any time `StitchMCPService` is used on Windows dev. Production (Cloud Run / Docker on Windows) is unaffected.

```python
# At the very top of app/fast_api_app.py, before any asyncio usage:
import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

**Dev command for Windows:** Add `make local-backend-stitch` target that runs `uvicorn` without `--reload`.

### Pattern 3: Immediate Asset Download and Supabase Storage Upload

**What:** Within the same tool call that generates a screen, download the temporary URL and upload to Supabase Storage. Return the permanent public URL.

**Verified API from installed `storage3` 0.x (supabase 2.27.2 includes storage3):**

```python
# Sync Supabase client pattern — matches brain_dump.py project pattern
import httpx
from app.services.supabase_client import get_service_client

async def _download_and_persist(
    temp_url: str,
    storage_path: str,       # e.g. "stitch-assets/user_id/project_id/screen.html"
    content_type: str,
) -> str:
    """Download a temporary Stitch URL and store permanently. Returns public URL."""
    # Download — use async httpx since we're in an async context
    async with httpx.AsyncClient() as client:
        resp = await client.get(temp_url, follow_redirects=True, timeout=30.0)
        resp.raise_for_status()
        file_bytes = resp.content

    # Upload — sync Supabase Storage client in thread (matches project pattern)
    supabase = get_service_client()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: supabase.storage.from_("stitch-assets").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        ),
    )
    # Return permanent public URL (bucket must be public)
    return supabase.storage.from_("stitch-assets").get_public_url(storage_path)
```

**Note:** `get_public_url` returns a string directly (not a response object). The bucket `stitch-assets` must be set to public in Supabase Storage dashboard or via SQL policy.

### Pattern 4: Gemini Flash Prompt Enhancement

**What:** Call Gemini Flash (cheap, fast) to expand a vague user description into a structured Stitch prompt. Return as a plain string or structured dict.

**When to use:** Every initial screen generation call. Skip for iteration prompts.

```python
# app/services/prompt_enhancer.py
import logging
from google import genai
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

DESIGN_VOCABULARY = {
    "bakery": {
        "colors": ["#F5E6D3 (warm cream)", "#8B4513 (saddle brown)", "#D2691E (chocolate)"],
        "typography": "Playfair Display headings, Lato body",
        "mood": "artisan, warm, inviting",
        "sections": ["hero with bread/pastry photography", "featured products grid",
                     "about/story section", "hours and location with Google Maps"],
    },
    "saas": {
        "colors": ["#6366F1 (indigo)", "#FFFFFF (white)", "#F9FAFB (gray-50)"],
        "typography": "Inter headings and body",
        "mood": "professional, modern, trustworthy",
        "sections": ["hero with product screenshot", "feature highlights",
                     "social proof / testimonials", "pricing table", "CTA"],
    },
    "restaurant": {
        "colors": ["#1C1C1E (near black)", "#C9A96E (gold)", "#FFFFFF (white)"],
        "typography": "Cormorant Garamond headings, Raleway body",
        "mood": "elegant, upscale, appetizing",
        "sections": ["full-bleed hero", "menu preview", "reservations", "location"],
    },
    "fitness": {
        "colors": ["#FF6B35 (orange)", "#1A1A2E (dark navy)", "#FFFFFF"],
        "typography": "Montserrat bold headings, Open Sans body",
        "mood": "energetic, motivating, bold",
        "sections": ["hero with action photography", "class schedule", "trainers", "pricing"],
    },
}

ENHANCEMENT_SYSTEM_PROMPT = """You are a UI design specialist who converts vague web page descriptions
into structured specifications for an AI design tool (Google Stitch).

Output a detailed specification in this exact format:
CONCEPT: [one-sentence summary]
VISUAL_STYLE: [adjectives: modern/minimal/bold/warm/elegant/playful]
COLOR_PALETTE: [3 hex codes with names, e.g. #F5E6D3 warm cream]
TYPOGRAPHY: [heading font + body font pairing]
SECTIONS: [comma-separated list of page sections in order]
IMAGERY: [photography/illustration style description]
TONE: [brand voice: professional/friendly/luxurious/energetic]
TARGET_AUDIENCE: [who this is for]

Be specific. Include actual hex codes, specific font names, concrete section names.
Do not use generic language like "nice colors" or "good fonts".
"""


async def enhance_prompt(description: str, domain_hint: str | None = None) -> str:
    """Expand vague user description into a Stitch-optimized specification.

    Args:
        description: Raw user input, e.g. "bakery website"
        domain_hint: Optional category to pull design vocabulary, e.g. "bakery"

    Returns:
        Structured specification string ready to pass to Stitch generate_screen_from_text
    """
    # Pre-load domain vocabulary if available
    vocab_context = ""
    if domain_hint and domain_hint.lower() in DESIGN_VOCABULARY:
        vocab = DESIGN_VOCABULARY[domain_hint.lower()]
        vocab_context = (
            f"\n\nDesign vocabulary for {domain_hint}: "
            f"colors={vocab['colors']}, typography={vocab['typography']}, "
            f"typical sections={vocab['sections']}"
        )

    client = genai.Client()
    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"{description}{vocab_context}",
        config=genai_types.GenerateContentConfig(
            system_instruction=ENHANCEMENT_SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=500,
        ),
    )
    return response.text
```

### Pattern 5: CallToolResult Content Extraction

**What:** `ClientSession.call_tool()` returns `types.CallToolResult`, not a plain dict. Content is in `.content` as a list of typed content items.

```python
from mcp.types import CallToolResult, TextContent

result: CallToolResult = await session.call_tool("generate_screen_from_text", {
    "prompt": enhanced_prompt,
    "projectId": project_id,
    "deviceType": "DESKTOP",
})

if result.isError:
    raise RuntimeError(f"Stitch tool error: {result.content}")

# Extract text payload — Stitch returns JSON in a TextContent item
text_item = next(item for item in result.content if isinstance(item, TextContent))
import json
data = json.loads(text_item.text)  # {"screenId": "...", "projectId": "...", ...}
```

### Anti-Patterns to Avoid

- **Calling `stdio_client().__aenter__()`**: `stdio_client` is an `@asynccontextmanager` function, not a class. Never call `.__aenter__()` on it manually — use it with `async with stdio_client(...) as (r, w)`.
- **Returning `CallToolResult.content` directly as a dict**: `content` is a list of typed content objects (TextContent, ImageContent). Parse with `json.loads(item.text)`.
- **Using `asyncio.WindowsProactorEventLoopPolicy` on Linux**: The guard must be `if sys.platform == "win32"` — the policy class doesn't exist on Linux.
- **Running `make local-backend` with `--reload` on Windows**: Uvicorn's reload mode resets the event loop policy. Use `--no-reload` for Stitch MCP development.
- **Returning Stitch signed URLs to frontend or DB**: Download immediately. Signed URLs expire in minutes.
- **Uploading HTML as `text/html` without `upsert: true`**: Without upsert, re-generating the same screen fails with a conflict error.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP stdio subprocess management | Custom subprocess + pipe reader | `mcp.client.stdio.stdio_client` + `mcp.ClientSession` | Already handles JSONRPC framing, process termination trees, Windows job objects |
| Node.js process cleanup on crash | Manual SIGKILL logic | mcp 1.25.0's `_terminate_process_tree` + anyio cancel scope | Platform-specific (POSIX killpg vs Windows Job Object) — handled internally |
| Stitch signed URL download | Custom retry logic | `httpx.AsyncClient().get()` with `follow_redirects=True` | Signed URLs may redirect; httpx handles redirects transparently |
| Supabase Storage public URL construction | String concatenation of Supabase URL + path | `supabase.storage.from_(bucket).get_public_url(path)` | Handles URL encoding, bucket region, CDN prefix correctly |
| Design vocabulary for prompts | Training Gemini on design specs | `DESIGN_VOCABULARY` dict + Gemini Flash expansion | Fast, cheap, deterministic for known domains; Gemini handles unknown domains gracefully |

---

## Common Pitfalls

### Pitfall 1: anyio vs asyncio Event

**What goes wrong:** `anyio.Event()` is created but `.wait()` is called from a plain asyncio context without anyio's task group running.

**Why it happens:** `anyio.Event` requires an anyio backend to be active. FastAPI (via Uvicorn) runs asyncio; anyio detects the backend automatically when called from inside an anyio task group. Calling `anyio.Event().wait()` from plain asyncio works because anyio auto-detects the asyncio backend. However, creating the Event before the backend is active can cause issues.

**How to avoid:** Create `anyio.Event()` inside the `__init__` of StitchMCPService (at import time, no backend required). Call `.set()` and `.wait()` only after the asyncio event loop is running (inside an async function).

### Pitfall 2: ClientSession Receive Loop Dies Silently

**What goes wrong:** The background task holding `ClientSession` exits due to an unhandled exception. Subsequent `call_tool()` calls hang or raise `ClosedResourceError`.

**Why it happens:** If Stitch MCP server process crashes or the Node.js process exits, the `ClientSession` receive loop gets an exception on the read stream. If nothing re-raises this to the parent task, the session appears "alive" but is broken.

**How to avoid:** Wrap `_run()` with a try/except that logs and clears `self._session` on failure. Implement a health check: if `call_tool()` fails with `ClosedResourceError`, mark service unhealthy and log a clear error.

**Warning signs:** `ClosedResourceError` from anyio; `RuntimeError: StitchMCPService not initialized` after startup; Node.js process not visible in process list.

### Pitfall 3: MCP Tool Names Are camelCase

**What goes wrong:** Calling `session.call_tool("generate_screen_from_text", ...)` fails with "tool not found."

**Why it happens:** Stitch MCP tool names may use camelCase or snake_case. The architecture research shows names like `generate_screen_from_text` but the actual server may expose `generateScreenFromText`.

**How to avoid:** After session initialization, call `await session.list_tools()` and log the actual tool names. Write a startup validation that confirms expected tools are present.

### Pitfall 4: Supabase Storage Bucket Must Pre-Exist

**What goes wrong:** `supabase.storage.from_("stitch-assets").upload(...)` raises a 404 error.

**Why it happens:** Unlike databases, Supabase Storage buckets are not created by SQL migrations — they require an API call or manual creation in the Supabase dashboard.

**How to avoid:** Create the `stitch-assets` bucket as part of Wave 0 setup. Add it to the migration SQL using Supabase's internal function, or document it as a manual setup step with clear instructions.

```sql
-- Add to the migration file for bucket creation:
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'stitch-assets',
    'stitch-assets',
    true,           -- public bucket for permanent preview URLs
    52428800,       -- 50MB limit per file
    ARRAY['text/html', 'image/png', 'image/jpeg', 'image/webp', 'application/zip']
)
ON CONFLICT (id) DO NOTHING;
```

### Pitfall 5: STITCH_API_KEY Not Passed to Child Process

**What goes wrong:** The Node.js subprocess starts but all Stitch tool calls return auth errors.

**Why it happens:** `StdioServerParameters.env` replaces the default environment (only safe inherited vars) rather than extending it. If `STITCH_API_KEY` is not explicitly in `env`, the child process doesn't get it.

**How to avoid:** Always spread the current process environment into the `env` dict:
```python
env={**os.environ, "STITCH_API_KEY": os.environ["STITCH_API_KEY"]}
```
Or use `get_default_environment()` from mcp.client.stdio as the base and add the key on top.

---

## Code Examples

Verified patterns from installed source code:

### mcp ClientSession context manager usage

```python
# Source: .venv/Lib/site-packages/mcp/shared/session.py lines 221-238
# Source: .venv/Lib/site-packages/mcp/client/session.py lines 112-127
from mcp import ClientSession, StdioServerParameters, stdio_client

async with stdio_client(params) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        result = await session.call_tool("tool_name", {"arg": "value"})
        # result.isError: bool
        # result.content: list[TextContent | ImageContent | ...]
```

### Supabase Storage upload (matches brain_dump.py project pattern)

```python
# Source: app/agents/tools/brain_dump.py lines 271-276
from app.services.supabase_client import get_service_client

supabase = get_service_client()
supabase.storage.from_("stitch-assets").upload(
    path="user_id/project_id/screen_id.html",
    file=html_bytes,
    file_options={"content-type": "text/html", "upsert": "true"},
)
public_url = supabase.storage.from_("stitch-assets").get_public_url(
    "user_id/project_id/screen_id.html"
)
```

### Existing lifespan extension point

```python
# Source: app/fast_api_app.py lines 307-338
# The lifespan() function already exists and follows this structure:
@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    if not BYPASS_IMPORT:
        try:
            from app.services.cache import get_cache_service
            cache = get_cache_service()
            await cache.prewarm()
        except Exception as e:
            logger.warning(f"Redis pre-warm failed (non-fatal): {e}")
    # ... A2A init ...
    yield
    # Shutdown code goes here (after yield)
```

### StdioServerParameters — exact field names

```python
# Source: .venv/Lib/site-packages/mcp/client/stdio/__init__.py lines 72-103
from mcp.client.stdio import StdioServerParameters  # also exported from mcp directly

params = StdioServerParameters(
    command="npx",                              # str: executable
    args=["@_davideast/stitch-mcp", "proxy"],   # list[str]
    env={"STITCH_API_KEY": "..."},              # dict[str,str] | None
    cwd=None,                                   # str | Path | None
    encoding="utf-8",                           # default
    encoding_error_handler="strict",            # default
)
```

### Windows platform guard

```python
# Source: .venv/Lib/site-packages/mcp/client/stdio/__init__.py lines 229-232
# mcp itself does platform detection internally for subprocess creation
# (create_windows_process vs anyio.open_process). The guard you need is only
# for Uvicorn's event loop policy:
import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

---

## DB Schema (Verified from ARCHITECTURE.md — all DDL is correct)

The schema in ARCHITECTURE.md is production-ready. Key notes for migration file:

- Use filename: `20260321400000_app_builder_schema.sql` (next after `20260321300000_admin_panel_foundation.sql`)
- All 4 tables: `app_projects`, `design_systems`, `app_screens`, `screen_variants`
- Include `build_sessions` table per FOUN-02 requirement (missing from ARCHITECTURE.md draft — add it)
- Include Storage bucket INSERT (see Pitfall 4 above)
- Follow existing migration style: `CREATE TABLE IF NOT EXISTS`, schema-prefix `public.`, RLS enabled, policies created immediately after table

**build_sessions table (missing from ARCHITECTURE.md, required by FOUN-02):**

```sql
CREATE TABLE public.build_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES public.app_projects(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    stage           TEXT NOT NULL DEFAULT 'questioning',
                                        -- questioning | research | brief | build | verify | ship
    stage_data      JSONB DEFAULT '{}', -- per-stage state (answers, selections, etc.)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.build_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their build sessions"
  ON public.build_sessions FOR ALL USING (auth.uid() = user_id);
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `mcp` 0.x: `ClientSession` used as a bare class | `mcp` 1.x: `ClientSession` is an async context manager (uses anyio task group in `__aenter__`) | mcp 1.0 release | Must use `async with ClientSession(...)` — not just `ClientSession(read, write)` then call methods |
| Per-request MCP subprocess (old agent_tools.py pattern) | Persistent singleton subprocess | This phase | Eliminates 2s Node.js cold start per Stitch call |
| REST API auth for Stitch | MCP protocol (stdio subprocess) | Architecture decision | REST auth is broken ("API keys not supported"); MCP is the only working path |

**Deprecated/outdated:**

- `app/mcp/tools/stitch.py` REST client: The entire `generate_with_stitch()` method using `httpx.post()` to `stitch.withgoogle.com/api` is broken. The REST endpoint does not accept API keys. This entire file's Stitch-calling code is dead code and must be replaced.
- `mcp_stitch_landing_page` sync wrapper in `agent_tools.py`: Incompatible with persistent MCP session (spawns new process per call). Remove entirely.

---

## Open Questions

1. **Stitch MCP actual tool names**
   - What we know: Architecture research lists `generate_screen_from_text`, `edit_screens`, `list_projects`, etc. based on external docs.
   - What's unclear: Whether actual names are `snake_case` or `camelCase` — the sparse stitch-mcp docs don't confirm.
   - Recommendation: After starting the singleton in Wave 1, call `await session.list_tools()` and log the result. Write a startup assertion.

2. **Stitch MCP tool argument schema**
   - What we know: `projectId`, `screenId`, `deviceType` are referenced in architecture docs.
   - What's unclear: Exact required vs optional fields; whether `deviceType` accepts `"desktop"` or `"DESKTOP"`.
   - Recommendation: After Wave 1 succeeds, add a smoke test that calls each tool with minimal args and logs the response shape.

3. **Stitch-assets bucket public access in Supabase**
   - What we know: The SQL `INSERT INTO storage.buckets` approach exists but may require superuser permissions in hosted Supabase.
   - What's unclear: Whether `storage.buckets` is writable via migrations in the hosted Supabase project.
   - Recommendation: Attempt the SQL approach in the migration. If it fails, document the manual bucket creation step in the migration file header as a comment.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 + pytest-asyncio 0.23.8 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/unit/test_stitch_foundation.py -x` |
| Full suite command | `uv run pytest tests/ --ignore=tests/load_test -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUN-01 | `StitchMCPService.start()` initializes session without spawning new process per call | unit (mock subprocess) | `pytest tests/unit/test_stitch_foundation.py::test_service_singleton -x` | ❌ Wave 0 |
| FOUN-01 | `call_tool()` raises `RuntimeError` if called before `start()` | unit | `pytest tests/unit/test_stitch_foundation.py::test_call_tool_before_start -x` | ❌ Wave 0 |
| FOUN-02 | Migration applies cleanly: all 5 tables exist, RLS enabled | integration (local Supabase) | `pytest tests/integration/test_app_builder_schema.py -x` | ❌ Wave 0 |
| FOUN-02 | Test project + screen row can be inserted and read back | integration | `pytest tests/integration/test_app_builder_schema.py::test_round_trip -x` | ❌ Wave 0 |
| FOUN-03 | `enhance_prompt("bakery website")` returns string containing hex color, font name, and section list | unit (mock Gemini) | `pytest tests/unit/test_stitch_foundation.py::test_prompt_enhancer -x` | ❌ Wave 0 |
| FOUN-04 | `_download_and_persist()` downloads bytes from URL and calls storage upload | unit (mock httpx + mock storage) | `pytest tests/unit/test_stitch_foundation.py::test_asset_persistence -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/unit/test_stitch_foundation.py -x`
- **Per wave merge:** `uv run pytest tests/unit/ tests/integration/test_app_builder_schema.py -x`
- **Phase gate:** Full unit suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_stitch_foundation.py` — covers FOUN-01, FOUN-03, FOUN-04
- [ ] `tests/integration/test_app_builder_schema.py` — covers FOUN-02
- [ ] `tests/unit/conftest.py` already exists — may need Gemini mock fixtures added
- [ ] Stitch-assets Storage bucket creation — manual or via migration

---

## Sources

### Primary (HIGH confidence)

- `.venv/Lib/site-packages/mcp/client/stdio/__init__.py` — `stdio_client` signature, `StdioServerParameters` fields, Windows process handling
- `.venv/Lib/site-packages/mcp/client/session.py` — `ClientSession.__init__`, `call_tool()` signature, return type `CallToolResult`
- `.venv/Lib/site-packages/mcp/shared/session.py` — `BaseSession.__aenter__/__aexit__`, anyio task group lifecycle
- `.venv/Lib/site-packages/mcp/__init__.py` — confirmed public API exports
- `.venv/Lib/site-packages/storage3/_sync/file_api.py` — `upload()` and `get_public_url()` signatures
- `app/agents/tools/brain_dump.py` lines 271-276 — exact Storage upload pattern used in this project
- `app/fast_api_app.py` lines 307-338 — existing lifespan structure to extend
- `uv.lock` — confirmed mcp 1.25.0, anyio 4.12.0, supabase 2.27.2, httpx 0.28.1 all present

### Secondary (MEDIUM confidence)

- `.planning/research-v2/ARCHITECTURE.md` — DB schema DDL (produced by earlier architecture research); tool call patterns (verified against mcp source except for Stitch tool names which remain unverified)
- stitch-mcp external docs (referenced in ARCHITECTURE.md) — tool catalog (MEDIUM — sparse, tool name casing unconfirmed)

### Tertiary (LOW confidence)

- Stitch MCP tool argument schemas (e.g., `deviceType` accepted values) — referenced in architecture docs but not independently verified; must be confirmed at runtime via `list_tools()`

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all packages verified from installed venv source
- mcp API (stdio_client, ClientSession): HIGH — read actual installed source, not docs
- Architecture patterns: HIGH for MCP lifecycle; MEDIUM for Stitch tool surface
- Supabase Storage: HIGH — verified from installed storage3 source + project usage
- Pitfalls: HIGH — derived from reading actual code behavior

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (mcp 1.x SDK — stable; Stitch MCP tool surface may change without notice)

**Critical correction from prior architecture research:**
The ARCHITECTURE.md `StitchMCPService.start()` pattern that calls `self._stdio_cm.__aenter__()` manually is incorrect for mcp 1.25.0. `stdio_client` is an `@asynccontextmanager` function yielding `(read_stream, write_stream)`, not a class with `__aenter__`. The correct singleton pattern uses an asyncio background task holding both `async with stdio_client(...)` and `async with ClientSession(...)` open for the process lifetime.
