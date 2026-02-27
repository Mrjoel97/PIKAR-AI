# Plan: Upgrade Remotion to "Pro" Level

## Objective
Enable creation of high-quality, long-form videos (15s to 3m) by combining **Remotion's orchestration** with **Veo 3's generation** and **Gemini's reasoning**.

## Core Concept: "AI Director"
Instead of a single "text-to-video" call, we build a pipeline where the AI acts as a director:
1.  **Scripting**: Gemini writes a script and storyboard based on the user's prompt.
2.  **Asset Generation**: 
    - **Visuals**: Generate multiple Veo 3 clips (4-6s each) or high-quality Imagen backgrounds for each scene.
    - **Audio**: Generate voiceover (TTS) and select background music.
3.  **Assembly**: Remotion stitches these assets together with pro-level transitions, captions, and effects.

## Comparison
| Feature | Current Remotion | "Pro" Remotion Plan |
| :--- | :--- | :--- |
| **Duration** | Any (but static) | 15s - 3 mins+ |
| **Visuals** | Single static image | Multi-scene (Video clips + Images) |
| **Audio** | Silent | Voiceover + Music + SFX |
| **Transitions** | None (Hard cut) | Fades, Wipes, Zooms |
| **Content** | Single text overlay | Scripted narrative with captions |

## Implementation Steps

### Phase 1: Enhanced Remotion Engine (The "Body")
Upgrade the React/Remotion code (`remotion-render`) to support rich features.
- [ ] **Multi-Clip Support**: Update `Composition.tsx` to accept a sequence of video/image assets.
- [ ] **Transitions**: Implement `remotion-transitions` (e.g., `Slide`, `Fade`) between scenes.
- [ ] **Audio Layer**: Add `<Audio />` tags for background music and voiceover tracks.
- [ ] **Dynamic Captions**: Implement time-synced captions using `remotion-best-practices/rules/display-captions.md`.

### Phase 2: The AI Director (The "Brain")
Create a new service `DirectorService` (Python) to orchestrate the process.
- [ ] **Storyboard Agent**: A specialized LLM prompt that takes a user request ("Make a 1m ad for shoes") and outputs a JSON storyboard:
    ```json
    {
      "audio_mood": "upbeat",
      "scenes": [
        {"desc": "Close up of running shoes on pavement", "duration": 4, "text": "Run faster."},
        {"desc": "Runner sprinting at sunset", "duration": 4, "text": "Go further."}
      ]
    }
    ```
- [ ] **Asset Factory**: A loop that calls `vertex_video_service` (Veo 3) for each scene in the storyboard.
- [ ] **Audio Gen**: Integration with Google Cloud TTS for voiceover.

### Phase 3: Integration
- [ ] Update `create_video` tool to use `DirectorService` for long requests.
- [ ] Update `remotion_render_service.py` to construct the complex `props` JSON required by Phase 1.

## Required "Skills" to Utilize
- `remotion-best-practices/rules/transitions.md` (smooth cuts)
- `remotion-best-practices/rules/audio.md` (mixing music/voice)
- `remotion-best-practices/rules/text-animations.md` (professional titles)
- `remotion-best-practices/rules/sequencing.md` (pacing)
