---
status: awaiting_human_verify
trigger: "Investigate issue: vertex-tts-voiceover-benchmark"
created: 2026-03-11T00:00:00Z
updated: 2026-03-11T00:40:00Z
---

## Current Focus
hypothesis: The remaining blocker to a voiced 60s benchmark is external GCP API enablement; code now exposes voiceover absence as a benchmark failure when requested.
test: Have the user enable Cloud Text-to-Speech API for project `pikar-ai`, then rerun the benchmark with `--require-voiceover` and confirm scenes include voiceover.
expecting: After API enablement, the benchmark should stop failing with `SERVICE_DISABLED`; if voiceover is still absent, the new benchmark guardrail should fail with `voiceover_required_but_missing` instead of silently passing.
next_action: user enables API and reruns the voiced 60s benchmark

## Symptoms
expected: google-cloud-texttospeech should be installed, VoiceoverService should synthesize audio with the Vertex service account, and the 60s long-video benchmark should include scene voiceover.
actual: package import was missing earlier; dependency was added and installed. Import now works in the real venv, but a live TTS smoke test returned 403 SERVICE_DISABLED for Cloud Text-to-Speech API in project pikar-ai (project number 940109926661). Because of that, long-video benchmarks still run without voiceover.
errors: 403 Cloud Text-to-Speech API has not been used in project 940109926661 before or it is disabled. reason=SERVICE_DISABLED.
reproduction: Load env with GOOGLE_APPLICATION_CREDENTIALS pointing at secrets/pikar-ai-19beab383665.json, GOOGLE_CLOUD_PROJECT=pikar-ai, GOOGLE_CLOUD_LOCATION=us-central1, then run a direct synthesize_speech smoke using app.services.voiceover_service.synthesize_speech.
started: This started during the long-video optimization work on March 11, 2026. The dependency install/import issue was partially fixed, and the remaining blocker appears to be GCP API enablement.

## Eliminated
- hypothesis: The remaining issue is still a missing Python dependency/import.
  evidence: `app/services/voiceover_service.py` now imports `google.cloud.texttospeech`, and the user-reported live smoke already moved past import into a real API 403.
  timestamp: 2026-03-11T00:20:00Z

## Evidence
- timestamp: 2026-03-11T00:00:00Z
  checked: skill and codebase entry points
  found: `gsd-debug` instructions are available locally, and the repo contains `app.services.voiceover_service`, long-video benchmark scripts, and director tests referencing `synthesize_speech`.
  implication: We can continue the paused investigation with persistent state and inspect the exact production code path.
- timestamp: 2026-03-11T00:12:00Z
  checked: `app/services/voiceover_service.py`
  found: The service uses `google.cloud.texttospeech.TextToSpeechClient()` directly with ADC/project env and returns `{success: False, error: str(exc)}` on API failures.
  implication: The reported 403 SERVICE_DISABLED is consistent with the real runtime path; this is not a dormant or unused code path.
- timestamp: 2026-03-11T00:15:00Z
  checked: `app/services/director_service.py`
  found: Scene processing attempts voiceover generation, but `_generate_voiceover_asset_for_scene` returns `(None, None, None)` whenever TTS fails, and rendering still proceeds.
  implication: Voiceover failures are intentionally non-fatal, so the product can render a silent video.
- timestamp: 2026-03-11T00:18:00Z
  checked: `app/services/long_video_benchmark.py`
  found: Benchmark success only requires a final `video_url`; before the fix it did not count voiceover presence and `is_healthy_report()` ignored voiceover entirely.
  implication: A long-video benchmark could pass even when every scene was missing voiceover, masking the external TTS blocker.
- timestamp: 2026-03-11T00:35:00Z
  checked: benchmark/report code changes
  found: Added voiceover coverage metrics plus `require_voiceover` plumbing to service benchmark scripts so voiced runs can fail fast with `voiceover_required_but_missing`.
  implication: Once the API is enabled, reruns will explicitly validate voiceover instead of silently succeeding without it.
- timestamp: 2026-03-11T00:37:00Z
  checked: local verification commands
  found: `uv run python -m py_compile ...` succeeded for the edited files, while `uv run pytest tests/unit/test_long_video_benchmark.py -q` was blocked by the local environment (`PermissionError` reading `.venv\Lib\site-packages\typing_extensions.py` plus `.pth` warnings from `google_cloud_aiplatform`).
  implication: The edited Python files parse, but full unit-test verification is currently limited by the local virtualenv state.

## Resolution
root_cause: Cloud Text-to-Speech API is disabled for project `pikar-ai`, causing TTS synthesis to fail with 403. Separately, the benchmark health model previously treated silent videos as healthy, so the blocker was not surfaced in benchmark results.
fix: Added voiceover coverage accounting and an opt-in `require_voiceover` gate to the long-video service benchmark/report path, and exposed `--require-voiceover` in the debug benchmark scripts.
verification: `uv run python -m py_compile app/services/long_video_benchmark.py scripts/debug/verify_pro_video.py scripts/debug/benchmark_long_video.py tests/unit/test_long_video_benchmark.py` completed successfully. Full pytest verification remains blocked by local `.venv` permission/import issues unrelated to the code change.
files_changed: ["app/services/long_video_benchmark.py", "scripts/debug/verify_pro_video.py", "scripts/debug/benchmark_long_video.py", "tests/unit/test_long_video_benchmark.py"]
