# Plan: Video creation in workspace — chat-first, no Remotion for users

**Implementation status:** Phases 1–4 implemented. Phase 1 (no video_spec on failure, agent copy, duration) and Phase 2 (server-side Remotion fallback), Phase 3 (Vertex Veo REST LRO), Phase 4 (rehydration + vault download) are in place. Enable server-side render with `REMOTION_RENDER_ENABLED=1` and install `remotion-render` (`cd remotion-render && npm install`). Veo requires `GOOGLE_CLOUD_PROJECT` and credentials.

## Goals

1. **Single place**: User creates video from the **chat** by prompting the AI (e.g. “Create a 30 second video about our new product”). No switching apps, no Remotion project, no manual render steps.
2. **Duration in natural language**: User can say 10 seconds, 15, 28, 30, 1 minute, 3 minutes. The system maps this to supported durations and creates one video.
3. **Always a finished video**: The result is a **playable MP4** that appears in chat and workspace — not code, not “video spec,” not “how to render” instructions. Non-technical users never see Remotion or run any commands.
4. **Auto-save to Knowledge Vault**: Every created video is stored in the user’s media (Knowledge Vault). User can open **Knowledge Vault → Media Files** to see, play, and **download** the video.
5. **View in workspace from chat**: Clicking the video in the chat opens it in the workspace. Same behavior for media opened from the vault (aligned with CHAT_MEDIA_PERSIST_AND_VIEW_PLAN).

---

## Current behavior (problems)

- **Veo path**: `create_video_with_veo` is the intended path for “prompt + duration” → MP4. Today `vertex_video_service.generate_video` is a **stub**: it always returns `success: False`, so every request falls back to the Remotion spec.
- **Fallback**: When Veo “fails,” the backend returns a **video_spec** widget: Remotion code + instructions (“Create a new Remotion project… Replace Root.tsx… Run npm start… Render: npx remotion render…”). Users see a preview in the Remotion Player plus “How to render to MP4” and “Show Remotion code.” That’s the opposite of “simple and in-workspace only.”
- **create_video (Remotion)**: Only ever returns a video_spec (code + instructions). There is no server-side step that renders to MP4 and saves to vault.
- **Duration**: Veo is currently clamped to 4–8 seconds in code. User wants 10, 15, 28, 30, 60, 180 seconds.
- **Result**: Users must leave the app, run Remotion, and render to MP4 themselves. Videos are not automatically in the vault as a downloadable file.

---

## Target behavior

| Step | What happens |
|------|----------------|
| 1 | User types in chat: “Create a 30 second video about our coffee launch.” |
| 2 | Agent calls the video-creation tool with prompt + duration (e.g. 30). |
| 3 | Backend either: (A) uses Veo (or other AI video API) to generate MP4, or (B) generates a programmatic spec and **server-side renders** it to MP4. |
| 4 | MP4 is uploaded to `knowledge-vault` at `media/{user_id}/{asset_id}.mp4` and a row is added to `media_assets`. |
| 5 | Backend returns a **video** widget (not video_spec) with `videoUrl` (signed or public) and `asset_id`. |
| 6 | Chat shows the video; user can click to view in workspace. After reload, rehydration uses `asset_id` (per CHAT_MEDIA_PERSIST_AND_VIEW_PLAN). |
| 7 | Knowledge Vault → Media Files lists the video; user can play, view in workspace, and **download**. |

No Remotion UI, no code, no “render to MP4” instructions for the user.

---

## Root causes to address

1. **Veo not implemented**: `vertex_video_service.generate_video` does not call the real Vertex Veo API; it always returns failure. So we never get an MP4 from Veo today.
2. **No server-side Remotion render**: When we have a programmatic video (scenes + Remotion code), there is no service that renders it to MP4 and uploads to storage. So the only option today is to return a video_spec and ask the user to render locally.
3. **Fallback exposes Remotion**: On Veo failure we return video_spec + instructions. For non-technical users we should never show that; we should either render server-side and return a video widget or show a friendly “video unavailable, try again later” message.
4. **Duration limits**: Veo’s actual API may limit duration (e.g. 4–8s). We need a clear mapping from user intent (10s, 15s, 30s, 1min, 3min) to what we can produce (e.g. cap at 8s for Veo; use Remotion render for longer).
5. **Agent wording**: Agent should never say “open Remotion” or “run npx remotion render.” It should say “Your video is ready in the chat and in Knowledge Vault; you can download it from Media Files.”

