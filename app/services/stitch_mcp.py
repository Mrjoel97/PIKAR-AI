# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Stitch MCP Service — persistent singleton managing the Stitch Node.js subprocess.

Holds stdio_client + ClientSession alive for the FastAPI process lifetime via
an asyncio background task. Individual tool calls serialize through a Lock.
"""
import asyncio
import base64
import hashlib
import html
import json
import logging
import os
import time
from typing import Any, NamedTuple
from uuid import uuid4

import anyio

logger = logging.getLogger(__name__)

# Module-level singleton
_stitch_service: "StitchMCPService | None" = None
_stitch_task: "asyncio.Task[None] | None" = None


def _as_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def should_use_mock_stitch_service() -> bool:
    """Return True when app-builder should use local mock previews for testing."""
    return _as_bool(os.getenv("APP_BUILDER_USE_MOCK_STITCH"))


def _to_data_url(content_type: str, body: str) -> str:
    encoded = base64.b64encode(body.encode("utf-8")).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


class StitchMCPService:
    """Singleton owning the Stitch MCP subprocess for the FastAPI process lifetime."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialise the service. If api_key is None, _run() falls back to env."""
        self._api_key = api_key
        self._session = None
        self._lock = asyncio.Lock()
        self._ready = anyio.Event()  # anyio — consistent with mcp library internals
        self._healthy = True

    async def _run(self) -> None:
        """Background coroutine — holds stdio_client + ClientSession open until cancelled."""
        from mcp import ClientSession, StdioServerParameters, stdio_client

        stitch_key = self._api_key or os.environ.get("STITCH_API_KEY", "")
        params = StdioServerParameters(
            command="npx",
            args=["@_davideast/stitch-mcp", "proxy"],
            env={**os.environ, "STITCH_API_KEY": stitch_key},
            cwd=None,
        )
        try:
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    # Log available tools so we know exact names (camelCase vs snake_case)
                    try:
                        tools = await session.list_tools()
                        logger.info(
                            "StitchMCP tools available: %s",
                            [t.name for t in tools.tools],
                        )
                    except Exception as e:
                        logger.warning("Could not list Stitch tools: %s", e)
                    self._session = session
                    self._healthy = True
                    self._ready.set()
                    logger.info("StitchMCPService ready — subprocess alive")
                    # Hang here until asyncio task is cancelled at shutdown
                    await anyio.sleep_forever()
        except asyncio.CancelledError:
            logger.info("StitchMCPService shutting down (task cancelled)")
            raise
        except Exception as e:
            logger.error("StitchMCPService _run() failed: %s", e)
            self._healthy = False
            self._session = None
            # Don't re-raise — let the service degrade gracefully

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a Stitch MCP tool by name. Serialized via Lock.

        Returns parsed JSON dict from the TextContent response.
        Raises RuntimeError if session is not initialized or the call errors.
        """
        from mcp.types import TextContent

        if self._session is None or not self._healthy:
            raise RuntimeError(
                "StitchMCPService not available — subprocess may have crashed"
            )
        async with self._lock:
            result = await self._session.call_tool(name, arguments)

        if result.isError:
            raise RuntimeError(f"Stitch tool '{name}' returned error: {result.content}")

        # Extract JSON from first TextContent item
        text_item = next(
            (item for item in result.content if isinstance(item, TextContent)), None
        )
        if text_item is None:
            raise RuntimeError(f"Stitch tool '{name}' returned no TextContent")

        try:
            return json.loads(text_item.text)
        except json.JSONDecodeError:
            # Return raw text wrapped in dict if not JSON
            return {"raw": text_item.text}

    def is_ready(self) -> bool:
        """Return True if the MCP session is initialized and healthy."""
        return self._session is not None and self._healthy


class MockStitchMCPService(StitchMCPService):
    """Testing-only Stitch replacement that returns local data-URL previews."""

    def __init__(self) -> None:
        super().__init__(api_key=None)
        self._projects: dict[str, dict[str, Any]] = {}

    async def _run(self) -> None:
        self._session = self
        self._healthy = True
        self._ready.set()
        logger.info("MockStitchMCPService ready — using local preview assets")
        await anyio.sleep_forever()

    async def list_tools(self):  # pragma: no cover - tiny adapter for existing callers
        from types import SimpleNamespace

        return SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name="create_project",
                    description="Create a local mock app-builder project.",
                ),
                SimpleNamespace(
                    name="generate_screen_from_text",
                    description="Generate a mock screen preview from a prompt.",
                ),
                SimpleNamespace(
                    name="edit_screens",
                    description="Create an edited mock screen preview.",
                ),
                SimpleNamespace(
                    name="get_screen",
                    description="Fetch an existing mock screen preview.",
                ),
            ]
        )

    def _render_screen_payload(
        self,
        *,
        project_id: str,
        screen_id: str,
        prompt: str,
        device_type: str,
        project_name: str,
    ) -> dict[str, Any]:
        prompt_text = (prompt or "Untitled screen").strip()
        prompt_preview = html.escape(prompt_text[:280] or "Untitled screen")
        device_label = html.escape((device_type or "DESKTOP").upper())
        project_label = html.escape(project_name or "Untitled app")
        accent = {
            "MOBILE": "#0f766e",
            "TABLET": "#1d4ed8",
        }.get(device_label, "#7c3aed")

        html_doc = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>{project_label} Mock Preview</title>
    <style>
      :root {{
        color-scheme: light;
        --accent: {accent};
        --ink: #0f172a;
        --muted: #475569;
        --surface: #ffffff;
        --bg-a: #f8fafc;
        --bg-b: #e2e8f0;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        font-family: "Segoe UI", system-ui, sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(124, 58, 237, 0.18), transparent 34%),
          linear-gradient(135deg, var(--bg-a), var(--bg-b));
        display: grid;
        place-items: center;
      }}
      main {{
        width: min(960px, calc(100vw - 48px));
        padding: 32px;
        border-radius: 28px;
        background: rgba(255,255,255,0.88);
        border: 1px solid rgba(148,163,184,0.28);
        box-shadow: 0 28px 80px rgba(15, 23, 42, 0.14);
        backdrop-filter: blur(10px);
      }}
      .eyebrow {{
        display: inline-flex;
        gap: 8px;
        align-items: center;
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(255,255,255,0.9);
        color: var(--muted);
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }}
      h1 {{
        margin: 18px 0 10px;
        font-size: clamp(2rem, 4vw, 3.6rem);
        line-height: 1;
      }}
      p {{
        margin: 0;
        max-width: 60ch;
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.7;
      }}
      .cards {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;
        margin-top: 28px;
      }}
      .card {{
        padding: 18px;
        border-radius: 20px;
        background: var(--surface);
        border: 1px solid rgba(148,163,184,0.22);
      }}
      .card strong {{
        display: block;
        margin-bottom: 8px;
      }}
      .cta {{
        display: inline-flex;
        margin-top: 24px;
        padding: 12px 18px;
        border-radius: 14px;
        background: var(--accent);
        color: white;
        font-weight: 600;
      }}
    </style>
  </head>
  <body>
    <main>
      <div class="eyebrow">
        <span>Mock Stitch Preview</span>
        <span>{device_label}</span>
      </div>
      <h1>{project_label}</h1>
      <p>{prompt_preview}</p>
      <section class="cards">
        <article class="card">
          <strong>Project</strong>
          <span>{html.escape(project_id)}</span>
        </article>
        <article class="card">
          <strong>Screen</strong>
          <span>{html.escape(screen_id)}</span>
        </article>
        <article class="card">
          <strong>Status</strong>
          <span>Generated locally for testing</span>
        </article>
      </section>
      <div class="cta">Temporary app-builder sandbox enabled</div>
    </main>
  </body>
</html>"""

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="960" viewBox="0 0 1440 960">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f8fafc" />
      <stop offset="100%" stop-color="#e2e8f0" />
    </linearGradient>
  </defs>
  <rect width="1440" height="960" fill="url(#bg)" />
  <rect x="88" y="84" width="1264" height="792" rx="40" fill="#ffffff" />
  <rect x="132" y="136" width="240" height="42" rx="21" fill="{accent}" opacity="0.12" />
  <text x="156" y="164" font-size="24" fill="{accent}" font-family="Segoe UI, Arial, sans-serif">Mock Stitch Preview</text>
  <text x="132" y="262" font-size="66" fill="#0f172a" font-family="Segoe UI, Arial, sans-serif">{project_label}</text>
  <foreignObject x="132" y="304" width="1040" height="220">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Segoe UI, Arial, sans-serif;color:#475569;font-size:30px;line-height:1.45;">
      {prompt_preview}
    </div>
  </foreignObject>
  <rect x="132" y="592" width="280" height="176" rx="26" fill="#f8fafc" stroke="#cbd5e1" />
  <rect x="446" y="592" width="280" height="176" rx="26" fill="#f8fafc" stroke="#cbd5e1" />
  <rect x="760" y="592" width="280" height="176" rx="26" fill="#f8fafc" stroke="#cbd5e1" />
  <text x="164" y="646" font-size="24" fill="#0f172a" font-family="Segoe UI, Arial, sans-serif">Device</text>
  <text x="164" y="692" font-size="34" fill="{accent}" font-family="Segoe UI, Arial, sans-serif">{device_label}</text>
  <text x="478" y="646" font-size="24" fill="#0f172a" font-family="Segoe UI, Arial, sans-serif">Project</text>
  <text x="478" y="692" font-size="28" fill="#334155" font-family="Segoe UI, Arial, sans-serif">{project_label}</text>
  <text x="792" y="646" font-size="24" fill="#0f172a" font-family="Segoe UI, Arial, sans-serif">Screen</text>
  <text x="792" y="692" font-size="28" fill="#334155" font-family="Segoe UI, Arial, sans-serif">{html.escape(screen_id)}</text>
