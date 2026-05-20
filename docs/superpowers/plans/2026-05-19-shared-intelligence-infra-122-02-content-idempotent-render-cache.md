# Shared Intelligence Infrastructure — Plan 122-02: Idempotent Canva / Veo Render Cache

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap the two most expensive Content external surfaces — Canva design rendering and Veo video rendering — with an **idempotent render cache** keyed by the *content* of the render request (not by a user-supplied key). A cache HIT returns the previously rendered asset URL plus `cost_usd=0.00`; a cache MISS calls Canva or Veo, persists the asset URL under the same key, and emits an `asset_generation_provenance` claim (full claim shape settled in Plan 122-03 — this plan ships the *cache* and the *emission hook*).

**Architecture:** A small thin façade — `app/services/intelligence/render_cache.py` — sits in front of the two existing tools (`create_video_with_veo` in `app/mcp/tools/canva_media.py` and `create_design_with_canva`). The cache uses the existing two-tier infrastructure (`should_call_external` from `app/services/intelligence/cache.py`) with a hashed cache key:

```python
render_cache_key = sha256(
    f"{template_id}|{brand_profile_version}|{prompt_text}|{style_preset}|{dimensions}"
).hexdigest()
```

TTL is 30 days (2_592_000s) for both surfaces — render outputs are deterministic for a given input tuple and external pricing changes infrequently. Cost saved per cache hit:

- Canva design render: ~$0.08 / design (Canva Pro API tier pricing snapshot, 2026)
- Veo 3 render: ~$0.12 / render (snapshot from Vertex AI Veo pricing, May 2026; varies with duration)

**Tech Stack:** `app/services/intelligence/render_cache.py` (new façade), `app/services/intelligence/__init__.py` (re-export), `app/mcp/tools/canva_media.py` (wrap call sites), `app/services/cache.py` (existing CacheService — reused as the Redis backend).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 122 — Content Agent adoption § Cache.

**Out of scope:** Cost-tracking analytics surfacing (separate dashboard work), MCP-tool API key rotation (separate ops), the full provenance-claim shape (lives in 122-03 — this plan only emits a *placeholder* claim hook so the cache MISS path exercises end-to-end).

---

## File structure

**Create:**
- `app/services/intelligence/render_cache.py` — `render_cache_key()` + `cached_render()` + emission hook
- `tests/unit/services/intelligence/test_render_cache.py` — unit tests with mocked Redis
- `tests/integration/test_render_cache_canva_veo.py` — integration tests against real Redis + stub render fns

**Modify:**
- `app/services/intelligence/__init__.py` — re-export `render_cache_key`, `cached_render`
- `app/mcp/tools/canva_media.py` — wrap `create_video_with_veo` + the canva design path with `cached_render`

---

## Pre-flight context

### Prerequisite check (depends on 122-01 audit)

This plan **must not start** until Plan 122-01's brand-profile audit has shipped with conclusion = PROCEED. The cache key references `brand_profile_version`; if that column does not exist (audit = ESCALATE_TO_121_5), Phase 121.5 ships first to add it.

The kickoff check is mandatory and explicit:

```bash
test -f docs/superpowers/audits/2026-05-19-content-brand-profile-audit.md \
  && grep -q "Outcome: PROCEED" docs/superpowers/audits/2026-05-19-content-brand-profile-audit.md \
  && echo "OK — proceed" \
  || echo "BLOCKED — Phase 121.5 needed, do not start 122-02"
```

### Cache key contract

```python
def render_cache_key(
    *,
    template_id: str,
    brand_profile_version: int | str,
    prompt_text: str,
    style_preset: str,
    dimensions: tuple[int, int] | str,
) -> str:
    """Deterministic cache key for an idempotent render request.

    Returns the hex digest of sha256 over the canonical string form.
    """
```

Why each input matters:

| Field | Why it's in the key | What changes invalidate cache |
|---|---|---|
| `template_id` | Canva design template / Remotion composition variant | New template version → new render |
| `brand_profile_version` | A different brand looks different — same prompt, different style | Brand profile update → new render |
| `prompt_text` | The actual instruction the renderer follows | Any word change → new render (intentional) |
| `style_preset` | "vibrant" vs "tech" vs "ugc" totally changes output | Preset change → new render |
| `dimensions` | 1080x1080 vs 1080x1920 → different layouts | Aspect ratio / size change → new render |

The cache key is **input-deterministic**, not output-deterministic. Two semantically-identical prompts that differ in punctuation (e.g., "Create a launch promo." vs "Create a launch promo") produce different keys. That false-miss rate is acceptable; the alternative (embedding-similarity collapse) introduces unbounded staleness risk.

### Cache value shape

On HIT, we return a `CachedRender` dict:

```python
{
    "cache_hit": True,
    "asset_url": "<URL of the previously rendered asset>",
    "asset_id": "<UUID written into the user's Knowledge Vault>",
    "tool_metadata": {...},
    "rendered_at": "<ISO8601 UTC of original render>",
    "cost_usd": 0.0,
    "tier": "redis",
    "freshness_hours": <float>,
}
```

On MISS, we call the underlying render function, persist the value, emit a claim hook, and return:

```python
{
    "cache_hit": False,
    "asset_url": "<URL just rendered>",
    "asset_id": "<UUID just persisted>",
    "tool_metadata": {...},
    "rendered_at": "<ISO8601 UTC of THIS render>",
    "cost_usd": <surface-specific>,
    "tier": "redis",
    "freshness_hours": 0.0,
}
```

The `cached_render` façade is the *only* surface to call from MCP-tool wrappers — it owns the consult/persist/emit choreography so the render functions stay simple.

### TTL

30 days = `2_592_000` seconds for both `canva_render:*` and `veo_render:*`. The spec sets this once and doesn't differentiate between surfaces. Don't try to micro-optimize per-surface TTL in this plan — we have zero telemetry to base it on.

