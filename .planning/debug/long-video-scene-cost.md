---
status: awaiting_human_verify
trigger: "Investigate long-video slowness in the director pipeline and confirm the lowest-risk speed cut."
created: 2026-03-11T00:00:00Z
updated: 2026-03-11T00:00:00Z
---

## Current Focus
hypothesis: the lowest-risk speed cut is to enforce a hard Veo budget only on 60s+ storyboards, while preserving existing short-video render_type behavior.
test: verify director normalization keeps explicit render_type choices for sub-60s paths and caps long-video Veo scenes.
expecting: 60s+ runs should generate fewer Veo scenes without changing the overall long-video product contract.
next_action: human-verify with a fresh 60-second benchmark run against Vertex

## Symptoms
expected: 60-second long-video benchmark should complete much faster, ideally with fewer expensive Veo scene generations.
actual: 60-second benchmark artifacts show 4+ minutes in asset generation and then very long Remotion assembly. 12-second benchmark succeeds but still spends 418s in render/upload.
errors: no correctness error now; primary issue is runtime cost. Earlier benchmark artifacts: verify-pro-video-60s-20260311T085940Z.json and verify-pro-video-60s-20260311T091847Z.json.
reproduction: run scripts/debug/verify_pro_video.py --duration 60 against current Vertex setup.
started: after fixing provider/runtime issues, the remaining blocker is performance.

## Eliminated
- hypothesis: hidden runtime env overrides are already lowering Veo usage for 60s+ runs.
  evidence: benchmark env_overrides were empty, and the director path relied on storyboard normalization rather than an external override.
  timestamp: 2026-03-11T00:00:00Z
- hypothesis: the long-video cap should apply to every storyboard duration.
  evidence: targeted tests showed that broad remapping broke explicit render_type preservation for shorter/default paths.
  timestamp: 2026-03-11T00:00:00Z

## Evidence
- timestamp: 2026-03-11T00:00:00Z
  checked: app/services/director_service.py scene planning helpers
  found: 60s targets about 8 scenes via ceil(duration/8), while render_type budget is the real lever that decides how many expensive Veo scenes are generated.
  implication: reducing Veo usage is safer than shrinking total scene count because it preserves runtime coverage and the long-video contract.
- timestamp: 2026-03-11T00:00:00Z
  checked: artifacts/benchmarks/long_video/live/verify-pro-video-60s-20260311T085940Z.json
  found: planning_done reported 8 scenes; assets_done arrived at 260.738s; rendering then timed out before completion.
  implication: asset generation is already a dominant bottleneck for 60s runs.
- timestamp: 2026-03-11T00:00:00Z
  checked: artifacts/benchmarks/long_video/live/verify-pro-video-60s-20260311T091847Z.json
  found: planning_done again reported 8 scenes, and the run timed out before assets completed.
  implication: repeated 60s performance problems occur before final assembly completes.
- timestamp: 2026-03-11T00:00:00Z
  checked: app/services/director_service.py and tests/unit/test_director_service.py
  found: the current safe fix is to apply the render_type budget only for 60s+ runs, preserving existing explicit render_type behavior elsewhere.
  implication: the speed cut stays focused on long-video cost instead of altering unrelated storyboard behavior.
- timestamp: 2026-03-11T00:00:00Z
  checked: uv run pytest tests/unit/test_director_service.py tests/unit/test_long_video_benchmark.py -q
  found: 19 passed.
  implication: the targeted change is regression-covered and benchmark reporting still passes.

## Resolution
root_cause: 60s+ runs plan about 8 scenes, and runtime cost is driven primarily by how many of those scenes become Veo generations; the safest speed cut is a hard long-video render_type budget rather than reducing total scene coverage.
fix: gated the render_type budget so it only applies to 60s+ storyboards, keeping the long-video Veo cap while preserving short/default render_type behavior. Added a unit test asserting long videos are capped to two Veo anchor scenes.
verification: targeted unit coverage passed with uv run pytest tests/unit/test_director_service.py tests/unit/test_long_video_benchmark.py -q; full 60s Vertex benchmark still needs human verification.
files_changed: ["app/services/director_service.py", "tests/unit/test_director_service.py"]
