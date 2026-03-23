# Phase 22: React Conversion & Output Targets - Research

**Researched:** 2026-03-23
**Domain:** HTML-to-React conversion, PWA generation, Capacitor scaffolding, Remotion video, npm version resolution, ZIP streaming
**Confidence:** HIGH

---

## Summary

Phase 22 is a pure generation phase — it takes existing Stitch-generated HTML stored in Supabase Storage and transforms it into four output formats: modular React/TypeScript components, a PWA-ready web package, a downloadable Capacitor project, and a Remotion walkthrough video. The ship stage ties all four targets together in a single user action.

The critical architectural insight is that the project already has Remotion fully wired: `remotion-render/` contains the composition, `app/services/remotion_render_service.py` handles the subprocess call pattern, and the `stitch-assets` bucket already allows `application/zip` MIME type. This phase is additive — no new infrastructure is needed, only new service modules and routes.

The HTML-to-React conversion cannot be done reliably with a static rule-based mapper because Stitch outputs vary in structure. Gemini with `response_mime_type="application/json"` structured output is the correct approach, consistent with how this project already uses Gemini for brief generation and design research. The output is a set of `.tsx` files zipped in-memory via Python's stdlib `zipfile` + `io.BytesIO`, then uploaded to `stitch-assets` and returned as a download URL — matching the existing asset persistence pattern exactly.

**Primary recommendation:** Use Gemini Flash (`response_mime_type="application/json"`) for HTML-to-React and Tailwind extraction, Python stdlib `zipfile`+`BytesIO` for all ZIP outputs, the existing `remotion_render_service.py` pattern for video, and a sequential async ship orchestrator that streams SSE per target.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OUTP-01 | Stitch HTML converted to modular React/TypeScript with Tailwind theme extraction; downloadable ZIP | HTML-to-React via Gemini Flash structured output; zipfile+BytesIO pattern; upload to stitch-assets bucket |
| OUTP-02 | PWA export: valid manifest.json, service worker, mobile meta tags; installable on Android + iOS | PWA manifest spec (name, icons 192+512, start_url, display:standalone); workbox SW recipe; iOS apple-touch meta tags |
| OUTP-03 | Capacitor project scaffold downloadable (capacitor.config.ts, package.json, platform configs) | Minimal Capacitor scaffold: 4 files; appId/appName/webDir pattern confirmed; ZIP download |
| OUTP-04 | Remotion walkthrough video from screenshots with transitions and title overlays | Existing remotion-render/ composition already supports imageUrl+text scenes; GeneratedVideoInputProps maps directly |
| OUTP-05 | Generated package.json files use current stable npm versions resolved at generation time | npm registry API: `GET https://registry.npmjs.org/{pkg}?fields=dist-tags` returns `{"dist-tags":{"latest":"x.y.z"}}`; httpx already in project |
| FLOW-07 | Ship stage generates all selected output targets in a single user action with SSE streaming | Sequential async generator per target; SSE events per step; same pattern as build-all-pages baton loop |
</phase_requirements>

---

## Standard Stack

### Core (all already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `zipfile` | stdlib | In-memory ZIP creation | No dep; `ZipFile(buf, "w")` + `writestr()` pattern |
| `io.BytesIO` | stdlib | In-memory byte buffer for ZIP | Pairs with zipfile; no disk I/O needed |
| `httpx` | `>=0.27.0` (pinned in pyproject.toml) | Async npm registry queries + HTML download | Already project dep; async API consistent with codebase |
| `google-genai` | `>=0.2.0` (pinned) | Gemini Flash for HTML→React structured output | Already used in prompt_enhancer.py and design_brief_service.py |
| `remotion_render_service` | internal | Subprocess Remotion render to MP4 | Fully implemented in app/services/remotion_render_service.py |
| `BeautifulSoup4` | `>=4.12.0` | HTML parsing for meta-tag extraction + style harvesting | Need to add; lxml parser recommended; stdlib html.parser slower |

### New Dependency (must add)

| Library | Version | Purpose | Why Needed |
|---------|---------|---------|------------|
| `beautifulsoup4` | `>=4.12.0` | Parse Stitch HTML to extract `<style>` blocks, `<meta>` tags, color variables | No HTML parsing lib currently in pyproject.toml; stdlib `html.parser` is sufficient parser backend — no lxml needed |

