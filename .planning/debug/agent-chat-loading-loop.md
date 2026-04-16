---
status: awaiting_human_verify
trigger: "Investigate agent chat interface loading loop."
created: 2026-04-01T00:00:00Z
updated: 2026-04-01T00:00:00Z
---

## Current Focus

hypothesis: The history-loading effect in useAgentChat is retriggering because its dependencies are unstable, especially a new Supabase client on every render and the full activeSessions map.
test: Stabilize the Supabase client, stop the history effect from depending on the volatile activeSessions map directly, and add a regression test that fails if unrelated session-map updates restart history loading.
expecting: The selected session history load will run once per session selection and settle into either loaded history or a stable welcome state without looping.
next_action: User verifies the chat interface no longer loops on load in the real dashboard.

## Symptoms

expected: The dashboard chat interface should finish loading and show either chat history or an empty ready state, then accept input.
actual: The agent chat interface keeps loading and appears stuck in a loop.
errors: None provided yet.
reproduction: Open the agent chat interface from the dashboard/workspace and observe a repeated loading state.
started: Newly reported after recent frontend fixes/deploys.

## Eliminated

- hypothesis: The loop is caused only by missing handling for empty histories.
  evidence: useAgentChat already includes a resolvedHistorySessionsRef guard and explicitly converts empty history to a welcome-message state.
  timestamp: 2026-04-01T00:00:00Z

## Evidence

- timestamp: 2026-04-01T00:00:00Z
  checked: frontend/src/hooks/useAgentChat.ts session resolution and history effect
  found: currentSessionId is derived from visibleSessionId or initialSessionId, but the history loader effect is driven separately by initialSessionId and local loading state.
  implication: Session selection and history loading can drift unless the effect dependencies are very stable.

- timestamp: 2026-04-01T00:00:00Z
  checked: frontend/src/hooks/useAgentChat.ts Supabase client creation
  found: useAgentChat calls createClient() directly during render and includes the resulting supabase object in the history effect dependency list.
  implication: Every render can create a new dependency identity and retrigger the history-loading effect.

- timestamp: 2026-04-01T00:00:00Z
  checked: frontend/src/hooks/useAgentChat.ts history effect dependencies
  found: the history-loading effect depends on the full activeSessions map and cancels in-flight work in its cleanup.
  implication: Any unrelated session-map update can cancel and restart history loading, which matches a visible loading loop.

- timestamp: 2026-04-01T00:00:00Z
  checked: frontend/src/components/dashboard/PersonaDashboardLayout.tsx and frontend/src/contexts/ChatSessionContext.tsx
  found: the dashboard passes the selected session through currentSessionId/visibleSessionId into ChatInterface, so the chat panel stays mounted while session state changes underneath it.
  implication: Hook-level effect retriggers are sufficient to produce a stuck loading overlay without remounting the whole chat UI.

## Resolution

root_cause: useAgentChat's history-loading effect depends on unstable values, especially a per-render Supabase client and the entire activeSessions map, so normal rerenders can repeatedly cancel and restart the selected session history load.
fix: Three changes applied to useAgentChat.ts — (1) Supabase client stabilized via useMemo(() => createClient(), []) on line 103, (2) activeSessionsRef created as a stable ref mirror of activeSessions on line 124 with a dedicated sync effect, (3) history-loading effect (lines 219-327) reads activeSessionsRef.current instead of activeSessions directly, with activeSessions intentionally excluded from deps via eslint-disable. Applied in commit 77317ef1.
verification: awaiting human verification — open the dashboard chat interface and confirm it no longer loops on load
files_changed: [frontend/src/hooks/useAgentChat.ts]
