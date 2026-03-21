---
phase: 16-foundation
plan: "03"
subsystem: app-builder-services
tags: [stitch, asset-persistence, prompt-enhancement, gemini, supabase-storage, tdd]
one_liner: "Stitch asset persistence via httpx+Supabase Storage and Gemini Flash prompt enhancement with 4-domain DESIGN_VOCABULARY wired into generate_app_screen"

dependency_graph:
  requires:
    - 16-01  # stitch-assets bucket + DB schema
    - 16-02  # StitchMCPService + app_builder.py base tools
  provides:
    - stitch_assets.download_and_persist()
    - stitch_assets.persist_screen_assets()
    - prompt_enhancer.enhance_prompt()
    - prompt_enhancer.DESIGN_VOCABULARY
    - app_builder.enhance_description() ADK tool
    - app_builder.generate_app_screen() with enhance + persist pipeline
  affects:
    - app/agents/tools/app_builder.py
    - app/services/ (two new modules)

tech_stack:
  added:
    - httpx async download (already in deps, newly used for Stitch URLs)
    - google-genai async (client.aio.models.generate_content) via guarded import
  patterns:
    - thread executor for sync Supabase storage calls (run_in_executor)
    - try/except import guard for google.genai (matches embedding_service.py)
    - TDD — RED then GREEN for both service modules

key_files:
  created:
    - app/services/stitch_assets.py
    - app/services/prompt_enhancer.py
    - tests/unit/app_builder/test_stitch_assets.py
    - tests/unit/app_builder/test_prompt_enhancer.py
  modified:
    - app/agents/tools/app_builder.py

decisions:
  - "google.genai try/except import guard: matches project pattern from embedding_service.py — prevents ImportError in environments where google namespace package resolution is incomplete (Windows dev, some CI runners)"
  - "supabase_client import deferred inside download_and_persist body: avoids circular import during module load while keeping the httpx download and storage upload in a single async function"
  - "persist_screen_assets falls back to temp URL on error, not None: callers still receive a usable URL even if Supabase Storage is temporarily unavailable"
  - "enhance_prompt auto-detects domain from description keywords: no required parameter change for callers — backwards compatible"

metrics:
  duration: "20 min"
  completed_date: "2026-03-21"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 1
---

# Phase 16 Plan 03: Asset Persistence + Prompt Enhancer Summary

**One-liner:** Stitch asset persistence via httpx+Supabase Storage and Gemini Flash prompt enhancement with 4-domain DESIGN_VOCABULARY wired into generate_app_screen.

## What Was Built

### Task 1: Asset Persistence Service (`app/services/stitch_assets.py`)
- `download_and_persist(temp_url, storage_path, content_type)` — async httpx download of Stitch signed URL, sync Supabase upload via `run_in_executor`, returns permanent public URL string
- `persist_screen_assets(stitch_response, user_id, project_id, screen_id, variant_index)` — extracts `html_url`/`htmlUrl` and `screenshot_url`/`screenshotUrl` from Stitch response, persists both, returns `{"html_url": ..., "screenshot_url": ...}` with fallback to original URL on error and `None` when keys absent
- 3 unit tests covering: happy path, both URLs persisted, no URLs case

### Task 2: Prompt Enhancer (`app/services/prompt_enhancer.py`)
- `DESIGN_VOCABULARY` with 4 domains: bakery, saas, restaurant, fitness — each with colors, typography, mood, sections
- `ENHANCEMENT_SYSTEM_PROMPT` — structured output format: CONCEPT, VISUAL_STYLE, COLOR_PALETTE, TYPOGRAPHY, SECTIONS, IMAGERY, TONE, TARGET_AUDIENCE
- `enhance_prompt(description, domain_hint)` — auto-detects domain from description keywords, injects vocabulary context, calls `gemini-2.0-flash` async, falls back to original description on any error
- Guarded import `try/except` for `google.genai` matching project pattern
- 4 unit tests covering: structured output, domain auto-detection, Gemini error fallback, DESIGN_VOCABULARY completeness

### Task 2 (Part B): `app/agents/tools/app_builder.py` updated
- `_generate_screen_async` extended with: `enhance`, `user_id`, `project_uuid`, `screen_id`, `variant_index` parameters
- Pipeline: `enhance_prompt()` → Stitch `generate_screen_from_text` → `persist_screen_assets()` → `enhanced_prompt` field injected into result
- `enhance_description()` added as standalone ADK tool
- `APP_BUILDER_TOOLS` updated to 3 items: `[generate_app_screen, list_stitch_tools, enhance_description]`

## Verification

```
uv run pytest tests/unit/app_builder/test_prompt_enhancer.py tests/unit/app_builder/test_stitch_assets.py -v
7 passed in 9.80s

uv run ruff check app/services/stitch_assets.py app/services/prompt_enhancer.py app/agents/tools/app_builder.py
All checks passed!

from app.services.prompt_enhancer import DESIGN_VOCABULARY
['bakery', 'saas', 'restaurant', 'fitness']

from app.services.stitch_assets import download_and_persist, persist_screen_assets
# stitch_assets OK
```

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | a4ca743 | feat(16-03): add stitch_assets service |
| Task 2 | da7527c | feat(16-03): add prompt_enhancer + wire app_builder.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added try/except import guard for google.genai in prompt_enhancer.py**
- **Found during:** Task 2 smoke test
- **Issue:** `from google import genai` at module top level fails with `ImportError: cannot import name 'genai' from 'google'` in the dev environment (Windows, incomplete google namespace package resolution — same issue as other services in the project)
- **Fix:** Wrapped `from google import genai` + `from google.genai import types as genai_types` in `try/except Exception` block, assigning `None` on failure; added `if genai is None` early-return guard in `enhance_prompt()` body
- **Precedent:** Exact same pattern used in `app/rag/embedding_service.py`
- **Files modified:** `app/services/prompt_enhancer.py`
- **Commit:** da7527c

## Self-Check: PASSED

| Item | Status |
|------|--------|
| app/services/stitch_assets.py | FOUND |
| app/services/prompt_enhancer.py | FOUND |
| tests/unit/app_builder/test_stitch_assets.py | FOUND |
| tests/unit/app_builder/test_prompt_enhancer.py | FOUND |
| commit a4ca743 | FOUND |
| commit da7527c | FOUND |