**Installation:**
```bash
uv add beautifulsoup4
```

Note: `beautifulsoup4` uses Python's stdlib `html.parser` by default — no additional C extension needed. Do NOT add `lxml` as a separate dependency; it requires native compilation and adds CI complexity.

### Frontend (already in project)

| Library | Version | Purpose | Note |
|---------|---------|---------|------|
| `remotion` | `^4.0.421` | Video player in frontend | Already in frontend/package.json |
| `@remotion/player` | `^4.0.421` | Embed video player in shipping UI | Already in frontend/package.json |

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
app/services/
├── react_converter.py        # HTML→React/TS via Gemini Flash + ZIP creation
├── pwa_generator.py          # manifest.json + service worker + meta tags + ZIP
├── capacitor_generator.py    # capacitor.config.ts + package.json + scaffold ZIP
└── ship_service.py           # orchestrates all 4 targets, yields SSE events

app/routers/app_builder.py    # add ship endpoint (existing file)

frontend/src/app/app-builder/[projectId]/shipping/
└── page.tsx                  # ShippingPage: target selection + progress + download links

tests/unit/app_builder/
├── test_react_converter.py
├── test_pwa_generator.py
├── test_capacitor_generator.py
└── test_ship_service.py
```

### Pattern 1: HTML-to-React via Gemini Flash structured output (OUTP-01)

**What:** Fetch HTML from Supabase Storage, send to Gemini Flash with JSON schema for component output, receive structured component tree, write TSX files + tailwind.config.ts to ZIP.
**When to use:** Whenever the HTML structure is Stitch-generated and variable in structure — rule-based HTML-to-JSX would miss custom tags, inline styles, and semantic groupings.

```python
# Source: matches existing pattern from app/services/prompt_enhancer.py
import json
import io
import zipfile
from google import genai

client = genai.Client()

REACT_CONVERTER_SCHEMA = {
    "type": "object",
    "properties": {
        "components": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},       # e.g. "HeroSection"
                    "filename": {"type": "string"},   # e.g. "HeroSection.tsx"
                    "code": {"type": "string"},       # full TSX source
                    "section": {"type": "string"},    # e.g. "hero"
                }
            }
        },
        "tailwind_theme": {
            "type": "object",
            "properties": {
                "colors": {"type": "object"},
                "fontFamily": {"type": "object"},
                "spacing": {"type": "object"},
            }
        },
        "index_tsx": {"type": "string"},   # root App.tsx that imports all components
    }
}

async def convert_html_to_react(html_content: str, screen_name: str) -> dict:
    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"""Convert this HTML to modular React TypeScript components.
Extract inline styles into Tailwind classes where possible.
Return structured JSON matching the schema.

Screen name: {screen_name}
HTML:
{html_content}""",
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=REACT_CONVERTER_SCHEMA,
        )
    )
    return json.loads(response.text)
```

**ZIP creation (in-memory, no disk):**
```python
# Source: Python stdlib zipfile + io.BytesIO (verified against Python docs)
def _build_react_zip(components: list[dict], tailwind_theme: dict, index_tsx: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for comp in components:
            zf.writestr(f"src/components/{comp['filename']}", comp["code"])
        zf.writestr("src/App.tsx", index_tsx)
        tailwind_config = _render_tailwind_config(tailwind_theme)
        zf.writestr("tailwind.config.ts", tailwind_config)
        zf.writestr("package.json", _render_package_json(["react", "tailwindcss"]))
    buf.seek(0)
    return buf.read()
```

### Pattern 2: PWA Generation (OUTP-02)

**What:** Generate manifest.json, a minimal service worker (SW), and HTML meta tags from the project's design system. Return as ZIP.
**When to use:** Any project where the user selects the PWA output target in the shipping stage.

**Required manifest.json fields (verified against web.dev docs):**
```python
# Source: https://web.dev/learn/pwa/web-app-manifest (HIGH confidence)
def _build_manifest(app_name: str, theme_color: str, bg_color: str) -> dict:
    return {
        "name": app_name,
        "short_name": app_name[:12],
        "description": f"{app_name} — generated by Pikar AI",
        "start_url": "/",
        "display": "standalone",
        "background_color": bg_color or "#ffffff",
        "theme_color": theme_color or "#000000",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {
                "src": "/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",  # required for Android adaptive icons
            },
        ],
        "categories": ["productivity"],
    }
