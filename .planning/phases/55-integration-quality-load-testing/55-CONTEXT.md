# Phase 55: Integration Quality & Load Testing - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 55 closes the production-readiness gaps that only show up when integrations reconnect, multiple users stream at once, and the app is stressed at realistic beta-launch load:

1. **OAuth lifecycle reliability** — connect, disconnect, and reconnect flows must leave no stale credential or sync-state residue for provider-backed integrations or Google Workspace.
2. **SSE and multi-user session isolation** — concurrent streaming must stay scoped to the authenticated user and target session so no cross-session or cross-user leakage is possible.
3. **100-user load-test readiness** — the project needs a repeatable on-demand load harness with pass/fail thresholds, connection-pool observability, and staging-ready instructions.

**Out of scope for Phase 55**:
- Shipping new integration providers or expanding provider registry breadth
- Replacing SSE with WebSockets or redesigning chat architecture
- Full production infra resizing beyond what is required to measure and verify current limits
- GDPR/data-deletion or Knowledge Vault work reserved for Phase 56
- Broad dashboard or onboarding UX changes unrelated to integration quality or concurrency behavior

</domain>

<decisions>
## Implementation Decisions

### Execution Order

- **Plan and execute Phase 55 inside GSD.** No detached checklist or side planning system.
- **Start with OAuth lifecycle truthfulness (`55-01`).** It is the clearest stale-state correctness gap already visible in the codebase.
- **Then lock down SSE session isolation (`55-02`).** This depends on understanding the final auth/integration truth paths from 55-01.
- **Finish with the repeatable load harness (`55-03`).** Reuse the existing Locust groundwork rather than inventing a new load-testing track.

### OAuth Lifecycle Boundary

- **Disconnect must clear stale operational state, not only tokens.** If sync/error rows survive a disconnect, reconnect truth becomes unreliable.
- **Google Workspace remains a special-case OAuth flow.** It uses canonical backend-owned credentials and must be handled explicitly, not assumed to behave like the generic `/integrations` registry.
- **Reconnect status must be truthful after a disconnect.** The UI and APIs should not report leftover error state or partial credentials as a healthy connection.

### SSE Isolation Boundary

- **Bearer-authenticated identity is the source of truth for chat streams.** Request-body `user_id` values must never create cross-user trust.
- **Session isolation must be tested across both backend and frontend stream layers.** The backend owns the user/session boundary; the frontend owns per-session rendering and side-effect routing.
- **No cross-session widget/activity leakage.** Background stream effects should stay scoped to the session that produced them.

### Load Harness Boundary

- **Reuse `tests/load_test` rather than replacing it.** The richer `locustfile.py` should become the canonical harness unless a clear blocker appears.
- **Pass/fail thresholds must be machine-readable.** Phase 55 should produce an on-demand report that can fail when p95, error rate, or pool-health expectations are violated.
- **Staging execution should be documented, not implied.** The runbook must explain auth, target URL, output artifacts, and how to interpret failures.

### Claude's Discretion

The executor may decide without re-asking:
- Exact file split between helpers, scripts, and tests for the load harness
- Whether Google Workspace disconnect is implemented through a dedicated route or a shared configuration helper, as long as the trust boundary remains backend-owned
- Whether SSE isolation tests are added to existing integration/frontend suites or a new focused file, as long as the coverage is behavior-first

</decisions>

<specifics>
## Specific Ideas

- `IntegrationManager.delete_credentials()` currently appears to remove only `integration_credentials`; Phase 55 should verify whether `integration_sync_state` also needs cleanup for disconnect truth.
- Google Workspace already has truthful status and callback-time sync from Phase 54, but there is not yet a dedicated disconnect lifecycle.
- The existing `tests/load_test/locustfile.py` already authenticates through Supabase, exercises SSE chat, and hits health endpoints; it looks like the right base for Phase 55 instead of the older `tests/load_test/load_test.py`.

</specifics>

<code_context>
## Existing Code Insights

### Integrations

- `app/routers/integrations.py` already owns generic OAuth authorize, callback, status, and disconnect flows.
- `app/services/integration_manager.py` stores encrypted OAuth credentials and separately stores per-provider sync/error state in `integration_sync_state`.
- `app/services/google_workspace_auth_service.py` owns canonical Google Workspace credential persistence and truthful reconnect status.
- `app/routers/configuration.py` exposes Google Workspace status and callback-time sync, but does not yet expose a dedicated disconnect path.

### SSE / Session Isolation

- `app/fast_api_app.py` derives the effective chat user from the Bearer token and uses that value when loading/creating sessions.
- `frontend/src/hooks/useBackgroundStream.ts` already scopes stream handling by `sessionId`, `visibleSessionId`, and per-session refs, but the repo lacks explicit regression coverage for cross-session leakage scenarios.
- Existing integration tests focus on SSE auth and streaming format, not same-session-id cross-user isolation behavior.

### Load Testing

- `tests/load_test/locustfile.py` already contains authenticated chat, workflow, dashboard, finance, content, and health tasks, including SSE-heavy user variants.
- `tests/load_test/README.md` documents both local and Cloud Run execution, but the docs still reference the older `load_test.py` flow and do not define explicit pass/fail thresholds.
- `app/fast_api_app.py` already exposes connection-health and SSE-capacity telemetry that a load harness can consume for pool/backpressure verification.

</code_context>

<deferred>
## Deferred Ideas

- Long-duration soak testing beyond the scoped beta-readiness thresholds
- Autoscaling policy or infrastructure-tier changes that are not required to verify the existing app behavior
- Voice-session or websocket concurrency hardening outside the SSE/chat surface

</deferred>

---

*Phase: 55-integration-quality-load-testing*
*Context gathered: 2026-04-11*