### Claim emission hook (forward-looking)

Plan 122-03 owns the full claim shape, but the cache MISS path must *invoke* claim emission so the wiring is exercised in this plan's tests. We import lazily:

```python
async def _emit_provenance_claim_safe(*, agent_id, prompt_text, asset_id, ...):
    """Best-effort emission. Failures must NOT fail the render."""
    try:
        from app.agents.content.claims import emit_asset_generation_provenance  # noqa: defined in 122-03
        await emit_asset_generation_provenance(
            agent_id=agent_id, prompt_text=prompt_text, asset_id=asset_id, ...
        )
    except ImportError:
        # 122-03 has not landed yet; that's fine.
        logger.debug("emit_asset_generation_provenance not available; skipping.")
    except Exception as e:
        logger.warning("provenance claim emission failed: %s", e)
```

The `ImportError` arm is deliberate: this plan ships before 122-03, so the import will fail at first; the cache must remain usable.

### Environment quirks

Same as Phase 113: Windows-PowerShell, `uv run`. Integration tests need `REDIS_HOST`/`REDIS_PORT` env vars and a running `docker compose` Redis (`pikar_dev_redis` password — see memory `reference_local_dev_env_quirks`).

---

## Tasks

### Task 1: Prerequisite check

**Files:** no edits.

- [ ] **Step 1: Verify Plan 122-01 audit shipped with PROCEED**

```bash
test -f docs/superpowers/audits/2026-05-19-content-brand-profile-audit.md
grep -E "^\*\*Outcome:\*\*" docs/superpowers/audits/2026-05-19-content-brand-profile-audit.md
```

Expected: file exists and the Outcome line reads `PROCEED`. If `ESCALATE_TO_121_5`, stop and open Phase 121.5.

- [ ] **Step 2: Verify the two-tier cache + Redis backend symbols exist**

```bash
grep -E "^async def should_call_external" app/services/intelligence/cache.py
grep -E "^def get_cache_service" app/services/cache.py
```

Expected: both present. If not, prior phases haven't landed — stop.

- [ ] **Step 3: Verify `create_video_with_veo` + `create_design_with_canva` still exist with the signatures Plan 122-02 wraps**

```bash
grep -nE "^async def (create_video_with_veo|create_design_with_canva)" app/mcp/tools/canva_media.py
```

Expected: both present. If signatures have changed, update the wrap sites in Task 5 accordingly.

No commit in this task.

### Task 2: Implement `render_cache_key()` (TDD)

**Files:**
- Create: `tests/unit/services/intelligence/test_render_cache.py`
- Create: `app/services/intelligence/render_cache.py`

- [ ] **Step 1: Failing unit tests for `render_cache_key`**

```python
"""Unit tests for the idempotent render cache façade."""

from __future__ import annotations

import hashlib

import pytest


def test_render_cache_key_is_deterministic():
    """Same inputs → same key."""
    from app.services.intelligence.render_cache import render_cache_key

    k1 = render_cache_key(
        template_id="instagram_post",
        brand_profile_version=7,
        prompt_text="Launch promo with bold contrast",
        style_preset="vibrant",
        dimensions=(1080, 1080),
    )
    k2 = render_cache_key(
        template_id="instagram_post",
        brand_profile_version=7,
        prompt_text="Launch promo with bold contrast",
        style_preset="vibrant",
        dimensions=(1080, 1080),
    )
    assert k1 == k2


def test_render_cache_key_changes_per_input_dimension():
    """Each of the 5 inputs influences the key — flip one at a time."""
    from app.services.intelligence.render_cache import render_cache_key

    base = dict(
        template_id="instagram_post",
        brand_profile_version=7,
        prompt_text="Launch promo with bold contrast",
        style_preset="vibrant",
        dimensions=(1080, 1080),
    )
    base_key = render_cache_key(**base)

    flipped_template = {**base, "template_id": "instagram_story"}
    flipped_version = {**base, "brand_profile_version": 8}
    flipped_prompt = {**base, "prompt_text": "Launch promo with bold contrast."}  # extra period
    flipped_style = {**base, "style_preset": "tech"}
    flipped_dims = {**base, "dimensions": (1080, 1920)}

    for f in (flipped_template, flipped_version, flipped_prompt, flipped_style, flipped_dims):
        assert render_cache_key(**f) != base_key, f"flip did not change key: {f}"


def test_render_cache_key_is_sha256_hex():
    """Key shape: 64-char hex (sha256)."""
    from app.services.intelligence.render_cache import render_cache_key

    k = render_cache_key(
        template_id="t",
        brand_profile_version=1,
        prompt_text="p" * 50,
        style_preset="s",
        dimensions="1080x1080",
    )
    assert len(k) == 64
    assert all(c in "0123456789abcdef" for c in k)


def test_render_cache_key_dimensions_tuple_vs_string_equivalent():
    """(1080, 1080) and '1080x1080' are normalized to the same key."""
    from app.services.intelligence.render_cache import render_cache_key

    k_tuple = render_cache_key(
        template_id="t", brand_profile_version=1,
        prompt_text="p" * 30, style_preset="s",
        dimensions=(1080, 1080),
    )
    k_string = render_cache_key(
        template_id="t", brand_profile_version=1,
        prompt_text="p" * 30, style_preset="s",
        dimensions="1080x1080",
    )
    assert k_tuple == k_string
```

- [ ] **Step 2: Run — should FAIL (module not yet created)**

```powershell
uv run pytest tests/unit/services/intelligence/test_render_cache.py -v --tb=short
```

- [ ] **Step 3: Implement `render_cache_key` in `app/services/intelligence/render_cache.py`**