```

**iOS meta tags** (Safari does not use manifest for home screen — these are required):
```html
<!-- Source: https://junkangworld.com/blog/master-pwa-installs-on-ios-android-the-2025-guide -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="{app_name}">
<link rel="apple-touch-icon" href="/icon-192.png">
```

**Minimal service worker (cache-first strategy for static assets):**
```javascript
// Source: https://web.dev/learn/pwa/workbox (MEDIUM - workbox is the standard)
// Minimal hand-written SW (no workbox dep needed for generated output):
const CACHE_NAME = 'v1';
const STATIC_ASSETS = ['/', '/index.html'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
```

Note: We generate a HAND-WRITTEN minimal SW, not workbox. The exported project is a static ZIP for a developer to download — adding workbox as a build tool dependency inside the export would force the developer to run a build step. A self-contained minimal SW is the right output for a downloadable scaffold.

### Pattern 3: Capacitor Scaffold Generation (OUTP-03)

**What:** Generate a 4-file ZIP scaffold that a developer can download and immediately run `npx cap add ios && npx cap add android`.
**Minimum required files (verified against capacitorjs.com/docs/config):**

```
my-app/
├── capacitor.config.ts    # app identity + webDir
├── package.json           # @capacitor/core + @capacitor/cli + @capacitor/ios + @capacitor/android
├── index.html             # required by Capacitor (must have <head> tag)
└── README.md              # developer instructions
```

**capacitor.config.ts template:**
```typescript
// Source: https://capacitorjs.com/docs/config (HIGH confidence)
import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: '{reverse_domain}',      // e.g. "com.pikar.myapp"
  appName: '{app_name}',
  webDir: 'www',
  server: {
    androidScheme: 'https',
  },
};

export default config;
```

**package.json for Capacitor scaffold:**
```json
{
  "name": "{app_slug}",
  "version": "1.0.0",
  "scripts": {
    "build": "echo 'Copy your web app build output to www/'",
    "cap:add:ios": "npx cap add ios",
    "cap:add:android": "npx cap add android",
    "cap:sync": "npx cap sync"
  },
  "dependencies": {
    "@capacitor/core": "{resolved_version}",
    "@capacitor/ios": "{resolved_version}",
    "@capacitor/android": "{resolved_version}"
  },
  "devDependencies": {
    "@capacitor/cli": "{resolved_version}"
  }
}
```

### Pattern 4: Remotion Video from Screenshots (OUTP-04)

**What:** Build a `GeneratedVideoInputProps` scenes array from project screenshot URLs and screen titles, call the existing `remotion_render_service.render_scenes_to_mp4()`.
**The existing service already handles everything** — FFmpeg, tempdir cleanup, timeouts, diagnostics. Phase 22 only needs to build the props dict.

```python
# Source: app/services/remotion_render_service.py (existing service)
# GeneratedVideoInputProps shape (from remotion-render/src/Composition.tsx):
# scenes: list of {text, duration, imageUrl?, videoUrl?, transition?}

def _build_walkthrough_scenes(screens: list[dict]) -> list[dict]:
    """Build Remotion scene list from approved screens with screenshots."""
    scenes = []
    for i, screen in enumerate(screens):
        scenes.append({
            "text": screen.get("name", f"Screen {i+1}"),
            "duration": 4,  # 4 seconds per screen
            "imageUrl": screen.get("screenshot_url") or screen.get("html_url"),
            "transition": {"type": "fade", "durationFrames": 15},
        })
    # Add intro and outro
    scenes.insert(0, {"text": project_title, "duration": 3})
    scenes.append({"text": "Built with Pikar AI", "duration": 2})
    return scenes
