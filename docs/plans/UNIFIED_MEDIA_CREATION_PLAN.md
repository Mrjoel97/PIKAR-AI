# Plan: Unified Media Creation — Remotion, Imagen, VEO 3, and Skills

**Status:** Implemented (Phases 1, 2, 4). Credentials: use `secrets/my-project-pk-484623-c72b7850d9d5.json` (or set `GOOGLE_APPLICATION_CREDENTIALS` / `VERTEX_CREDENTIALS_PATH`).  
**Goal:** When server-side Remotion is enabled, agents use **VEO 3** for short videos (within API limits), **Remotion** for longer or programmatic videos, and **Google Imagen** (nano-banana skill) for images — with clear routing so users get high-quality images, videos, infographics, and animated content based on what they request. Agents must utilize both **Remotion skills** and **nano-banana skills** in media creation.

---

## 1. Context and current state

### 1.1 Existing pieces

| Capability | Implementation | Limits / notes |
|------------|----------------|----------------|
| **Images** | `create_image` → `generate_image_with_nano_banana` → `vertex_image_service` (Imagen 4/3) | Nano-banana = style presets + prompt enhancement; stored in Knowledge Vault. |
| **Short video** | `create_video_with_veo` → `vertex_video_service` (Veo 3/2) | Veo 3: typically **4–8 s** per clip; extension APIs can go longer but add complexity. |
| **Long / programmatic video** | Server-side Remotion fallback in `create_video_with_veo` when Veo fails; `remotion_render_service.render_scenes_to_mp4` | Triggered only after Veo fails; duration from user (e.g. 30, 60, 180 s) passed to Remotion. |
| **Remotion (spec only)** | `create_video` → `generate_video_with_remotion` | Returns video_spec (code + instructions); no MP4 unless server-side render is used elsewhere. |
| **Social graphic** | `create_social_graphic` → uses nano-banana for image + platform dimensions | Image + caption. |

### 1.2 Gaps to address

1. **Duration-based routing:** Today we always try Veo first and cap to 4–8 s. If the user asks for “30 second video” or “2 minute video,” we should **route directly to Remotion** when server-side render is enabled, instead of trying Veo and then falling back.
2. **Explicit use of Remotion skill:** Agent instructions don’t tell the model to use **Remotion skill** (`.claude/skills/remotion`) when generating programmatic/scene-based video (compositions, animations, sequencing). Remotion skill should be referenced for quality and patterns.
3. **Explicit use of nano-banana skill:** Agent instructions mention “nano-banana” but don’t point to the **nano-banana skill** (`.agents/skills/nano-banana`) for prompting strategy (vibrancy, surrealism, cohesion, example prompts). Image creation should align with that skill.
4. **Single entry point and routing:** User says “create a video” or “create an image” or “create an infographic.” We need one coherent **routing and tool-selection strategy** so the right backend (VEO 3, Remotion, Imagen) is used by the agent.
5. **Infographics and animated images:** No dedicated path; can be modeled as “image with specific style” (Imagen + nano-banana) or “short animated / motion graphic” (Remotion with short duration or GIF-like output).

---

## 2. Goals

1. **Duration-aware video routing**  
   - User asks for video **≤ ~8 s** → use **VEO 3** (then fallback to Remotion if Veo fails).  
   - User asks for video **> 8 s** (e.g. 30 s, 1 min, 3 min) and server-side Remotion is enabled → use **Remotion** path directly so they get one MP4 in the vault without hitting Veo limits.

2. **Agents use Remotion and nano-banana skills**  
   - When generating **programmatic / scene-based / long video**: agent is instructed to apply **Remotion skill** (compositions, sequencing, frame-based animation, assets).  
   - When generating **images** (including for infographics, hero visuals, social): agent is instructed to apply **nano-banana skill** (vibrancy, surrealism, cohesion, prompting strategy).

3. **Unified media creation UX**  
   - One coherent set of tools and instructions so the agent chooses:  
     - **Image** → Imagen (nano-banana skill).  
     - **Short video** → VEO 3 (with Remotion fallback).  
     - **Long video / programmatic / animated** → Remotion (server-side when enabled).  
     - **Infographic / static graphic** → Imagen + nano-banana.  
     - **Animated graphic / motion** → Remotion (short composition) or VEO 3 depending on duration and style.

4. **High quality**  
   - Images: Imagen 4/3 + nano-banana style presets and prompting.  
   - Short video: VEO 3 (with fallback).  
   - Long video: Remotion with skill-guided composition and server-side render.

---

## 3. Duration and routing constants

| Source | Short video (use VEO 3) | Long video (use Remotion when enabled) |
|--------|-------------------------|----------------------------------------|
| **VEO 3 API** | 4–8 s typical per generation | N/A (extension possible but not required for this plan) |
| **This plan** | ≤ 8 s | > 8 s (e.g. 10, 15, 28, 30, 60, 180 s) |

- **VEO_MAX_DURATION_SECONDS = 8** (configurable via env if needed).  
- When **requested duration > VEO_MAX_DURATION_SECONDS** and **REMOTION_RENDER_ENABLED=1**: backend uses **Remotion path only** (no Veo call for that request).  
- When requested duration ≤ 8 s: try Veo first; on failure, use Remotion fallback as today.