```python
"""Idempotent Canva / Veo render cache.

Phase 122-02 wraps the two most expensive Content external surfaces with a
content-keyed Redis cache. The cache key is a sha256 over the canonical
input tuple — same prompt + same brand version + same dimensions returns
the previously rendered asset URL with zero external cost.

Saves ~$0.08-0.12 per cache HIT (Canva design or Veo render).
TTL is 30 days for both surfaces.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from app.services.cache import get_cache_service
from app.services.intelligence.cache import should_call_external

logger = logging.getLogger(__name__)

# 30 days — render outputs are deterministic for a given input tuple
# and external pricing changes infrequently.
RENDER_CACHE_TTL_SECONDS = 30 * 24 * 60 * 60  # 2_592_000

# Per-surface cost approximations (May 2026 pricing snapshot).
SURFACE_COST_USD: dict[str, float] = {
    "canva_render": 0.08,
    "veo_render": 0.12,
}


def _normalize_dimensions(dimensions: tuple[int, int] | str) -> str:
    """Canonicalise dimensions to '<w>x<h>' regardless of input shape."""
    if isinstance(dimensions, str):
        return dimensions.strip().lower().replace(" ", "")
    w, h = dimensions
    return f"{int(w)}x{int(h)}"


def render_cache_key(
    *,
    template_id: str,
    brand_profile_version: int | str,
    prompt_text: str,
    style_preset: str,
    dimensions: tuple[int, int] | str,
) -> str:
    """Compute the deterministic render cache key.

    Args:
        template_id: Canva design template id or Remotion composition variant.
        brand_profile_version: Version token from the brand_profiles row
            (added in Phase 121.5).
        prompt_text: Full instruction text passed to the renderer.
        style_preset: Style label (vibrant / tech / ugc / minimal / ...).
        dimensions: Either (w, h) tuple or '<w>x<h>' string.

    Returns:
        64-char lowercase hex sha256 digest.
    """
    norm_dims = _normalize_dimensions(dimensions)
    canonical = f"{template_id}|{brand_profile_version}|{prompt_text}|{style_preset}|{norm_dims}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Update `app/services/intelligence/__init__.py`**

```python
from app.services.intelligence.render_cache import (
    RENDER_CACHE_TTL_SECONDS,
    cached_render,           # implemented in Task 3
    render_cache_key,
)
```

Add the new names to `__all__`. (Note: `cached_render` lands in Task 3 — for now leave the import behind an existence check or stub it; the cleanest path is to land Task 2 + Task 3 in the same commit, but writing the tests before either implementation lets us TDD both. We split commits for clarity.)

- [ ] **Step 5: Re-run — should PASS for the key tests**

```powershell
uv run pytest tests/unit/services/intelligence/test_render_cache.py -v --tb=short
```

- [ ] **Step 6: Commit**

```bash
git add app/services/intelligence/render_cache.py app/services/intelligence/__init__.py tests/unit/services/intelligence/test_render_cache.py
git commit -m "feat(122-02): render_cache_key sha256 over canonical input tuple (GREEN)"
```

### Task 3: Implement `cached_render(...)` with HIT / MISS choreography (TDD)

**Files:**
- Modify: `tests/unit/services/intelligence/test_render_cache.py` — append HIT/MISS tests
- Modify: `app/services/intelligence/render_cache.py` — add `cached_render`

- [ ] **Step 1: Failing HIT/MISS tests**

```python
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_cached_render_hit_returns_zero_cost(monkeypatch):
    """Cache HIT returns cost_usd=0.0 and does NOT call the render fn."""
    from app.services.intelligence import render_cache

    cached_payload = {
        "asset_url": "https://cdn.example.com/asset.mp4",
        "asset_id": "00000000-0000-0000-0000-000000000001",
        "tool_metadata": {"duration": 6},
        "rendered_at": "2026-04-01T12:00:00+00:00",
    }

    class _FakeCache:
        async def get_with_age(self, key):
            return cached_payload, 60  # 60s old

        async def set_with_ttl(self, key, value, ttl):
            raise AssertionError("set should not be called on HIT")

    monkeypatch.setattr(render_cache, "get_cache_service", lambda: _FakeCache())

    render_fn = AsyncMock(side_effect=AssertionError("render fn should not be called on HIT"))

    result = await render_cache.cached_render(
        surface="veo_render",
        key=render_cache.render_cache_key(
            template_id="t", brand_profile_version=1,
            prompt_text="A test prompt of sufficient length to pass",
            style_preset="s", dimensions=(1080, 1080),
        ),
        render_fn=render_fn,
        emission_metadata={"agent_id": "VideoDirectorAgent", "prompt_text": "x" * 50},
    )

    assert result["cache_hit"] is True
    assert result["cost_usd"] == 0.0
    assert result["asset_url"] == "https://cdn.example.com/asset.mp4"
    render_fn.assert_not_called()


@pytest.mark.asyncio
async def test_cached_render_miss_calls_render_then_persists(monkeypatch):
    """Cache MISS calls render_fn, persists with 30-day TTL, returns cost."""
    from app.services.intelligence import render_cache

    persisted: dict = {}

    class _FakeCache:
        async def get_with_age(self, key):
            return None, None  # MISS

        async def set_with_ttl(self, key, value, ttl):
            persisted["key"] = key
            persisted["value"] = value
            persisted["ttl"] = ttl

    monkeypatch.setattr(render_cache, "get_cache_service", lambda: _FakeCache())

    async def fake_render():
        return {
            "asset_url": "https://cdn.example.com/new.mp4",
            "asset_id": "00000000-0000-0000-0000-000000000002",
            "tool_metadata": {"duration": 12},
        }

    key = render_cache.render_cache_key(
        template_id="t", brand_profile_version=1,
        prompt_text="A different prompt long enough to be useful",
        style_preset="s", dimensions=(1080, 1080),
    )

    result = await render_cache.cached_render(
        surface="veo_render",
        key=key,
        render_fn=fake_render,
        emission_metadata={"agent_id": "VideoDirectorAgent", "prompt_text": "y" * 50},
    )

    assert result["cache_hit"] is False
    assert result["cost_usd"] == render_cache.SURFACE_COST_USD["veo_render"]
    assert result["asset_url"] == "https://cdn.example.com/new.mp4"
    assert persisted["ttl"] == render_cache.RENDER_CACHE_TTL_SECONDS
    assert persisted["key"].startswith("veo_render:")