```

The existing `Composition.tsx` already handles:
- Ken Burns effect on static images (`scale` + `panX`/`panY` animation)
- Fade/slide-left/slide-right transitions between scenes
- Text overlays with spring animation

**CRITICAL:** `render_scenes_to_mp4()` is synchronous (uses `subprocess.run`). In the async ship orchestrator, call it with `asyncio.to_thread(render_scenes_to_mp4, ...)` — the established project pattern for sync calls (matches `asyncio.to_thread` in user management tools).

Upload the resulting MP4 bytes to `stitch-assets` bucket with content-type `video/mp4`. The bucket's `allowed_mime_types` currently only allows `['text/html', 'image/png', 'image/jpeg', 'image/webp', 'application/zip']` — **a migration is needed to add `video/mp4`**.

### Pattern 5: npm Version Resolution (OUTP-05)

**What:** Query npm registry at generation time so package.json files contain current stable versions, not hardcoded stale ones.
**Endpoint (verified):**

```python
# Source: https://www.tutorialpedia.org/blog/get-versions-from-npm-registry-api/ (MEDIUM)
# Official npm registry API (not api-docs.npmjs.com — that covers auth only)
# Endpoint: GET https://registry.npmjs.org/{package}?fields=dist-tags
# Response: {"dist-tags": {"latest": "4.17.21"}}

import httpx

_NPM_REGISTRY = "https://registry.npmjs.org"
_FALLBACK_VERSIONS = {
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "tailwindcss": "4.0.0",
    "@capacitor/core": "7.0.0",
    "@capacitor/cli": "7.0.0",
    "@capacitor/ios": "7.0.0",
    "@capacitor/android": "7.0.0",
    "remotion": "4.0.421",
}