---

## 4. Implementation plan

### Phase 1: Backend — duration-based routing in `create_video_with_veo`

**Owner:** Backend (canva_media + config).

1. **Define constant**  
   - e.g. `VEO_MAX_DURATION_SECONDS = 8` (or from env `VEO_MAX_DURATION_SECONDS`).

2. **In `create_video_with_veo` (or shared helper):**  
   - If `duration_seconds > VEO_MAX_DURATION_SECONDS` and `REMOTION_RENDER_ENABLED` is true:  
     - **Skip Veo.**  
     - Call Remotion render path directly (same as current fallback: build scenes from prompt + duration, `render_scenes_to_mp4`, upload to vault, return video widget).  
   - Else:  
     - Call Veo as today; on failure, use existing Remotion fallback.

3. **Optional:** Add a small helper e.g. `should_use_remotion_for_duration(duration_seconds: int) -> bool` so both tool logic and (if needed) agent-facing docstrings stay in sync.

**Files:**  
- `app/mcp/tools/canva_media.py`  
- Optional: `app/services/remotion_render_service.py` (only if we move the “should use Remotion” check into a shared place).

**Acceptance:**  
- User asks “create a 30 second video about X” with Remotion enabled → backend uses Remotion only, returns one MP4 in vault.  
- User asks “create a 6 second video about X” → backend tries Veo first, then Remotion on failure.

---

### Phase 2: Agent instructions — media creation and skills

**Owner:** Agent / prompts.

1. **Unified media creation section**  
   Update the main agent (e.g. `app/agent.py`) “Media Creation” block so that:

   - **Images (including infographics, hero visuals, social):**  
     - Use `create_image` with appropriate style.  
     - **Apply the nano-banana skill** (`.agents/skills/nano-banana`): high-fidelity, vibrant, surreal when appropriate; use the skill’s prompting strategy (subject, style, lighting, composition) and example prompts to improve quality.

   - **Videos:**  
     - **Short (e.g. ≤ 8 seconds):** Prefer `create_video_with_veo` (VEO 3). User gets one MP4; if the tool fails, the tool’s response will say so and may still return a Remotion-rendered video when available.  
     - **Long (e.g. 10+ seconds, 30 s, 1 min, 3 min):** Use `create_video_with_veo` with the user’s duration — the backend will use Remotion when server-side render is enabled.  
     - **Programmatic / scene-based / “animated explainer” / multi-scene:** Prefer `create_video_with_veo` with a clear prompt that describes scenes/duration; for complex compositions, **use the Remotion skill** (`.claude/skills/remotion`) for composition structure, sequencing, and animation patterns. The same backend path can still be Remotion when duration > 8 s or when Veo fails.

   - **Infographics:**  
     - Use `create_image` with a prompt that describes the infographic (e.g. “infographic about X, clear sections, icons, minimal text labels”). Use **nano-banana skill** for style and cohesion.

   - **Animated images / short motion graphics:**  
     - If the user wants a short animated clip (e.g. &lt; 10 s): use `create_video_with_veo` with that duration.  
     - If they want a multi-scene or template-style animation: use `create_video_with_veo` with a descriptive prompt; backend may use Remotion; agent should apply **Remotion skill** for structure.

2. **Explicit skill references**  
   - In the same instructions, add two short bullets:  
     - “For **images** (including infographics and hero visuals), follow the **nano-banana skill** for prompting and style (vibrancy, cohesion, example prompts).”  
     - “For **programmatic or long videos** (scene-based, animated), follow the **Remotion skill** for compositions, sequencing, and frame-based animation where relevant.”

3. **No user-facing Remotion/Veo jargon**  
   - Keep existing rule: never tell the user to “open Remotion,” “run npx,” or “render to MP4.” The agent only describes outcomes: “Your video/image is in the chat and in Knowledge Vault → Media Files.”

**Files:**  
- `app/agent.py` (and any specialist agents that expose media tools, e.g. content/marketing).

**Acceptance:**  
- Agent chooses `create_image` for “create an infographic about X” and uses nano-banana-style prompting.  
- Agent chooses `create_video_with_veo` for “create a 1 minute video” and does not try to suggest local Remotion.  
- Documentation or in-code comments reference Remotion and nano-banana skills by path/name.

---

### Phase 3: Remotion skill usage in server-side composition (optional enhancement)

**Owner:** Backend / Remotion.

1. **Richer compositions**  
   - Today `remotion_render_service._scenes_from_prompt` builds a single-scene (or simple multi-scene) spec. Optionally, use patterns from the **Remotion skill** (e.g. sequencing, interpolate, useCurrentFrame) when generating scene list or when we have a future “advanced” Remotion composition generator (e.g. from canva_media or a dedicated module).  
   - This can be a follow-up: e.g. “scene breakdown” that matches Remotion skill’s composition and timing best practices.

2. **No change to user flow**  
   - Still one tool call; backend still returns one MP4. This phase is about quality of the generated Remotion composition, not UX.