@pytest.mark.asyncio
async def test_cached_render_miss_emits_provenance_claim_safely(monkeypatch):
    """Provenance emission failures must NOT propagate."""
    from app.services.intelligence import render_cache

    class _FakeCache:
        async def get_with_age(self, key):
            return None, None
        async def set_with_ttl(self, key, value, ttl):
            return None

    monkeypatch.setattr(render_cache, "get_cache_service", lambda: _FakeCache())

    # Force the safe-emission helper to raise; result should still be valid.
    async def _boom(**_kw):
        raise RuntimeError("downstream emission boom")

    monkeypatch.setattr(render_cache, "_emit_provenance_claim_safe", _boom)

    async def fake_render():
        return {"asset_url": "u", "asset_id": "x", "tool_metadata": {}}

    result = await render_cache.cached_render(
        surface="canva_render",
        key="x" * 64,
        render_fn=fake_render,
        emission_metadata={"agent_id": "GraphicDesignerAgent", "prompt_text": "p" * 50},
    )
    assert result["cache_hit"] is False
    assert result["asset_url"] == "u"


@pytest.mark.asyncio
async def test_cached_render_cache_get_failure_falls_through_to_render(monkeypatch):
    """If Redis is down on GET, we still render (don't 500 the user)."""
    from app.services.intelligence import render_cache

    class _BrokenCache:
        async def get_with_age(self, key):
            raise ConnectionError("redis down")
        async def set_with_ttl(self, key, value, ttl):
            return None

    monkeypatch.setattr(render_cache, "get_cache_service", lambda: _BrokenCache())

    async def fake_render():
        return {"asset_url": "u", "asset_id": "x", "tool_metadata": {}}

    result = await render_cache.cached_render(
        surface="canva_render",
        key="y" * 64,
        render_fn=fake_render,
        emission_metadata={"agent_id": "GraphicDesignerAgent", "prompt_text": "p" * 50},
    )
    assert result["cache_hit"] is False
    assert result["asset_url"] == "u"
```

- [ ] **Step 2: Run — should FAIL (`cached_render` not implemented)**

```powershell
uv run pytest tests/unit/services/intelligence/test_render_cache.py -v --tb=short
```

- [ ] **Step 3: Append `cached_render` + helpers to `render_cache.py`**

```python
async def _emit_provenance_claim_safe(
    *,
    surface: str,
    asset_id: str,
    asset_url: str,
    agent_id: str,
    prompt_text: str,
) -> None:
    """Best-effort emission of an asset_generation_provenance claim.

    Plan 122-03 owns the full emission shape; this helper is the wiring
    point so MISS paths can call it without a forward dependency.
    Failures are logged at WARNING and swallowed.
    """
    try:
        # Lazy import — Plan 122-03 has not necessarily landed yet.
        from app.agents.content.claims import emit_asset_generation_provenance
    except ImportError:
        logger.debug(
            "emit_asset_generation_provenance not available (122-03 not landed); skipping."
        )
        return
    try:
        await emit_asset_generation_provenance(
            surface=surface,
            asset_id=asset_id,
            asset_url=asset_url,
            agent_id=agent_id,
            prompt_text=prompt_text,
        )
    except Exception as e:
        logger.warning(
            "provenance claim emission failed (surface=%s asset_id=%s): %s",
            surface, asset_id, e,
        )


