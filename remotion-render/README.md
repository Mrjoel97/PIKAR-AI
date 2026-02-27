# Remotion server-side render

Used by the backend to render programmatic videos (scenes with text) to MP4 when Vertex Veo is unavailable. The same composition as the frontend `GeneratedVideoComposition` is used so output matches the in-app preview.

## Setup

From the repo root:

```bash
cd remotion-render
npm install
```

## Usage (backend)

The Python service `app/services/remotion_render_service.py` calls:

```bash
npx remotion render src/index.tsx GeneratedVideo out.mp4 --props=props.json
```

Enable server-side render by setting:

- `REMOTION_RENDER_ENABLED=1`
- `REMOTION_RENDER_DIR` (optional): path to this package; defaults to `{repo}/remotion-render`
- `REMOTION_RENDER_TIMEOUT` (optional): seconds to wait for render; default 120

Props JSON shape: `{ "scenes": [{ "text": "...", "duration": 5 }], "fps": 30, "durationInFrames": 150 }`.

## Manual test

```bash
echo '{"scenes":[{"text":"Hello world","duration":5}],"fps":30,"durationInFrames":150}' > props.json
npx remotion render src/index.tsx GeneratedVideo out.mp4 --props=props.json
```

Then open `out.mp4`.
