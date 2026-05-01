# Phase 85 — Deferred Items

## Out-of-scope discoveries during Plan 01 execution

### 1. SC4: renders that legitimately exceed 570s lose the SSE asset URL

**Discovered:** Plan 01 RESEARCH (`85-RESEARCH.md` § Q3, § SC4 Deferred-Work Documentation Plan).

**Trigger:** Any video render where `total_duration_seconds > 8` (Veo per-scene cost is ~80s × 8 scenes = ~640s — already past the new 570s SSE deadline). Slow renders driven by long prompts, full-quality settings, or transient Vertex AI rate-limiting can also push past 570s.

**What goes wrong:**
- The SSE deadline at `_SSE_MAX_DURATION_S = 570` (admin) / `SSE_MAX_DURATION_S = 570` (user) fires before the render completes.
- The user sees `Error: Stream timeout — please retry your request.` in chat (`frontend/src/hooks/useBackgroundStream.ts` does not auto-retry on `data: {error}` events — by design).
- The `runner_task.cancel()` path does NOT abort the in-flight render thread. The director's total budget is `DIRECTOR_TOTAL_TIMEOUT_SECONDS = 1200` (`app/services/director_service.py:248-252`), so the render continues server-side and the asset DOES land in the `generated-videos` bucket.
- **Net effect:** the user has lost the URL for an asset that was successfully produced. They have to re-prompt and pay the render cost twice.

**Why deferred:**
- The fix requires an async job queue (Cloud Tasks or Pub/Sub) + persistent render-status storage + frontend polling-or-SSE-resume — a multi-phase architectural change, not a hotfix.
- We cannot just raise SSE_MAX_DURATION_S past 600s without ALSO raising Cloud Run's `--timeout` (Makefile:107, cloud-run-service.yaml:118, cloudrun.yaml:20, scripts/deploy-fast.ps1:124) — and even then, Cloud Run's hard ceiling is 3600s, beyond which the only path is async.
- See `85-RESEARCH.md` § SC4 for the full architectural sketch.

**Existing mitigations:**
- **Phase 89 (Knowledge Vault Auto Sync)** — auto-ingests bucket assets so the orphaned video is still searchable in the user's vault even though the chat UI lost the URL.
- **Sentry warning logs** — `app/fast_api_app.py:1973-1976` already emits `logger.warning("SSE stream hit max duration (%ds), closing", SSE_MAX_DURATION_S)` on deadline-hit. The Sentry SDK auto-captures warnings if configured, giving ops visibility into how often this fires in production.
- **The error string contract** — `Stream timeout — please retry your request.` (em-dash) remains byte-identical so future async-resume work can detect it and trigger a status-poll without breaking the current "final error" UX.

**Proposed approach (future phase):**
1. Detect long-running renders at director-dispatch time (before SSE starts) when `expected_duration > 570`.
2. Switch those renders to an async path: enqueue a Cloud Tasks job, return an interaction_id with status='pending', and surface a "we'll notify you when it's ready" widget instead of streaming.
3. Frontend polls a `/render-status/{interaction_id}` endpoint (or subscribes via a separate short-lived SSE) and renders the asset card when the job lands in the bucket.
4. Backwards-compat: short renders (<570s expected) keep using the existing SSE path.

**Status:** Deferred. Tracked here. Will be picked up in a later phase once the async-job-queue infrastructure is needed for additional long-running operations (e.g., bulk imports, large data exports).

**Reference:** `.planning/phases/85-render-sse-timeout/85-RESEARCH.md` § SC4 Deferred-Work Documentation Plan.
