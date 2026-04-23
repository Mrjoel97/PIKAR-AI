# Failed Commit Batch Analysis

Current repaired GitHub `main`: `71fff835` plus the backend trust-test
environment fix from this repair branch.

All unique commits listed by the user are ancestors of the repaired `main`.
The fixes for the shared local gate failures were applied after them in
`657451fd`.

## What Failed

The listed commits had two overlapping failure classes:

1. GitHub Actions did not execute the jobs. For recorded runs, both trust-gate
   jobs ended with `steps=0` and `runner_id=0`, which means checkout, install,
   tests, and builds never started. The run page for `ce2b8d2b` reported:
   "The job was not started because your account is locked due to a billing
   issue."
2. After the billing lock was resolved, the `71fff835` retrigger proved that
   GitHub-hosted runners started normally. The frontend and admin trust gates
   passed, and the backend trust gate reached pytest.
3. The repo also contained real local CI failures that would have failed once
   Actions started running:
   - duplicate Supabase migration prefixes
   - stale frontend test mock after `fetchWithAuth()` moved to `getAccessToken()`
   - backend trust tests relying on local Supabase environment variables

The first two local gate failures were fixed in `657451fd`. The backend
trust-test environment issue was exposed only after GitHub Actions could start
jobs again, and is fixed by the follow-up test helper change.

## Commit Outcomes

| Commit | Summary | GitHub Actions record | Included in repaired main |
| --- | --- | --- | --- |
| `7810b40d` | Let Supabase handle admin OAuth redirect | failure before steps (`runner_id=0`) | yes |
| `023ce930` | Use standard Supabase admin OAuth flow | failure before steps (`runner_id=0`) | yes |
| `1f2ba007` | Stabilize admin Google PKCE start flow | failure before steps (`runner_id=0`) | yes |
| `f2dd41a8` | Harden admin PKCE verifier storage | failure before steps (`runner_id=0`) | yes |
| `fde9188a` | Avoid duplicate admin OAuth code exchange | failure before steps (`runner_id=0`) | yes |
| `84e75c05` | Fix admin OAuth PKCE callback flow | failure before steps (`runner_id=0`) | yes |
| `5fb78467` | Persist admin password sessions server-side | failure before steps (`runner_id=0`) | yes |
| `f241792a` | Fix admin layout access redirect handling | failure before steps (`runner_id=0`) | yes |
| `6bfbcc31` | Add admin favicon | failure before steps (`runner_id=0`) | yes |
| `a56dd715` | Fix admin access verification flow | failure before steps (`runner_id=0`) | yes |
| `b435a092` | Fix brainstorm voice turns and workspace shell | failure before steps (`runner_id=0`) | yes |
| `a70ecfc0` | Update live brainstorm model id | failure before steps (`runner_id=0`) | yes |
| `a334919b` | Hide KPI shell on workspace | failure before steps (`runner_id=0`) | yes |
| `31f551aa` | Hide dashboard chrome on workspace route | failure before steps (`runner_id=0`) | yes |
| `6f19e8a4` | Fix workflow approval and vault chat handoff | failure before steps (`runner_id=0`) | yes |
| `e7a25ee5` | Fix onboarding brief access in live agent context | failure before steps (`runner_id=0`) | yes |
| `bf48341a` | Skip history restore for fresh chat sessions | failure before steps (`runner_id=0`) | yes |
| `c0da9324` | Fix post-onboarding agent launch handoff | failure before steps (`runner_id=0`) | yes |
| `98bba65f` | Ship onboarding vault sync and testing unlocks | failure before steps (`runner_id=0`) | yes |
| `18f80859` | Add sanitized Cloud Run service reference | no Actions run found | yes |
| `437c2b21` | Link Cloudflare checklist to runtime stabilization plan | failure before steps (`runner_id=0`) | yes |
| `3775b3d4` | Support workflow integration alias checks | no Actions run found | yes |
| `75ded6c4` | Stabilize workflow readiness and video health | failure before steps (`runner_id=0`) | yes |
| `501338fe` | Codify Cloud Run plain runtime config | failure before steps (`runner_id=0`) | yes |
| `ae9880cb` | Harden Cloud Run runtime secrets | failure before steps (`runner_id=0`) | yes |
| `fc66d6d4` | Fix Vertex embedding health parsing | failure before steps (`runner_id=0`) | yes |
| `a411eb22` | Skip startup embedding warmup on Cloud Run | failure before steps (`runner_id=0`) | yes |
| `8200272e` | Stabilize Cloud Run runtime and scheduled jobs | failure before steps (`runner_id=0`) | yes |
| `7efbbd24` | Add local deployment and load-test support files | failure before steps (`runner_id=0`) | yes |

## Important Note

Historical checks attached to old SHAs cannot be changed by committing new code.
They can only be rerun by GitHub after Actions is fixed. Rerunning those old
SHAs is not useful as a correctness signal because they do not contain
`657451fd`. The correctness target is the current `main` head.

## Required GitHub-Side Follow-Up

- Push the backend trust-test environment fix to `main`.
- Confirm the next `CI` run starts all jobs.
- Confirm `Frontend Trust Gate`, `Admin Trust Gate`, and `Backend Trust Gate`
  all pass on the latest `main` SHA.