---

## Plan (implementation order)

### Phase 1: Single tool and duration handling (no user-facing Remotion)

**1.1 One primary tool for “create video from chat”**

- Treat **create_video_with_veo** as the main tool for “user wants a video from a prompt” (with optional duration). Keep **create_video** for internal use (e.g. generating a spec for server-side render) but do not expose it to the user as the path to get a video.
- Agent instructions: When the user asks for a video (any duration), use **create_video_with_veo** with the user’s prompt and parsed duration. Never direct the user to Remotion or to run any commands.

**1.2 Duration parsing and mapping**

- In the agent (or in the tool), accept flexible duration from the user: e.g. 10, 15, 28, 30 seconds; 1 minute (60); 3 minutes (180).
- In **create_video_with_veo** (and any Remotion render path), accept `duration_seconds` in a supported set (e.g. 6, 8, 10, 15, 28, 30, 60, 180). Map invalid values into the nearest supported value (e.g. 7 → 6 or 8).
- **Veo**: Check Vertex Veo docs for max duration. If the API only supports 4–8 seconds, then for “30 seconds” or “1 minute” we must use the Remotion render path (Phase 2), not Veo. Document this in code and in the plan.

**1.3 Stop returning video_spec to the user on “create video”**

- When **create_video_with_veo** fails (Veo not configured or errors):
  - **Option A (preferred for simplicity)**: Return a short, friendly message widget or tool result: “Video generation is temporarily unavailable. Please try again in a few minutes or try a shorter duration (e.g. under 10 seconds).” Do **not** return a video_spec with Remotion code and instructions. This keeps the UX consistent: “create video” either gives a video or a clear message, never “here’s code, run Remotion.”
  - **Option B**: Trigger a server-side Remotion render (Phase 2) and return the video widget when render completes. Then we still never show video_spec for this flow.

Implement Option A in Phase 1 so that we remove Remotion from the user flow immediately. Option B is Phase 2.

---

### Phase 2: Server-side Remotion render (optional but recommended)

**2.1 Render service**

- Add a backend path that, given a **video_spec** (title, scenes, remotion_code or composition id, fps, durationInFrames), renders it to MP4.
- Options:
  - **Remotion Lambda** (or Remotion’s cloud render): Backend calls Remotion’s render API with the composition; receive MP4 URL or bytes; upload to `knowledge-vault`.
  - **Self-hosted Node render**: Run `@remotion/renderer` in a Docker container or long-running worker; same input → MP4 → upload.
- Output: MP4 file in `media/{user_id}/{asset_id}.mp4`, row in `media_assets` (asset_type `video`), optional ingestion into knowledge vault for search.

**2.2 Integrate with create_video_with_veo fallback**

- When Veo is not available or fails, instead of returning video_spec to the user:
  1. Call the same logic as **create_video** to get a Remotion spec (title, scenes, remotion_code, etc.).
  2. Call the new render service with that spec.
  3. When render completes, upload MP4 to vault, insert `media_assets`, return the same **video** widget shape (videoUrl, asset_id) as when Veo succeeds.
- User always gets either a video widget or a friendly error message; never a video_spec in the “create video” flow.

**2.3 Long durations**

- For requests like “1 minute” or “3 minutes,” Veo may not support that. Use the Remotion render path with a composition that has the right duration (e.g. 60 or 180 seconds). This satisfies “user says 1 minute → they get one video file in the vault.”

---

### Phase 3: Veo implementation (real API)

- Replace the stub in **vertex_video_service.py** with a real call to Vertex AI Veo (predictLongRunning or the correct REST endpoint). Submit the job, poll until done, then read video bytes or GCS URI.
- Respect Veo’s documented duration and aspect ratio limits. Map user durations to allowed values (e.g. 4, 6, 8 seconds if that’s the limit).
- On success: same as today — upload bytes to `knowledge-vault`, insert `media_assets`, return **video** widget with asset_id and signed URL.