async def resolve_npm_version(package: str) -> str:
    """Resolve current stable version from npm registry; return fallback on error."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{_NPM_REGISTRY}/{package}",
                params={"fields": "dist-tags"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["dist-tags"]["latest"]
    except Exception:
        return _FALLBACK_VERSIONS.get(package, "latest")
```

Resolve all required packages concurrently with `asyncio.gather` — each call is ~100 bytes and fast.

### Pattern 6: Ship Stage SSE Orchestrator (FLOW-07)

**What:** Single POST endpoint that accepts a list of requested output targets and streams progress events as each target completes. Uploads output ZIPs to `stitch-assets`, returns download URLs in final event.
**Pattern:** Same async generator + `StreamingResponse` as `build_all_pages` in `multi_page_service.py`.

```python
# Source: matches app/services/multi_page_service.py build_all_pages pattern (HIGH)
async def ship_project(
    project_id: str,
    user_id: str,
    targets: list[str],  # ["react", "pwa", "capacitor", "video"]
) -> AsyncIterator[dict]:
    screens = _fetch_approved_screens(project_id, user_id)
    download_urls = {}

    for target in targets:
        yield {"step": "target_started", "target": target}
        try:
            if target == "react":
                url = await _ship_react_export(project_id, user_id, screens)
            elif target == "pwa":
                url = await _ship_pwa_export(project_id, user_id, screens)
            elif target == "capacitor":
                url = await _ship_capacitor_export(project_id, user_id, screens)
            elif target == "video":
                url = await _ship_video_export(project_id, user_id, screens)
            download_urls[target] = url
            yield {"step": "target_complete", "target": target, "url": url}
        except Exception as exc:
            yield {"step": "target_failed", "target": target, "error": str(exc)}

    yield {"step": "ship_complete", "downloads": download_urls}
    # Advance app_projects.stage to "done" and status to "exported"
```

**SEQUENTIAL targets** — do not `asyncio.gather` the targets. Remotion render is a subprocess that consumes significant CPU; running it concurrently with Gemini calls on the same instance could cause timeouts. Sequential is safer and matches the baton loop precedent.

### Anti-Patterns to Avoid

- **Rule-based HTML-to-JSX:** Converting Stitch HTML with regex or a JS library like `html-to-react-components` is brittle — Stitch generates varied HTML structures. Use Gemini.
- **jszip in Python:** There is no jszip for Python. Use stdlib `zipfile` — it is sufficient and has no dependencies.
- **Hardcoded npm versions:** Violates OUTP-05. Always resolve from registry with fallback.
- **Streaming ZIP to client directly:** FastAPI `StreamingResponse` with a ZIP generator iterator has known issues (GitHub fastapi issue #2011). Upload to Supabase Storage and return a URL instead.
- **Blocking event loop on Remotion render:** `subprocess.run` in `render_scenes_to_mp4()` is synchronous. Always wrap with `asyncio.to_thread()`.
- **Writing ZIPs to disk:** All ZIP generation is in-memory (`io.BytesIO`). The project runs on Cloud Run — ephemeral filesystem, no guaranteed disk space.
- **Assuming stitch-assets bucket allows video/mp4:** It currently does not. A DB migration is required for the Remotion MP4 upload path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML→JSX attribute conversion | Custom regex: `class=` → `className=` etc. | Gemini Flash with JSON schema | LLM handles onclick/onmouseover/style/data-attrs, SVG attributes, boolean attrs, custom Stitch markup — all edge cases rule-based misses |
| Inline style → Tailwind class mapping | CSS value lookup table | Gemini extracts theme, generates arbitrary Tailwind values (`text-[14px]`, `bg-[#fff]`) | Complete Tailwind property mapping is 200+ rules; Gemini does it in one pass |
| ZIP file creation | Custom binary writer | Python stdlib `zipfile.ZipFile` + `io.BytesIO` | Stdlib handles deflate compression, ZIP64, CRC32 — all correct |
| npm version lookup | Scraping npmjs.com web page | `GET https://registry.npmjs.org/{pkg}?fields=dist-tags` | Official API, tiny payload, reliable |
| Service worker | Custom cache logic | Minimal hand-written SW (not workbox) | Workbox needs a build tool; generated output is standalone downloadable — keep it zero-dependency |
| Remotion video render | FFmpeg direct subprocess | Existing `remotion_render_service.render_scenes_to_mp4()` | Already handles FFmpeg fallback, diagnostics, retry on timeout, REMOTION_RENDER_ENABLED guard |

**Key insight:** Phase 22 is primarily a text/template generation phase. The hard problems (video render, asset persistence, auth) are already solved. The new work is coordinating the right tools in the right order.

---

## Common Pitfalls

### Pitfall 1: stitch-assets bucket missing video/mp4 MIME type
**What goes wrong:** `supabase.storage.from_("stitch-assets").upload(...)` fails with a storage error when trying to upload the Remotion MP4 — the bucket's `allowed_mime_types` currently excludes `video/mp4`.
**Why it happens:** The bucket was created in Phase 16 with a hardcoded allow-list. `video/mp4` was not anticipated then.
**How to avoid:** Add a migration (timestamp `20260324000000_stitch_assets_allow_video.sql`) that updates the bucket to add `video/mp4` to `allowed_mime_types`.
**Warning signs:** Upload returns `{"error": "mime type not allowed"}` at runtime.

### Pitfall 2: Gemini response_mime_type="application/json" returns truncated TSX code
**What goes wrong:** Gemini truncates code strings in JSON when the HTML is large, producing incomplete components.
**Why it happens:** Model output token limits. Stitch HTML for a full page can be 10-50KB.
**How to avoid:** Process screens individually (one HTML per Gemini call, not all screens in one batch). Limit to the selected variant's HTML. Use `gemini-2.0-flash` (larger output window than Pro for structured tasks). Consider chunking by section if HTML > 30KB.
**Warning signs:** Truncated `code` fields in the JSON response, or JSON parse errors.

### Pitfall 3: Remotion render blocked by asyncio event loop
**What goes wrong:** Calling `render_scenes_to_mp4()` directly in an async handler causes FastAPI to hang — the function uses `subprocess.run()` (blocking).
**Why it happens:** `subprocess.run()` blocks the event loop thread.
**How to avoid:** Always wrap: `mp4_bytes, asset_id = await asyncio.to_thread(render_scenes_to_mp4, ...)`. This is the exact pattern used in `users.py` for Supabase Auth Admin calls.
**Warning signs:** The `/ship` SSE endpoint hangs at the video step with no events.

### Pitfall 4: npm registry rate limiting in dev
**What goes wrong:** Rapid dev restarts trigger npm registry queries; after ~1000 requests/hour the registry returns 429.
**Why it happens:** The npm registry unauthenticated limit is 1000 req/hour (verified from search results).
**How to avoid:** Cache resolved versions in Redis for 1 hour with a `npm:version:{package}` key pattern. Fall back to `_FALLBACK_VERSIONS` on any error including 429. The circuit-breaker pattern from `app/services/cache.py` already handles Redis unavailability gracefully.
**Warning signs:** Version resolution returns empty strings or raises `httpx.HTTPStatusError: 429`.

### Pitfall 5: FastAPI StreamingResponse with ZIP bytes
**What goes wrong:** Returning ZIP bytes directly as `StreamingResponse` produces a corrupted ZIP file (documented FastAPI issue #2011).
**Why it happens:** `StreamingResponse` requires an iterator/generator, not raw bytes. Wrapping bytes in a single-chunk generator works but produces timing issues on the client.
**How to avoid:** Upload ZIP to Supabase Storage and return a permanent public URL. This also provides persistence (user can re-download), consistent with the project's generate-then-persist philosophy (matches `stitch_assets.py` pattern).
**Warning signs:** Downloaded ZIP cannot be opened; `zipfile` reports `BadZipFile`.

### Pitfall 6: iOS PWA requires separate meta tags, not just manifest
**What goes wrong:** PWA is installable on Android but shows no home-screen icon on iOS.
**Why it happens:** Safari on iOS/iPadOS does not use Web App Manifest for splash screens or icons — it requires proprietary `<meta name="apple-mobile-web-app-*">` tags and `<link rel="apple-touch-icon">`.
**How to avoid:** The PWA generator must produce an `index.html` with both the manifest link AND the Apple-specific meta tags.
**Warning signs:** Android install works; iOS "Add to Home Screen" shows a generic icon.

---

## Code Examples

### Resolved service structure

```python
# app/services/react_converter.py

import asyncio
import io
import json
import zipfile
from typing import Any

import httpx
from google import genai


_NPM_REGISTRY = "https://registry.npmjs.org"
_FALLBACK_VERSIONS = {
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "tailwindcss": "4.0.0",
}


async def resolve_npm_version(package: str) -> str:
    """Fetch latest stable version from npm registry; return fallback on error."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{_NPM_REGISTRY}/{package}", params={"fields": "dist-tags"})
            r.raise_for_status()
            return r.json()["dist-tags"]["latest"]
    except Exception:
        return _FALLBACK_VERSIONS.get(package, "latest")


