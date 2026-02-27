# Agent Image Constraints – Analysis

This doc explains the two constraints the agent reported about image generation and workspace display.

---

## Constraint 1: “I do not have the capability to choose a specific image generation model like ‘nano banana pro model’”

### Where it comes from

- **Agent instructions** (`app/agent.py`) say: *“create_image: Generate AI images using nano-banana skill (vibrant, artistic style)”*.
- The tool the agent actually uses is **`create_image`** from **`app/mcp/tools/canva_media.py`**, which calls **`generate_image_with_nano_banana`** inside the same file.

### Why there is no “model” choice

1. **Single backend path**  
   `generate_image_with_nano_banana` uses one fixed configuration:
   - **Model:** `gemini-2.0-flash-exp` (hardcoded).
   - **Modality:** `response_modalities=["TEXT"]`, so the API returns **text only**, not an image. The code returns an **image spec / description**, not a real image URL.

2. **“nano banana pro” is wording, not a model**  
   The string `"nano-banana pro quality"` is only used in the **prompt** sent to Gemini (`enhanced_prompt`), not as a selectable model name. There is no separate “nano banana pro” model in the codebase.

3. **Style is the only “knob”**  
   The tool already has a **`style`** argument with presets: `vibrant`, `minimal`, `tech`, `organic`, `bold`, `surreal`, `professional` (see `NANO_BANANA_STYLES` in `canva_media.py`). The agent **can** choose style; it **cannot** choose a different “model” (e.g. “nano banana pro”) because that concept is not implemented.

### Summary

- **Root cause:** Single hardcoded model + text-only response; “nano banana pro” is prompt text, not a model.
- **Fix options:**  
  - Add an optional **`model`** (or **`preset`**) parameter to `create_image` / `generate_image_with_nano_banana` and map it to different Gemini/Imagen configs or prompts.  
  - Or document for the agent that only **style** is configurable and “nano banana pro” is a quality hint in the prompt, not a selectable model.

---

## Constraint 2: “I don’t have a direct tool or widget to display images from a URL in the workspace”

### Where it comes from

- **Image tools** return:
  - **`create_image` (nano-banana):** An **image_spec** (description, style, recommendations, optional `asset_id`). No `image_url` when using TEXT-only Gemini.
  - **`generate_image` (enhanced_tools / image_generation skill):** A **stub** that returns a placeholder `image_url` string (e.g. `"[STUB] Image would be generated for: ..."`). So even when a URL exists, it’s not a real image.

- **Workspace UI** is driven by **widgets**. Widgets are defined in:
  - **Backend:** `app/agents/tools/ui_widgets.py` (e.g. initiative_dashboard, revenue_chart, form, table, workflow, etc.).
  - **Frontend:** `frontend/src/components/widgets/WidgetRegistry.tsx` and `frontend/src/types/widgets.ts`.

### Why images don’t show in the workspace

1. **No “image” or “media” widget type**  
   The registry has: `initiative_dashboard`, `revenue_chart`, `product_launch`, `kanban_board`, `workflow_builder`, `morning_briefing`, `boardroom`, `suggested_workflows`, `form`, `table`, `calendar`, `workflow`.  
   There is **no** widget type that takes an image URL and renders it (e.g. `image` or `media`).

2. **Agent can’t “display” an image**  
   The agent can return a widget definition that gets rendered by the frontend. Since no widget type exists for “show this image URL”, the agent has no way to instruct the workspace to display an image.

### Summary

- **Root cause:** Missing widget type and component for “display image from URL” in the workspace.
- **Fix options:**  
  - Add a new widget type (e.g. `image` or `media`) with:
    - **Backend:** A small helper in `ui_widgets.py` that returns a widget definition with `type: "image"` and `data: { imageUrl, title?, alt? }`.
    - **Frontend:** In `WidgetRegistry.tsx` and `widgets.ts`, register an **ImageWidget** (or MediaWidget) that renders `<img src={imageUrl} />` (with loading/error states and optional caption).  
  - Then have the agent call this widget when it has an image URL (e.g. from a future real image generator or from stored assets).

---

## Summary table

| Constraint | Cause | Location | Possible fix |
|------------|--------|----------|--------------|
| Cannot choose “nano banana pro” (or other) model | Single hardcoded model; “nano banana pro” is prompt text only | `app/mcp/tools/canva_media.py` (`generate_image_with_nano_banana`) | Add optional `model`/`preset` parameter and/or document that only `style` is selectable. |
| Cannot display image in workspace | No widget type for “image from URL” | `app/agents/tools/ui_widgets.py`, `frontend/.../WidgetRegistry.tsx`, `widgets.ts` | Add `image` (or `media`) widget type and component; have agent return it when it has an image URL. |

Implementing these fixes would allow the agent to (1) expose a model/preset choice if you add it, and (2) show generated (or any) images in the workspace when a URL is available.

---

## Can "nano banana pro" be accessed from the Vertex API?

**No.** "Nano banana pro" is **not** a Vertex AI model name. In this codebase it is only a phrase used in the prompt ("nano-banana pro quality"). Google’s official Vertex AI docs do not list any model with that name.

**What you can use on Vertex for image generation:**

| Type | Examples (Vertex) |
|------|-------------------|
| **Imagen** | `imagen-4.0-generate-001`, `imagen-4.0-fast-generate-001`, `imagen-4.0-ultra-generate-001`, `imagen-3.0-generate-002`, `imagen-3.0-generate-001`, `imagen-3.0-fast-generate-001` |
| **Gemini image** | **Gemini 2.5 Flash Image** (image generation + conversational editing), **Gemini 3 Pro Image** (preview; high-fidelity image generation) |

So you **can** use the Vertex API for real image generation, but by calling **Imagen** or **Gemini 2.5 Flash Image / Gemini 3 Pro Image** by their official names, not "nano banana pro." To support a "nano banana pro"–style quality in your app, you could map that label to one of these models (e.g. Imagen 4 or Gemini 3 Pro Image) in your backend.