---

### Phase 4: Knowledge Vault and chat UX (align with existing plan)

- **Persistence and rehydration**: Rely on **CHAT_MEDIA_PERSIST_AND_VIEW_PLAN**: video widgets must have `asset_id`; on loadHistory we rehydrate signed URLs for `media/{user_id}/{asset_id}.mp4` so the video still plays after reload.
- **Vault → workspace**: In Knowledge Vault → Media Files, clicking a video should open it in the workspace (already in progress in that plan). Ensure `media_assets` and vault UI pass the correct path and get a signed URL.
- **Download**: In the vault Media Files list (or detail view), ensure each video has a **Download** action that uses the signed URL or a direct download link so the user can save the MP4. No Remotion or “export” step.

---

### Phase 5: Agent instructions and copy

- Update **app/agent.py** (and any content agent that can create video):
  - “When the user asks to create a video, use **create_video_with_veo** with the user’s prompt and the duration they asked for (e.g. 10, 15, 30 seconds, 1 minute, 3 minutes). The video will appear in the chat and be saved to Knowledge Vault → Media Files. The user can view it in the workspace by clicking it and download it from the vault. Never tell the user to open Remotion, run npm, or render to MP4.”
- Remove or soften any wording that says “video spec” or “programmatic video ready to render” in the default user-facing message. From the user’s perspective there is only “video” or “video temporarily unavailable.”

---

## Success criteria

- User can say in chat: “Create a [X second / 1 minute / 3 minute] video about [topic]” and receive a **playable video** in the chat (and workspace on click), with no code or Remotion instructions.
- Every such video is stored in Knowledge Vault → Media Files and is **downloadable**.
- After page reload, the video still appears in the chat (rehydration with asset_id).
- Non-technical users never see “Remotion,” “npx,” “Root.tsx,” or “render to MP4” in the create-video flow.

---

## Files to touch (summary)

| Area | Files |
|------|--------|
| Video tool / Veo fallback | `app/mcp/tools/canva_media.py` — stop returning video_spec on Veo failure (Option A or B); optional: trigger server-side render |
| Veo implementation | `app/services/vertex_video_service.py` — replace stub with real Veo API; duration mapping |
| Server-side Remotion | New: e.g. `app/services/remotion_render_service.py` or Supabase Edge Function + Remotion Lambda; call from canva_media when Veo fails |
| Agent instructions | `app/agent.py` — single tool (create_video_with_veo), duration wording, never mention Remotion to user |
| Duration in tools | `app/mcp/tools/canva_media.py` — accept 10, 15, 28, 30, 60, 180; map to Veo/Remotion limits |
| Chat rehydration / vault | See CHAT_MEDIA_PERSIST_AND_VIEW_PLAN: `useAgentChat.ts`, storage RLS, VaultInterface, etc. |
| VideoSpecWidget (optional) | If we fully remove video_spec from create-video flow, we can keep the widget for potential “advanced” or internal use but do not show it for normal “create video” requests. |

---

## Verification

1. In chat: “Create a 30 second video about our new product launch.” → Response includes a **video** widget (playable), no Remotion code or instructions.
2. Click the video in chat → it opens in the workspace.
3. Go to Knowledge Vault → Media Files → the same video is listed; play and **download** work.
4. Reload the page → the video still appears in the chat (rehydration).
5. Repeat with “10 seconds,” “1 minute” (if supported) and confirm duration and single-file result.

---

## Summary

- **Fix**: Make “create video” from chat always produce a **finished MP4** saved to the Knowledge Vault, viewable in chat and workspace, and downloadable — with **no Remotion steps for the user**.
- **Short term**: Use **create_video_with_veo** only; on failure return a friendly message (no video_spec). Optionally implement Veo so short clips (e.g. 6–8s) work.
- **Medium term**: Add server-side Remotion render so that when Veo is unavailable we still deliver an MP4 (including for 30s, 1min, 3min) and keep the same simple UX.

**See also:** [UNIFIED_MEDIA_CREATION_PLAN.md](./UNIFIED_MEDIA_CREATION_PLAN.md) — duration-based routing (VEO 3 vs Remotion), and agent use of Remotion + nano-banana skills for images and videos.
