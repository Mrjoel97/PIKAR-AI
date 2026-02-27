# Plan: Vertex Image/Video + Gemini 3 Pro/Flash Fallback

This plan covers:
1. **Agent LLM**: Gemini 3 Pro as primary, Gemini 3 Flash as fallback.
2. **Image generation**: Vertex (Imagen 4 + Gemini image fallback), with "nano banana pro" mapped to this pipeline; **no Canva MCP required** — users can generate images directly via the agent.
3. **Video**: Remotion skill for programmatic video + Vertex Veo for AI-generated video with primary/fallback; **video storage and in-app playback are required** for all users.
4. **Knowledge Vault**: All generated images and videos are **automatically stored** in the Knowledge Vault under the **Media files** tab and made available to the agent for reference.

---

## Part 1: Agent model – Gemini 3 Pro with Gemini 3 Flash fallback

### Current state
- **`app/agents/shared.py`**: `get_model(model_name: str = "gemini-2.5-flash")` returns a single Gemini model.
- **`app/agent.py`**: Executive agent uses `get_model("gemini-2.5-flash")`.
- **`app/services/user_agent_factory.py`**: Builds agent with `Gemini(model="gemini-2.5-pro")`.
- All specialized agents use `get_model()` (default gemini-2.5-flash).

### Target behavior
- Prefer **Gemini 3 Pro** for the main agent (and optionally for user-built agents).
- If Gemini 3 Pro is unavailable (quota, region, 404, or other error), automatically use **Gemini 3 Flash** as fallback.

### Implementation steps