async def cached_render(
    *,
    surface: str,
    key: str,
    render_fn: Callable[[], Awaitable[dict[str, Any]]],
    emission_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Idempotent render façade.

    Consults Redis at ``{surface}:{key}``. On HIT, returns the cached payload
    with cost_usd=0.0 and does NOT call ``render_fn``. On MISS, calls
    ``render_fn`` to produce ``{asset_url, asset_id, tool_metadata}``,
    persists with 30-day TTL, emits a provenance claim (best-effort),
    and returns the render result with the per-surface cost.

    Failures of the cache backend on GET fall through to a fresh render
    (the user must not see a 500 because Redis is down). Failures on SET
    are logged but do not fail the response.

    Args:
        surface: One of ``canva_render``, ``veo_render``. Determines both
            the cache-key prefix and the cost attribution.
        key: Output of :func:`render_cache_key`.
        render_fn: Awaitable that performs the actual external render.
            Must return a dict with keys ``asset_url``, ``asset_id``,
            ``tool_metadata`` (free-form per-surface metadata).
        emission_metadata: Dict with ``agent_id`` and ``prompt_text``,
            forwarded to the provenance claim emitter.

    Returns:
        Dict matching the contract in plan 122-02 § Cache value shape.
    """
    if surface not in SURFACE_COST_USD:
        raise ValueError(f"Unknown render surface: {surface!r}")
    namespaced_key = f"{surface}:{key}"

    # --- Consult cache (degrades on backend failure) ---
    try:
        decision = await should_call_external(
            cache_key=namespaced_key,
            ttl_seconds=RENDER_CACHE_TTL_SECONDS,
        )
    except Exception as e:
        logger.warning("cached_render: should_call_external raised: %s", e)
        decision = None  # treat as miss

    # `decision` carries only tier+verdict+age; fetch the actual payload via the
    # cache service. should_call_external doesn't return the value (its contract
    # is verdict only).
    if decision is not None and decision.verdict == "fresh":
        try:
            cache = get_cache_service()
            payload, age_seconds = await cache.get_with_age(namespaced_key)
        except Exception as e:
            logger.warning("cached_render: cache get_with_age failed on fresh decision: %s", e)
            payload, age_seconds = None, None

        if payload is not None and isinstance(payload, dict):
            return {
                "cache_hit": True,
                "asset_url": payload.get("asset_url"),
                "asset_id": payload.get("asset_id"),
                "tool_metadata": payload.get("tool_metadata", {}),
                "rendered_at": payload.get("rendered_at"),
                "cost_usd": 0.0,
                "tier": "redis",
                "freshness_hours": (age_seconds or 0) / 3600.0,
            }

    # --- MISS path ---
    rendered = await render_fn()
    asset_url = rendered.get("asset_url")
    asset_id = rendered.get("asset_id")
    tool_metadata = rendered.get("tool_metadata", {})
    rendered_at = datetime.now(timezone.utc).isoformat()

    # Persist (best-effort)
    try:
        cache = get_cache_service()
        await cache.set_with_ttl(
            namespaced_key,
            {
                "asset_url": asset_url,
                "asset_id": asset_id,
                "tool_metadata": tool_metadata,
                "rendered_at": rendered_at,
            },
            RENDER_CACHE_TTL_SECONDS,
        )
    except Exception as e:
        logger.warning("cached_render: cache set failed (key=%s): %s", namespaced_key, e)

    # Emit provenance (best-effort)
    try:
        await _emit_provenance_claim_safe(
            surface=surface,
            asset_id=str(asset_id) if asset_id else "",
            asset_url=str(asset_url) if asset_url else "",
            agent_id=str(emission_metadata.get("agent_id") or ""),
            prompt_text=str(emission_metadata.get("prompt_text") or ""),
        )
    except Exception as e:
        # _emit_provenance_claim_safe already swallows; this is belt-and-braces.
        logger.warning("cached_render: emission outer guard caught: %s", e)

    return {
        "cache_hit": False,
        "asset_url": asset_url,
        "asset_id": asset_id,
        "tool_metadata": tool_metadata,
        "rendered_at": rendered_at,
        "cost_usd": SURFACE_COST_USD[surface],
        "tier": "redis",
        "freshness_hours": 0.0,
    }
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_render_cache.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/services/intelligence/render_cache.py tests/unit/services/intelligence/test_render_cache.py
git commit -m "feat(122-02): cached_render HIT/MISS choreography with safe provenance emission (GREEN)"
```

### Task 4: Wire `cached_render` around `create_video_with_veo`

**Files:**
- Modify: `app/mcp/tools/canva_media.py` — wrap the Veo entry point

- [ ] **Step 1: Read the existing function to confirm the signature and side effects**

```bash
grep -nE "^async def create_video_with_veo" app/mcp/tools/canva_media.py
```

`create_video_with_veo(prompt, duration_seconds=6, aspect_ratio="16:9", user_id=None)` delegates to `app.agents.tools.media.generate_video`. Wrap **outside** that call so the cache key includes the user-supplied inputs and not internal Remotion-vs-Veo routing details.

- [ ] **Step 2: Add a failing integration test stub**

`tests/unit/mcp/tools/test_create_video_with_veo_cache.py`:

```python
"""Verify create_video_with_veo consults cached_render on the hot path."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_create_video_with_veo_uses_cached_render(monkeypatch):
    """Second call with identical args returns cache_hit=True and zero cost."""
    from app.mcp.tools import canva_media

    # Stub out the underlying generate_video so we only test the cache layer.
    stub_video = {
        "success": True,
        "asset_id": "00000000-0000-0000-0000-000000000aaa",
        "asset_url": "https://cdn.example.com/video.mp4",
        "tool_metadata": {"duration": 6},
    }
    monkeypatch.setattr(
        "app.agents.tools.media.generate_video",
        AsyncMock(return_value=stub_video),
    )

    # Stub brand profile version
    async def _fake_brand_version(_user_id):
        return 7
    monkeypatch.setattr(canva_media, "_resolve_brand_profile_version", _fake_brand_version)

    # Use an in-memory fake cache that supports the contract
    cache_state: dict = {}

    class _FakeCacheService:
        async def get_with_age(self, key):
            v = cache_state.get(key)
            return (v, 1) if v is not None else (None, None)
        async def set_with_ttl(self, key, value, ttl):
            cache_state[key] = value

    from app.services.intelligence import render_cache
    monkeypatch.setattr(render_cache, "get_cache_service", lambda: _FakeCacheService())

    # Skip the should_call_external decision plumbing on first call
    async def _miss(**_kw):
        from app.services.intelligence.schemas import CacheDecision
        verdict = "fresh" if cache_state else "miss"
        return CacheDecision(tier="redis", verdict=verdict, freshness_hours=0.0)
    monkeypatch.setattr(render_cache, "should_call_external", _miss)

    # First call — MISS
    r1 = await canva_media.create_video_with_veo(
        prompt="A clean launch promo for the new feature, modern, energetic",
        duration_seconds=6,
        aspect_ratio="16:9",
        user_id="u1",
    )
    assert r1.get("cache_hit") is False
    assert r1.get("cost_usd") == render_cache.SURFACE_COST_USD["veo_render"]

    # Second call — HIT
    r2 = await canva_media.create_video_with_veo(
        prompt="A clean launch promo for the new feature, modern, energetic",
        duration_seconds=6,
        aspect_ratio="16:9",
        user_id="u1",
    )
    assert r2.get("cache_hit") is True
    assert r2.get("cost_usd") == 0.0
    assert r2.get("asset_url") == r1.get("asset_url")
```

- [ ] **Step 3: Run — should FAIL (wrap not yet in place)**

```powershell
uv run pytest tests/unit/mcp/tools/test_create_video_with_veo_cache.py -v --tb=short
```

- [ ] **Step 4: Implement the wrap**

In `app/mcp/tools/canva_media.py`, locate `create_video_with_veo` (line ~386) and refactor:

```python
async def _resolve_brand_profile_version(user_id: str | None) -> int | str:
    """Resolve the current brand_profile.version for cache keying.

    Returns 0 if no brand profile is found — that's a deliberate sentinel
    so cache entries for "no-brand" users still collide correctly with
    each other (i.e., they share the same key for the same prompt).
    """
    if not user_id:
        return 0
    try:
        from app.agents.tools.brand_profile import get_brand_profile
        result = await get_brand_profile(user_id=str(user_id))
        if result.get("success") and result.get("profile"):
            return result["profile"].get("version", 0)
    except Exception as e:
        logger.warning("_resolve_brand_profile_version failed: %s", e)
    return 0


def _aspect_ratio_to_dimensions(aspect_ratio: str, duration_seconds: int) -> tuple[int, int]:
    """Map "16:9" / "9:16" / "1:1" to a canonical dimensions tuple.

    Used solely as a cache-key input — actual render sizes are decided
    by the Veo / Remotion code paths downstream.
    """
    mapping = {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "1:1":  (1080, 1080),
        "4:5":  (1080, 1350),
    }
    return mapping.get(aspect_ratio, (1080, 1080))


async def create_video_with_veo(
    prompt: str,
    duration_seconds: int = 6,
    aspect_ratio: str = "16:9",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Create a video from a text prompt; cached + idempotent.

    Cache layer (Phase 122-02): sha256(prompt + brand_profile_version +
    duration + aspect_ratio + dimensions) — same args from the same brand
    return the cached MP4 URL with cost=0.

    Cache MISS calls media.generate_video (Veo 3 or Remotion as before)
    and emits an asset_generation_provenance claim.
    """
    from app.agents.tools import media
    from app.services.intelligence.render_cache import cached_render, render_cache_key

    brand_version = await _resolve_brand_profile_version(user_id)
    dimensions = _aspect_ratio_to_dimensions(aspect_ratio, duration_seconds)

    # The "style preset" for Veo cache keying is the duration bucket — same
    # prompt at 6s vs 28s produces different renders.
    style_preset = f"veo:{duration_seconds}s:{aspect_ratio}"

    key = render_cache_key(
        template_id="veo_render",
        brand_profile_version=brand_version,
        prompt_text=prompt,
        style_preset=style_preset,
        dimensions=dimensions,
    )

    async def _do_render() -> dict[str, Any]:
        raw = await media.generate_video(
            prompt=prompt,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            user_id=user_id,
        )
        # Normalize to the cached_render contract
        return {
            "asset_url": raw.get("asset_url") or raw.get("video_url") or raw.get("url"),
            "asset_id": raw.get("asset_id") or raw.get("id"),
            "tool_metadata": {
                "duration_seconds": duration_seconds,
                "aspect_ratio": aspect_ratio,
                "tool": "create_video_with_veo",
                **{k: v for k, v in raw.items() if k not in {"asset_url", "asset_id"}},
            },
        }

    result = await cached_render(
        surface="veo_render",
        key=key,
        render_fn=_do_render,
        emission_metadata={
            "agent_id": "VideoDirectorAgent",
            "prompt_text": prompt,
        },
    )
    # Preserve the upstream "success" contract — old callers expect it.
    result["success"] = True
    return result
```

- [ ] **Step 5: Re-run unit test — should PASS**

```powershell
uv run pytest tests/unit/mcp/tools/test_create_video_with_veo_cache.py -v --tb=short
```

- [ ] **Step 6: Commit**

```bash
git add app/mcp/tools/canva_media.py tests/unit/mcp/tools/test_create_video_with_veo_cache.py
git commit -m "feat(122-02): wrap create_video_with_veo in idempotent render cache (GREEN)"
```

### Task 5: Wire `cached_render` around the Canva design path

**Files:**
- Modify: `app/mcp/tools/canva_media.py` — wrap `CanvaMCPTool.create_design_with_canva`

The Canva path is a class method (line ~79), unlike the Veo path. Wrap at the *callable* boundary rather than monkeying with the class internals.

- [ ] **Step 1: Failing test**

`tests/unit/mcp/tools/test_canva_design_cache.py`:

```python
"""Cache wrap around the Canva design call."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_canva_design_uses_cached_render(monkeypatch):
    """create_design_with_canva returns cache HIT on second call with same args."""
    from app.mcp.tools import canva_media

    raw_result = {
        "asset_id": "00000000-0000-0000-0000-000000000bbb",
        "asset_url": "https://canva.example.com/design.png",
        "design_id": "abc123",
    }

    tool = canva_media.CanvaMCPTool()

    # Stub the underlying network call
    async def _stub_create_design(self, design_type, title, content=None):
        return raw_result
    monkeypatch.setattr(
        canva_media.CanvaMCPTool,
        "_uncached_create_design_with_canva",
        _stub_create_design,
    )

    async def _fake_brand_version(_user_id):
        return 7
    monkeypatch.setattr(canva_media, "_resolve_brand_profile_version", _fake_brand_version)

    state: dict = {}

    class _FakeCacheService:
        async def get_with_age(self, key):
            v = state.get(key)
            return (v, 1) if v else (None, None)
        async def set_with_ttl(self, key, value, ttl):
            state[key] = value

    from app.services.intelligence import render_cache
    monkeypatch.setattr(render_cache, "get_cache_service", lambda: _FakeCacheService())

    async def _decision(**_kw):
        from app.services.intelligence.schemas import CacheDecision
        return CacheDecision(
            tier="redis",
            verdict="fresh" if state else "miss",
            freshness_hours=0.0,
        )
    monkeypatch.setattr(render_cache, "should_call_external", _decision)

    r1 = await tool.create_design_with_canva(
        design_type="instagram_post",
        title="Launch promo",
        content={"prompt": "vibrant, energetic launch promo for the new feature"},
        user_id="u1",
    )
    assert r1.get("cache_hit") is False

    r2 = await tool.create_design_with_canva(
        design_type="instagram_post",
        title="Launch promo",
        content={"prompt": "vibrant, energetic launch promo for the new feature"},
        user_id="u1",
    )
    assert r2.get("cache_hit") is True
    assert r2.get("cost_usd") == 0.0
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/mcp/tools/test_canva_design_cache.py -v --tb=short
```

- [ ] **Step 3: Refactor `CanvaMCPTool.create_design_with_canva` into cached + uncached pair**

```python
# Rename existing logic
async def _uncached_create_design_with_canva(
    self,
    design_type: str,
    title: str,
    content: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Original Canva network call. Reachable only via cached wrapper."""
    # [... existing implementation body unchanged ...]


# New cached entry point
async def create_design_with_canva(
    self,
    design_type: str,
    title: str,
    content: dict[str, Any] | None = None,
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Cached Canva design entry point.

    Cache key uses design_type, brand_profile_version, prompt text (drawn
    from ``content["prompt"]`` or falling back to ``title``), the
    NANO_BANANA-style preset (defaulted to "vibrant"), and the
    DESIGN_TYPES dimensions for the design_type.
    """
    from app.services.intelligence.render_cache import cached_render, render_cache_key

    brand_version = await _resolve_brand_profile_version(user_id)
    prompt_text = (content or {}).get("prompt") or title or ""
    style_preset = (content or {}).get("style") or "vibrant"
    dims = self.DESIGN_TYPES.get(design_type, {"width": 1080, "height": 1080})

    key = render_cache_key(
        template_id=f"canva:{design_type}",
        brand_profile_version=brand_version,
        prompt_text=prompt_text,
        style_preset=style_preset,
        dimensions=(dims["width"], dims["height"]),
    )

    async def _do_render():
        raw = await self._uncached_create_design_with_canva(design_type, title, content)
        return {
            "asset_url": raw.get("asset_url") or raw.get("design_url"),
            "asset_id": raw.get("asset_id") or raw.get("design_id"),
            "tool_metadata": {
                "design_type": design_type,
                "title": title,
                "tool": "create_design_with_canva",
                **{k: v for k, v in raw.items() if k not in {"asset_url", "design_url"}},
            },
        }

    result = await cached_render(
        surface="canva_render",
        key=key,
        render_fn=_do_render,
        emission_metadata={
            "agent_id": "GraphicDesignerAgent",
            "prompt_text": prompt_text,
        },
    )
    result["success"] = result.get("asset_url") is not None
    return result
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/mcp/tools/test_canva_design_cache.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/mcp/tools/canva_media.py tests/unit/mcp/tools/test_canva_design_cache.py
git commit -m "feat(122-02): wrap CanvaMCPTool.create_design_with_canva in idempotent render cache (GREEN)"
```

### Task 6: Integration test against real Redis

**Files:**
- Create: `tests/integration/test_render_cache_canva_veo.py`

The unit tests use a fake cache. The integration test uses the actual `CacheService` so we catch (a) JSON serialization issues, (b) Redis key-shape regressions, and (c) circuit-breaker fallthrough behaviour.

- [ ] **Step 1: Write the integration test**

```python
"""Integration test: cached_render against real Redis with stub render fns."""

from __future__ import annotations

import os
from typing import Any

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("REDIS_HOST"),
        reason="REDIS_HOST not set; skipping integration test",
    ),
]


@pytest.mark.asyncio
async def test_cached_render_round_trip_via_real_redis(monkeypatch):
    """First call MISSes; second call HITs and returns cost=0."""
    from app.services.intelligence.render_cache import (
        SURFACE_COST_USD,
        cached_render,
        render_cache_key,
    )

    calls = {"n": 0}

    async def stub_render() -> dict[str, Any]:
        calls["n"] += 1
        return {
            "asset_url": f"https://example.com/asset-{calls['n']}.mp4",
            "asset_id": f"asset-{calls['n']}",
            "tool_metadata": {"call": calls["n"]},
        }

    key = render_cache_key(
        template_id="integration_test",
        brand_profile_version=999,
        prompt_text="A deterministic integration-test prompt that is long enough",
        style_preset="vibrant",
        dimensions=(1080, 1080),
    )

    r1 = await cached_render(
        surface="veo_render",
        key=key,
        render_fn=stub_render,
        emission_metadata={"agent_id": "VideoDirectorAgent", "prompt_text": "p" * 50},
    )
    assert r1["cache_hit"] is False
    assert r1["cost_usd"] == SURFACE_COST_USD["veo_render"]
    assert calls["n"] == 1

    r2 = await cached_render(
        surface="veo_render",
        key=key,
        render_fn=stub_render,
        emission_metadata={"agent_id": "VideoDirectorAgent", "prompt_text": "p" * 50},
    )
    assert r2["cache_hit"] is True
    assert r2["cost_usd"] == 0.0
    assert r2["asset_url"] == r1["asset_url"]
    assert calls["n"] == 1   # render_fn NOT called a second time


@pytest.mark.asyncio
async def test_cache_keys_are_namespaced_by_surface(monkeypatch):
    """Same key under different surfaces must NOT collide."""
    from app.services.intelligence.render_cache import cached_render, render_cache_key

    async def _render_video():
        return {"asset_url": "video", "asset_id": "v", "tool_metadata": {}}

    async def _render_canva():
        return {"asset_url": "canva", "asset_id": "c", "tool_metadata": {}}

    shared_key = render_cache_key(
        template_id="t", brand_profile_version=1,
        prompt_text="shared prompt long enough for the test",
        style_preset="s", dimensions=(1080, 1080),
    )

    v1 = await cached_render(
        surface="veo_render", key=shared_key,
        render_fn=_render_video,
        emission_metadata={"agent_id": "VideoDirectorAgent", "prompt_text": "x" * 50},
    )
    c1 = await cached_render(
        surface="canva_render", key=shared_key,
        render_fn=_render_canva,
        emission_metadata={"agent_id": "GraphicDesignerAgent", "prompt_text": "x" * 50},
    )
    assert v1["asset_url"] != c1["asset_url"]
```

- [ ] **Step 2: Run**

```powershell
$env:REDIS_HOST = "localhost"
$env:REDIS_PORT = "6379"
$env:REDIS_PASSWORD = "pikar_dev_redis"
uv run pytest tests/integration/test_render_cache_canva_veo.py -v --tb=short
```

Expected: PASS. If the cache HIT case fails with `cache_hit=False`, the JSON serialization of the cached payload is dropping a field — inspect `cache.set_with_ttl` and verify the round-trip.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_render_cache_canva_veo.py
git commit -m "test(122-02): integration test for render cache HIT/MISS via real Redis"
```

### Task 7: Cost-saving simulation test (synthetic burst)

**Files:**
- Create: `tests/integration/test_render_cache_cost_saving.py`

Establishes the headline number cited in the spec: ~$0.08-0.12 per cached render. Treat as a verification-of-claim test, not a perf gate.

- [ ] **Step 1: Write the test**

```python
"""Cost-saving simulation: N repeated render requests should produce 1 MISS + N-1 HITs."""

from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("REDIS_HOST"),
        reason="REDIS_HOST not set",
    ),
]


@pytest.mark.asyncio
async def test_repeated_renders_save_predictable_dollars():
    """20 identical Veo requests → 1 MISS ($0.12) + 19 HITs ($0.00 each) = $0.12."""
    from app.services.intelligence.render_cache import (
        SURFACE_COST_USD,
        cached_render,
        render_cache_key,
    )

    misses = {"n": 0}

    async def fake_render():
        misses["n"] += 1
        return {"asset_url": "u", "asset_id": "a", "tool_metadata": {}}

    key = render_cache_key(
        template_id="cost_sim",
        brand_profile_version=42,
        prompt_text="A long enough prompt to satisfy the embed guard length floor",
        style_preset="vibrant",
        dimensions=(1080, 1920),
    )

    total_cost = 0.0
    for _ in range(20):
        r = await cached_render(
            surface="veo_render",
            key=key,
            render_fn=fake_render,
            emission_metadata={"agent_id": "VideoDirectorAgent", "prompt_text": "p" * 50},
        )
        total_cost += float(r["cost_usd"])

    assert misses["n"] == 1, f"expected exactly 1 MISS, got {misses['n']}"
    assert total_cost == pytest.approx(SURFACE_COST_USD["veo_render"], abs=1e-6)
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_render_cache_cost_saving.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_render_cache_cost_saving.py
git commit -m "test(122-02): cost-saving sim — 20 calls cost only 1 MISS"
```

### Task 8: Lint + Plan 122-02 acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/services/intelligence/render_cache.py app/mcp/tools/canva_media.py tests/unit/services/intelligence/test_render_cache.py tests/unit/mcp/tools/ tests/integration/test_render_cache_canva_veo.py tests/integration/test_render_cache_cost_saving.py
uv run ruff format app/services/intelligence/render_cache.py app/mcp/tools/canva_media.py tests/unit/services/intelligence/test_render_cache.py tests/unit/mcp/tools/ tests/integration/test_render_cache_canva_veo.py tests/integration/test_render_cache_cost_saving.py --check
```

Fix in place. Commit any style-only changes with `style(122-02): ...`.

- [ ] **Step 2: Type check**

```powershell
uv run ty check app/services/intelligence/render_cache.py app/mcp/tools/canva_media.py
```

- [ ] **Step 3: Plan 122-02 acceptance cross-check**

| Acceptance criterion (Phase 122 spec) | Verified by |
|---|---|
| Idempotent render cache shipped | Task 3 |
| Cache key = sha256 over 5-tuple | Task 2 |
| TTL = 30 days for both surfaces | Task 3 constant + Task 6 round-trip |
| HIT returns asset URL + cost=$0.00 | Task 3 + Task 6 |
| MISS calls Canva/Veo + emits provenance claim hook | Task 3, Task 4, Task 5 |
| `canva_render:{key}` namespacing | Task 5, Task 6 |
| `veo_render:{key}` namespacing | Task 4, Task 6 |
| Cache surfaces don't collide | Task 6 second test |
| Provenance emission is best-effort (no propagation) | Task 3 third test |
| Backend failure falls through to render (no 500) | Task 3 fourth test |
| Cost saving demonstrated | Task 7 |
| Lint + type-check clean | Task 8 |

- [ ] **Step 4: Plan 122-02 complete.**

Next planned work in Phase 122: 122-03 (per-sub-agent claim emission, including the full `emit_asset_generation_provenance` shape that this plan's cache MISS path will start invoking automatically once 122-03 ships).

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `render_cache_key = sha256(template_id + brand_profile_version + prompt_text + style_preset + dimensions)` | Task 2 |
| Cache TTL 30 days | Task 3 constant `RENDER_CACHE_TTL_SECONDS` |
| Saves ~$0.08-0.12 per cached design / render | Task 3 `SURFACE_COST_USD` + Task 7 |
| Same inputs → cache HIT returns cached asset URL + cost=$0.00 | Task 3, Task 4, Task 5 acceptance |
| Cache MISS calls Canva/Veo and emits asset_generation_provenance claim | Task 3 emission hook + Task 4 + Task 5 |
| `canva_render:{render_cache_key}` TTL 30d (2_592_000s) | Task 5 + Task 6 |
| `veo_render:{render_cache_key}` TTL 30d | Task 4 + Task 6 |
| Audit-decision dependency (must wait for 122-01 PROCEED) | Task 1 |

All Plan 122-02 spec lines covered.