**Files:**  
- `app/services/remotion_render_service.py`  
- Optionally: `app/mcp/tools/canva_media.py` (if we add a Remotion-composition generator that consumes skill-inspired patterns).

**Acceptance:**  
- Server-rendered Remotion videos follow Remotion skill guidance (e.g. frame-based timing, sequencing) where applicable.

---

### Phase 4: Tool descriptions and docstrings

**Owner:** Backend.

1. **create_video_with_veo**  
   - Docstring: Clarify that for **durations longer than 8 seconds**, the system uses server-side Remotion when enabled, so the user can request 10, 15, 30, 60, or 180 seconds and receive one MP4.

2. **create_image**  
   - Docstring: Mention that generation uses **Imagen** with **nano-banana** style presets and that the agent should apply the nano-banana skill for best quality (vibrancy, cohesion, prompting).

3. **create_video** (Remotion spec)  
   - Docstring: State that this is for **programmatic/scene-based** video; for “one prompt → one MP4” the agent should prefer `create_video_with_veo`, which may use Remotion under the hood when duration is long or Veo fails.

**Files:**  
- `app/mcp/tools/canva_media.py`

**Acceptance:**  
- LLM and developers reading the code see clear routing and skill usage.

---

## 5. Summary table: when each backend is used

| User request | Primary path | Fallback / notes |
|--------------|--------------|------------------|
| Image (any) | Imagen (nano-banana) | — |
| Infographic | Imagen (nano-banana) | Same as image with infographic-style prompt |
| Short video (≤ 8 s) | VEO 3 | Remotion if Veo fails and REMOTION_RENDER_ENABLED=1 |
| Long video (> 8 s) | Remotion (when enabled) | — (Veo not called) |
| Programmatic / multi-scene video | Remotion (when enabled) or Veo then Remotion | Agent uses Remotion skill for composition guidance |

---

## 6. Skills to be utilized

| Skill | Path | Use in media creation |
|-------|------|------------------------|
| **Remotion** | `.claude/skills/remotion` | Programmatic/long video: compositions, sequencing, frame-based animation, assets. Referenced in agent instructions and (optionally) in server-side composition generation. |
| **nano-banana** | `.agents/skills/nano-banana` | All image generation: prompting strategy, vibrancy, surrealism, cohesion, example prompts. Referenced in agent instructions and in `create_image` / nano-banana tooling. |

---

## 7. Configuration

| Env / config | Purpose |
|--------------|--------|
| `REMOTION_RENDER_ENABLED=1` | Enable server-side Remotion; allows long-duration video and Remotion fallback. |
| `VEO_MAX_DURATION_SECONDS` (optional) | Default 8; requests above this use Remotion when Remotion is enabled. |
| `REMOTION_RENDER_DIR`, `REMOTION_RENDER_TIMEOUT` | Existing; unchanged. |
| `GOOGLE_CLOUD_PROJECT` | Required for Veo and Imagen. |
| **Google credentials (Veo / Imagen)** | Place key file at `secrets/my-project-pk-484623-c72b7850d9d5.json` (repo root relative). The app uses it by default if present. Alternatively set `GOOGLE_APPLICATION_CREDENTIALS` or `VERTEX_CREDENTIALS_PATH` to that path. See `app/fast_api_app.py` credential resolution. |

---

## 8. Files to touch (summary)

| Area | Files |
|------|--------|
| Duration routing | `app/mcp/tools/canva_media.py` — branch on duration and REMOTION_RENDER_ENABLED; call Remotion first when duration > 8 s. |
| Agent instructions | `app/agent.py` — unified media section; when to use Veo vs Remotion; nano-banana and Remotion skill references. |
| Tool docstrings | `app/mcp/tools/canva_media.py` — create_video_with_veo, create_image, create_video. |
| Remotion composition (optional) | `app/services/remotion_render_service.py` — align scene generation with Remotion skill patterns. |
| Specialist agents | Any agent that exposes create_image / create_video_with_veo (e.g. content, marketing) — same skill and routing guidance. |

---

## 9. Verification

1. **Long video:** “Create a 30 second video about our product launch.” → One MP4 in chat and vault; no Remotion instructions to user; backend used Remotion (with Remotion enabled).  
2. **Short video:** “Create a 6 second clip of a sunset.” → One MP4; Veo tried first; if Veo fails, Remotion fallback used when enabled.  
3. **Image:** “Create a hero image for our AI platform.” → Image widget; prompt reflects nano-banana style (vibrancy, composition).  
4. **Infographic:** “Create an infographic about our Q4 metrics.” → Image widget; infographic-style prompt + nano-banana.  
5. **Skills:** Agent instructions explicitly mention using Remotion skill for programmatic/long video and nano-banana skill for images.

---

## 10. Success criteria

- When server-side Remotion is enabled, **requests for video longer than VEO’s duration limit (e.g. 8 s) use Remotion directly** so users get one MP4 without hitting Veo limits.  
- Agents **use both Remotion and nano-banana skills** for media creation as specified in instructions.  
- Users get **high-quality images** (Imagen + nano-banana) and **videos** (VEO 3 for short, Remotion for long) and can request **infographics** and **animated content** through the same chat flow with the right backend chosen automatically.