| Step | Task | Location / approach |
|------|------|---------------------|
| 1.1 | Add **model fallback** support in shared layer | **`app/agents/shared.py`**: New `get_model_with_fallback(primary: str, fallback: str)` (or extend `get_model`) that returns a wrapper or the first model that succeeds. Alternatively: keep a single `get_model()` but change default to `"gemini-3.0-pro"` and implement **retry with fallback** inside the runner/ADK call site (e.g. on 404/429, retry with `gemini-3.0-flash`). Cleanest: **`get_model()`** accepts optional `fallback`; factory builds a model that the runner can swap on failure (if ADK supports), or we catch at run_sse and retry with fallback model. |
| 1.2 | Define Gemini 3 model names | Use Vertex model IDs, e.g. `gemini-3.0-pro` (or exact ID from [Vertex models](https://cloud.google.com/vertex-ai/generative-ai/docs/models)) as primary, `gemini-3.0-flash` as fallback. Confirm exact strings in Vertex docs. |
| 1.3 | Wire Executive Agent to Pro + fallback | **`app/agent.py`**: Use the new getter, e.g. `get_model("gemini-3.0-pro", fallback="gemini-3.0-flash")` or equivalent. |
| 1.4 | Wire User Agent Factory | **`app/services/user_agent_factory.py`**: Use Gemini 3 Pro with Gemini 3 Flash fallback instead of hardcoded `gemini-2.5-pro`. |
| 1.5 | Optional: specialized agents | Decide whether all sub-agents use the same Pro/Flash fallback or keep 2.5-flash for cost. If same tier: pass same getter from shared. |

### Fallback trigger
- Treat as “Pro not accessible” when: model returns 404 (model not in region), 429 (quota), or other non-transient error that indicates “use another model.”
- Implementation option A: **Runner-level** – in `run_sse` or wherever `runner.run_async` is called, catch failure, retry once with fallback model (requires building a second agent or swapping model on the same agent if ADK allows).  
- Option B: **Model wrapper** – if ADK’s Gemini class allows a custom client that tries primary then fallback, implement that.  
- Option C: **Config-driven** – env var `GEMINI_AGENT_MODEL_PRIMARY` / `GEMINI_AGENT_MODEL_FALLBACK`; at startup or first request, resolve which model is available and set that as the single model (no per-request fallback).  

Recommendation: start with **Option C** (resolve primary/fallback at startup or first use) to avoid touching ADK internals; if you need per-request fallback on 429, add Option A later.

---

## Part 2: Image generation – Vertex Imagen 4 + Gemini image fallback (“nano banana pro”)

### Current state
- **`app/mcp/tools/canva_media.py`**: `generate_image_with_nano_banana()` uses `genai.Client()` and `gemini-2.0-flash-exp` with `response_modalities=["TEXT"]` → returns text description only, no image bytes/URL.
- **`create_image`** in same file calls that; agent uses it for “nano banana” style.

### Target behavior
- Use **Vertex AI** for real image generation.
- **Primary**: Imagen 4 (e.g. `imagen-4.0-generate-001`).
- **Fallback**: When Imagen is not available (region, quota, or error), use **Gemini 3 Pro Image** (or **Gemini 2.5 Flash Image** if 3 Pro Image is not in region).
- Keep **“nano banana pro”** as a **style/preset**: same prompt enhancements (vibrant, artistic, etc.) but send the request to Vertex image API instead of text-only Gemini.

### Implementation steps

| Step | Task | Location / approach |
|------|------|---------------------|
| 2.1 | **Vertex image client** | New module, e.g. **`app/services/vertex_image_service.py`** (or under `app/mcp/tools/`). Use Vertex AI Python SDK or REST: [Generate images with Imagen](https://cloud.google.com/vertex-ai/generative-ai/docs/image/generate-images). Implement `generate_image(prompt, size/aspect_ratio, style_hint=None)` that: (1) calls Imagen 4 (`imagen-4.0-generate-001`); (2) on failure or “model not available”, retries with Gemini 2.5 Flash Image / Gemini 3 Pro Image (exact model ID from Vertex image docs). Return image bytes or a temporary URL (e.g. after uploading to Supabase Storage or returning base64 for the frontend). |
| 2.2 | **Map “nano banana pro” to style** | Keep existing style presets (vibrant, minimal, tech, etc.) and the enhanced prompt text (“nano-banana pro quality”, etc.). Pass that enhanced prompt into the Vertex image service; no separate “nano banana pro” model, only prompt styling. |
| 2.3 | **Wire canva_media to Vertex** | In **`app/mcp/tools/canva_media.py`**: Replace or wrap the current Gemini text-only path in `generate_image_with_nano_banana` with a call to the new Vertex image service. Preserve existing args (prompt, style, dimensions, user_id) and storage of result in `media_assets`; add fields for `image_url` or `image_bytes_base64` when Vertex returns an image. |
| 2.4 | **Auth and project** | Use same Vertex/GCP credentials as the rest of the app (e.g. `GOOGLE_APPLICATION_CREDENTIALS` or ADC). Ensure project and region support Imagen + Gemini image (see [Vertex locations](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations)). |
| 2.5 | **Optional: image widget** | So the agent can show the generated image in the workspace, add an **image widget** (see `docs/AGENT_IMAGE_CONSTRAINTS_ANALYSIS.md`): backend returns widget definition with `imageUrl` or base64; frontend registers an `image` widget type and renders it. Can be a follow-up task. |

### Model IDs (confirm in Vertex docs)
- Imagen 4: `imagen-4.0-generate-001` (primary).
- Fallback: `gemini-2.5-flash-preview-05-20` (image) or Gemini 3 Pro Image equivalent when available in your region.

---

## Part 3: Video – Remotion skill + Vertex Veo with fallback

### Current state
- **Remotion** in **`app/mcp/tools/canva_media.py`**: `generate_video_with_remotion()` produces **Remotion React code** (programmatic video): composition, sequences, scene components. No AI-generated video bytes; user runs Remotion locally to render.
- **Vertex Veo** is for **text-to-video** (and image-to-video): generates actual video output (e.g. 4–8 seconds, 1080p).

### Target behavior
- **Remotion**: Keep as-is for “programmatic” / “template-based” video (code generation). No change to model fallback; Remotion is code, not an LLM.
- **AI-generated video**: Add a **Vertex Veo** path for when the user (or agent) wants “generate a video from this prompt.” Use **Veo 3** (e.g. `veo-3.0-generate-001` or `veo-3.1-generate-001`) as **primary**, and **Veo 2** or **Veo 3 Fast** as **fallback** when the primary is not available.
- **Unified “video” tool**: Agent can have one video tool that:
  - Accepts a mode or intent: `remotion` (code/template) vs `veo` (AI from prompt), or
  - Chooses automatically: e.g. “create a marketing video from this script” → Veo; “create a Remotion composition with these scenes” → Remotion.

### Implementation steps

| Step | Task | Location / approach |
|------|------|---------------------|
| 3.1 | **Vertex Veo service** | New module, e.g. **`app/services/vertex_video_service.py`**. Use [Veo on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/veo-video-generation): text-to-video (and optionally image-to-video). Implement `generate_video(prompt, duration_seconds=6, aspect_ratio=..., primary_model="veo-3.0-generate-001", fallback_model="veo-2.0-generate-001" or veo-3.0-fast). Return video bytes or GCS/Storage URL. |
| 3.2 | **Fallback logic** | On 404/429/model-not-available, retry with fallback Veo model. Same region/credential pattern as image. |
| 3.3 | **Remotion unchanged** | Keep `generate_video_with_remotion()` for code-based video. Optionally add a **Remotion skill** doc or prompt so the agent knows when to use Remotion vs Veo (e.g. “template/scene-based” → Remotion; “describe a video in one sentence” → Veo). |
| 3.4 | **Agent video tool(s)** | Either: (A) Add a new tool `create_video_with_veo(prompt, duration, ...)` and keep `create_video` (Remotion) as-is; or (B) Extend `create_video` (or canva_media entrypoint) with a parameter `method: "remotion" | "veo"` and dispatch to Remotion vs Vertex Veo. Document in agent instructions when to use which. |
| 3.5 | **Storage and display** | Store Veo-generated videos in Supabase Storage (or GCS); return URL to frontend. Optional: add a **video widget** (or reuse a “media” widget) to play the URL in the workspace. |

### Model IDs (Veo, confirm in Vertex docs)
- Primary: `veo-3.0-generate-001` or `veo-3.1-generate-001`.
- Fallback: `veo-2.0-generate-001` or `veo-3.0-fast-generate-001`.

---

## Part 4: Configuration and environment

| Item | Purpose |
|------|--------|
| **Vertex project / region** | Same as existing Gemini usage; ensure [Imagen](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations) and [Veo](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations) are available in that region. |
| **Env vars (optional)** | E.g. `VERTEX_IMAGE_MODEL_PRIMARY`, `VERTEX_IMAGE_MODEL_FALLBACK`; `VERTEX_VIDEO_MODEL_PRIMARY`, `VERTEX_VIDEO_MODEL_FALLBACK`; `GEMINI_AGENT_MODEL_PRIMARY`, `GEMINI_AGENT_MODEL_FALLBACK`. Defaults: Imagen 4, Gemini image; Veo 3, Veo 2/Fast; Gemini 3 Pro, Gemini 3 Flash. |
| **Feature flags** | Optional: disable Vertex image/Veo if keys or quota are not set; fall back to current behavior (text-only image spec, Remotion-only video). |

---

## Part 5: Order of implementation (suggested)

1. **Gemini 3 Pro + Flash fallback** (Part 1) – single shared change, immediate benefit for all agents.
2. **Vertex image service + canva_media wiring** (Part 2) – real images and “nano banana pro” style.
3. **Image widget** (optional) – so generated images show in workspace.
4. **Vertex Veo service + video tool** (Part 3) – AI video with fallback; keep Remotion for code-based video.
5. **Video storage + optional video widget** – so generated videos are playable in-app.

---

## Summary table

| Area | Primary | Fallback | Notes |
|------|--------|----------|--------|
| **Agent LLM** | Gemini 3 Pro | Gemini 3 Flash | `get_model()` / runner or config-driven. |
| **Image** | Imagen 4 (`imagen-4.0-generate-001`) | Gemini 3 Pro Image / 2.5 Flash Image | New Vertex image service; “nano banana pro” = prompt style. |
| **Video (AI)** | Veo 3 (`veo-3.0-generate-001` or 3.1) | Veo 2 or Veo 3 Fast | New Vertex video service; Remotion stays for code-based video. |

All model IDs should be double-checked against the latest [Vertex AI models](https://cloud.google.com/vertex-ai/generative-ai/docs/models) and [model reference](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/) pages for your project and region.