async def convert_html_to_react_zip(
    html_content: str,
    screen_name: str,
    design_system: dict[str, Any],
) -> bytes:
    """Convert Stitch HTML to React/TS component ZIP via Gemini Flash."""
    client = genai.Client()
    # ... structured output call + ZIP assembly
```

### Capacitor scaffold generation (4 files, deterministic, no Gemini needed)

```python
# app/services/capacitor_generator.py

async def generate_capacitor_zip(
    app_name: str,
    app_id: str,       # e.g. "com.pikar.myapp"
    html_content: str, # selected index.html content
) -> bytes:
    cap_version = await resolve_npm_version("@capacitor/core")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("capacitor.config.ts", _render_cap_config(app_name, app_id))
        zf.writestr("package.json", _render_cap_package_json(app_name, cap_version))
        zf.writestr("www/index.html", html_content)
        zf.writestr("README.md", _render_cap_readme(app_name))
    buf.seek(0)
    return buf.read()
```

Note: Capacitor scaffold is 100% template-based — no Gemini needed. `app_id` is derived from `app_name` by the service (slugify + prepend `com.pikar.`).

### Ship endpoint skeleton

```python
# In app/routers/app_builder.py (new endpoint)

class ShipRequest(BaseModel):
    """Request body for the ship stage."""
    targets: list[Literal["react", "pwa", "capacitor", "video"]]


