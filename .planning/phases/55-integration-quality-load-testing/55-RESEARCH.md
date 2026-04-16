# Phase 55: Integration Quality & Load Testing - Research

**Researched:** 2026-04-11
**Status:** Complete

## Research Question

What is the lowest-risk way to close the remaining v7 integration and concurrency gaps without creating a parallel testing system outside the current GSD workflow?

## Findings

### 1. The repo already has a substantial load-testing base, but it is not yet a governed Phase 55 contract

- `tests/load_test/locustfile.py` already supports:
  - Supabase password auth
  - token refresh
  - authenticated SSE chat traffic
  - workflow, dashboard, finance, content, and approval endpoints
  - health endpoint probing
  - chat-heavy stress users
- `tests/load_test/README.md` already documents local and Cloud Run execution.
- The missing piece is not “a load harness from scratch”; it is:
  - one canonical harness path
  - explicit thresholds
  - pass/fail reporting
  - staging run instructions that match the real suite

### 2. Generic integration disconnect currently appears vulnerable to stale status residue

- `IntegrationManager` stores credentials in `integration_credentials`.
- It also stores sync/error state separately in `integration_sync_state`.
- `get_integration_status()` merges both tables and derives `status` from both.
- `delete_credentials()` currently deletes only the credential row.
- That means a disconnected provider can still retain stale error/sync metadata unless cleanup happens elsewhere.
- This is exactly the kind of connect/disconnect/reconnect seam that can make a later reconnect look broken even when tokens are fine.

### 3. Google Workspace is truthful on connect/reconnect, but it still lacks a disconnect lifecycle

- Phase 54 added:
  - canonical backend-owned Google Workspace credential sync
  - truthful status semantics
  - reconnect CTA behavior
- Current configuration routes expose:
  - `GET /configuration/google-workspace-status`
  - `POST /configuration/google-workspace/sync`
- There is no dedicated Google Workspace disconnect route in the configuration router yet.
- That means Phase 55 should explicitly cover Google Workspace rather than assuming the generic integration registry solves it.

### 4. The SSE backend already uses the right identity path, but the regression coverage is still shallow for isolation

- `app/fast_api_app.py` resolves `effective_user_id` from Bearer auth and uses it when loading or creating the chat session.
- This is a good isolation baseline because session lookup is already keyed by both `user_id` and `session_id`.
- The problem is assurance, not just implementation:
  - existing SSE integration tests verify auth handling and stream format
  - they do not explicitly prove that two different users reusing the same `session_id` remain isolated
  - frontend background streaming also lacks explicit tests that side effects remain session-scoped under concurrent use

### 5. The Phase 55 split should follow the actual risk seams

The cleanest breakdown is:

1. **55-01 OAuth lifecycle truthfulness**
   - stale-state cleanup
   - disconnect/reconnect correctness
   - Google Workspace disconnect lifecycle
2. **55-02 SSE multi-user isolation**
   - backend same-session cross-user isolation tests
   - frontend background-stream side-effect routing tests
3. **55-03 Load harness + report contract**
   - canonical Locust entrypoint
   - threshold evaluation
   - staging execution/reporting runbook

## Recommended Plan Shape

- Keep Phase 55 at **3 plans**.
- Make `55-01` the first execution target because it has an obvious stale-state bug path and can be completed without staging infra.
- Treat the live 100-user staging run as Phase 55 output, but build its repeatable harness and pass/fail contract before attempting to call the phase done.

## Key Risks To Control

- Disconnect must clear both credentials and stale sync/error metadata where appropriate.
- Google Workspace should not regress into browser-visible token handling while gaining disconnect support.
- SSE isolation tests must target real boundaries:
  - Bearer identity vs. request body
  - session ownership
  - per-session frontend side effects
- Load-test documentation must not point users to the wrong script or an incomplete results path.

---

*Phase: 55-integration-quality-load-testing*
*Research completed: 2026-04-11*