</svg>"""

        return {
            "screenId": screen_id,
            "screen_id": screen_id,
            "projectId": project_id,
            "html_url": _to_data_url("text/html", html_doc),
            "screenshot_url": _to_data_url("image/svg+xml", svg),
            "mock": True,
        }

    def _get_project(self, project_id: str) -> dict[str, Any]:
        project = self._projects.get(project_id)
        if project is None:
            raise RuntimeError(f"Mock Stitch project not found: {project_id}")
        return project

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "create_project":
            project_id = f"mock-project-{uuid4().hex[:12]}"
            project_name = str(arguments.get("name") or "Untitled app")
            self._projects[project_id] = {"name": project_name, "screens": {}}
            return {"id": project_id, "projectId": project_id, "name": project_name}

        if name in {"generate_screen_from_text", "edit_screens"}:
            project_id = str(arguments.get("projectId") or "").strip()
            if not project_id:
                raise RuntimeError("Mock Stitch requires projectId")
            project = self._get_project(project_id)
            device_type = str(arguments.get("deviceType") or "DESKTOP")
            prompt = str(arguments.get("prompt") or "Untitled screen")
            screen_id = f"mock-screen-{uuid4().hex[:12]}"
            payload = self._render_screen_payload(
                project_id=project_id,
                screen_id=screen_id,
                prompt=prompt,
                device_type=device_type,
                project_name=project["name"],
            )
            project["screens"][screen_id] = payload
            return payload

        if name == "get_screen":
            project_id = str(arguments.get("projectId") or "").strip()
            screen_id = str(arguments.get("screenId") or "").strip()
            if not project_id or not screen_id:
                raise RuntimeError("Mock Stitch get_screen requires projectId and screenId")
            project = self._get_project(project_id)
            payload = project["screens"].get(screen_id)
            if payload is None:
                raise RuntimeError(f"Mock Stitch screen not found: {screen_id}")
            return payload

        raise RuntimeError(f"Mock Stitch does not implement tool '{name}'")


class _ResolvedKey(NamedTuple):
    """Result of StitchPool._resolve_key.

    Carries which pool entry to use, the API key to spawn with (None for mock),
    and a fingerprint for rotation detection.
    """

    pool_key: str
    api_key: str | None
    fingerprint: str


class StitchPool:
    """Per-user pool of StitchMCPService subprocesses.

    Resolution order: user-saved key → env key → mock → error.
    Lazy spawn under a single lock; idle eviction at 10-min TTL.
    """

    POOL_KEY_ENV = "__env_default__"
    POOL_KEY_MOCK = "__mock__"

    def __init__(self, evict_ttl_seconds: int = 600) -> None:
        self._services: dict[str, StitchMCPService] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._fingerprints: dict[str, str] = {}
        self._last_used: dict[str, float] = {}
        self._spawn_lock = asyncio.Lock()
        self._evict_ttl = evict_ttl_seconds
        self._evict_task: asyncio.Task[None] | None = None

    @staticmethod
    def _fingerprint(api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]

    def _resolve_key(self, user_id: str | None) -> _ResolvedKey:
        """Return the pool key, API key, and fingerprint for this user.

        Raises ``RuntimeError`` if no key source is configured.
        """
        if user_id:
            from app.services.user_config import get_user_api_key

            user_key = get_user_api_key(user_id, "STITCH_API_KEY")
            if user_key:
                return _ResolvedKey(
                    f"user:{user_id}", user_key, self._fingerprint(user_key)
                )
        env_key = (os.environ.get("STITCH_API_KEY") or "").strip()
        if env_key:
            return _ResolvedKey(
                self.POOL_KEY_ENV, env_key, self._fingerprint(env_key)
            )
        if should_use_mock_stitch_service():
            return _ResolvedKey(self.POOL_KEY_MOCK, None, "mock")
        raise RuntimeError(
            "No Stitch API key configured. Connect your Stitch key in Configuration."
        )

    async def get_or_spawn(
        self, user_id: str | None = None
    ) -> "StitchMCPService":
        """Return a ready service for this user, spawning if necessary."""
        resolved = self._resolve_key(user_id)
        pool_key = resolved.pool_key
        api_key = resolved.api_key
        fingerprint = resolved.fingerprint

        existing = self._services.get(pool_key)
        if (
            existing is not None
            and existing.is_ready()
            and self._fingerprints.get(pool_key) == fingerprint
        ):
            self._last_used[pool_key] = time.monotonic()
            return existing

        async with self._spawn_lock:
            existing = self._services.get(pool_key)
            if (
                existing is not None
                and existing.is_ready()
                and self._fingerprints.get(pool_key) == fingerprint
            ):
                self._last_used[pool_key] = time.monotonic()
                return existing

            old_task = self._tasks.pop(pool_key, None)
            self._services.pop(pool_key, None)
            self._fingerprints.pop(pool_key, None)
            if old_task and not old_task.done():
                old_task.cancel()

            if pool_key == self.POOL_KEY_MOCK:
                service: StitchMCPService = MockStitchMCPService()
            else:
                service = StitchMCPService(api_key=api_key)

            task = asyncio.create_task(
                service._run(), name=f"stitch-{pool_key}"
            )
            try:
                await asyncio.wait_for(
                    asyncio.shield(service._ready.wait()),
                    timeout=30.0,
                )
            except asyncio.TimeoutError as exc:
                task.cancel()
                raise RuntimeError(
                    f"StitchMCPService for {pool_key} did not become ready in 30s"
                ) from exc

            self._services[pool_key] = service
            self._tasks[pool_key] = task
            self._fingerprints[pool_key] = fingerprint
            self._last_used[pool_key] = time.monotonic()
            return service

    async def shutdown(self) -> None:
        """Cancel every running task and clear pool state."""
        if self._evict_task and not self._evict_task.done():
            self._evict_task.cancel()
        for task in list(self._tasks.values()):
            if not task.done():
                task.cancel()
        self._services.clear()
        self._tasks.clear()
        self._fingerprints.clear()
        self._last_used.clear()

    async def evict_idle(self) -> int:
        """Cancel and remove pool entries idle longer than TTL.

        Never evicts ``__env_default__`` — that is the hot platform path.
        Returns the number of evicted entries.
        """
        now = time.monotonic()
        async with self._spawn_lock:
            to_evict = [
                k
                for k, ts in self._last_used.items()
                if k != self.POOL_KEY_ENV and (now - ts) > self._evict_ttl
            ]
            for k in to_evict:
                task = self._tasks.pop(k, None)
                self._services.pop(k, None)
                self._fingerprints.pop(k, None)
                self._last_used.pop(k, None)
                if task and not task.done():
                    task.cancel()
        return len(to_evict)

    async def _evict_loop(self) -> None:
        """Background task: run evict_idle every 60s for the process lifetime."""
        while True:
            try:
                await asyncio.sleep(60)
                await self.evict_idle()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # pragma: no cover - defensive
                logger.warning("Stitch pool evict loop error: %s", e)

    def start_evict_loop(self) -> None:
        """Start the background eviction task. Idempotent."""
        if self._evict_task is None or self._evict_task.done():
            self._evict_task = asyncio.create_task(
                self._evict_loop(), name="stitch-pool-evict"
            )


# Module-level pool — initialised on first use or by lifespan.
_pool: StitchPool | None = None


def get_pool() -> StitchPool:
    """Return the module-level StitchPool, creating it if needed."""
    global _pool
    if _pool is None:
        _pool = StitchPool()
    return _pool


async def get_stitch_service(
    user_id: str | None = None,
) -> "StitchMCPService":
    """Return a ready StitchMCPService for the given user.

    Resolution order: user-saved STITCH_API_KEY → env STITCH_API_KEY → mock
    (if ``APP_BUILDER_USE_MOCK_STITCH=1``) → RuntimeError.
    """
    return await get_pool().get_or_spawn(user_id)