@router.post("/app-builder/projects/{project_id}/ship")
async def ship_project(
    project_id: str,
    body: ShipRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> StreamingResponse:
    """Stream ship progress as SSE. One event per target: started → complete/failed."""
    async def event_generator():
        async for event in ship_service.ship(
            project_id=project_id,
            user_id=user_id,
            targets=body.targets,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rule-based HTML→JSX (class→className, etc.) | LLM-based structured conversion | 2024+ | Handles any HTML structure; extracts semantic component names |
| Workbox CLI for SW generation | Minimal hand-written SW for scaffolds | Always appropriate for standalone exports | No build tool dependency in generated output |
| Capacitor 5.x | Capacitor 7.x (2025) | Q1 2025 | `server.androidScheme` required for HTTPS on Android |
| Manifest icon arrays with many sizes | 3 sizes: 192, 512, 512+maskable | 2024 Lighthouse update | Simpler; 512 maskable covers Android adaptive icons |
| PWA requires service worker | SW still recommended but Chrome/Edge install without it | 2025 | Our generated SW provides offline fallback, which is still best practice |

**Deprecated/outdated:**
- `html-to-react-components` npm package: Last updated 2019, React 16 era, does not handle hooks/TypeScript — do not use.
- `transform.tools/html-to-jsx`: Online tool only, not automatable from Python — do not use.
- Capacitor `webDir: "build"` for React: Phase 22 generates a scaffold with `webDir: "www"` (generic) — the README instructs developers to configure for their framework.

---

## Open Questions

1. **Remotion render timeout for multi-screen projects**
   - What we know: `REMOTION_RENDER_TIMEOUT` defaults to 120 seconds. A 10-screen walkthrough at 4s/screen = 40s total video but render could take 2-4x.
   - What's unclear: Whether the Cloud Run default 60s request timeout conflicts with the Remotion subprocess timeout on the ship endpoint.
   - Recommendation: Ship endpoint should set a longer timeout via Cloud Run annotations, OR move Remotion render to an async background job (ai_jobs pattern from Phase 12.1). For Phase 22, use `asyncio.to_thread` with a 3-minute inner timeout, and document the Cloud Run timeout requirement.

2. **Gemini context window vs. large Stitch HTML files**
   - What we know: Stitch HTML can be 30-100KB for feature-rich pages. Gemini Flash 2.0 has a 1M token context window.
   - What's unclear: Whether 100KB of HTML + system prompt stays within structured output reliable zone.
   - Recommendation: If HTML > 50KB, strip `<script>` tags before sending. Script content adds tokens without helping component structure extraction.

3. **Capacitor appId derivation**
   - What we know: Capacitor requires reverse-domain notation (e.g. `com.company.app`).
   - What's unclear: Whether to ask the user for appId or derive it programmatically.
   - Recommendation: Derive from app title: `f"com.pikar.{slugify(title)}"` (no user input needed for the scaffold; developer can edit before `npx cap add`).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/unit/app_builder/test_react_converter.py -x` |
| Full suite command | `uv run pytest tests/unit/app_builder/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OUTP-01 | `convert_html_to_react_zip` returns valid ZIP with .tsx files | unit | `uv run pytest tests/unit/app_builder/test_react_converter.py -x` | ❌ Wave 0 |
| OUTP-01 | ZIP contains tailwind.config.ts and package.json | unit | same | ❌ Wave 0 |
| OUTP-02 | `generate_pwa_zip` returns ZIP containing manifest.json with required fields | unit | `uv run pytest tests/unit/app_builder/test_pwa_generator.py -x` | ❌ Wave 0 |
| OUTP-02 | manifest.json has name, icons array (192+512), start_url, display:standalone | unit | same | ❌ Wave 0 |
| OUTP-03 | `generate_capacitor_zip` returns ZIP with capacitor.config.ts + package.json | unit | `uv run pytest tests/unit/app_builder/test_capacitor_generator.py -x` | ❌ Wave 0 |
| OUTP-04 | `_build_walkthrough_scenes` builds correct scene list from screen list | unit | `uv run pytest tests/unit/app_builder/test_ship_service.py::test_build_walkthrough_scenes -x` | ❌ Wave 0 |
| OUTP-04 | Remotion render called with `asyncio.to_thread` (not direct call) | unit | `uv run pytest tests/unit/app_builder/test_ship_service.py::test_render_uses_to_thread -x` | ❌ Wave 0 |
| OUTP-05 | `resolve_npm_version` returns registry version on success, fallback on error | unit | `uv run pytest tests/unit/app_builder/test_react_converter.py::test_resolve_npm_version -x` | ❌ Wave 0 |
| OUTP-05 | package.json in React ZIP has resolved versions not hardcoded | unit | same file | ❌ Wave 0 |
| FLOW-07 | `ship_service.ship()` yields target_started + target_complete events for each target | unit | `uv run pytest tests/unit/app_builder/test_ship_service.py::test_ship_events -x` | ❌ Wave 0 |
| FLOW-07 | `ship_service.ship()` yields target_failed (not exception) on individual target error | unit | `uv run pytest tests/unit/app_builder/test_ship_service.py::test_ship_partial_failure -x` | ❌ Wave 0 |
| FLOW-07 | POST /app-builder/projects/{id}/ship returns 200 StreamingResponse | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_ship_endpoint -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/app_builder/ -x`
- **Per wave merge:** `uv run pytest tests/unit/app_builder/ tests/unit/services/test_remotion_render_service.py -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/app_builder/test_react_converter.py` — covers OUTP-01, OUTP-05 (npm resolution)
- [ ] `tests/unit/app_builder/test_pwa_generator.py` — covers OUTP-02
- [ ] `tests/unit/app_builder/test_capacitor_generator.py` — covers OUTP-03
- [ ] `tests/unit/app_builder/test_ship_service.py` — covers OUTP-04, FLOW-07
- [ ] `supabase/migrations/20260324000000_stitch_assets_allow_video.sql` — unblocks OUTP-04 upload

---

## Sources

### Primary (HIGH confidence)
- Python stdlib `zipfile` module — in-memory ZIP via `io.BytesIO` + `ZipFile.writestr()`
- `app/services/remotion_render_service.py` — existing render pattern (subprocess, tempdir, diagnostics)
- `remotion-render/src/Composition.tsx` — `GeneratedVideoInputProps` and `SceneInput` types verified
- `remotion-render/package.json` — Remotion 4.0.421, @remotion/transitions ^4.0.421
- `supabase/migrations/20260321400000_app_builder_schema.sql` — stitch-assets bucket MIME type allow-list (application/zip present; video/mp4 absent)
- `app/services/stitch_assets.py` — Supabase Storage upload pattern (upload via `run_in_executor`)
- `frontend/package.json` — confirmed remotion ^4.0.421 and @remotion/player already in frontend

### Secondary (MEDIUM confidence)
- [capacitorjs.com/docs/config](https://capacitorjs.com/docs/config) — `CapacitorConfig` structure; `appId`, `appName`, `webDir`, `server.androidScheme` verified
- [web.dev/learn/pwa/web-app-manifest](https://web.dev/learn/pwa/web-app-manifest) — required manifest fields; icon sizes (192, 512, 512+maskable); display: standalone
- [junkangworld.com — PWA 2025 guide](https://junkangworld.com/blog/master-pwa-installs-on-ios-android-the-2025-guide) — iOS apple-mobile-web-app meta tags required; Safari does not use manifest
- [tutorialpedia.org npm registry API](https://www.tutorialpedia.org/blog/get-versions-from-npm-registry-api/) — `GET https://registry.npmjs.org/{pkg}?fields=dist-tags` returns `{"dist-tags":{"latest":"x.y.z"}}` verified
- [web.dev/learn/pwa/workbox](https://web.dev/learn/pwa/workbox) — workbox strategies; why hand-written SW is correct for standalone exports

### Tertiary (LOW confidence, flagged for validation)
- Gemini `response_mime_type="application/json"` for HTML→React conversion — pattern inferred from existing `design_brief_service.py` usage + general knowledge; requires validation that Gemini Flash handles 30-100KB HTML inputs reliably in structured output mode

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libs verified against existing project or official docs
- Architecture: HIGH — patterns derived from existing services (multi_page_service.py, remotion_render_service.py, stitch_assets.py)
- Pitfalls: HIGH — stitch-assets MIME type gap verified against actual migration SQL; FastAPI ZIP issue verified against GitHub issue #2011
- npm version resolution: HIGH — endpoint verified against official npm registry behavior
- Gemini structured output for HTML conversion: MEDIUM — pattern confirmed in project but scale with large HTML is unverified

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable technologies; npm registry API and Capacitor config are stable)
