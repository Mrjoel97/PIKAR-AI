# Cloudflare Gateway Plan

This project will use a split deployment model:

- `Vercel`: frontend only
- `Cloudflare`: public API entry, DNS, WAF, caching, webhook edge, and routing
- `Google`: agent execution only, using Vertex AI / Gemini

## Goal

Move public traffic away from direct Google Cloud Run exposure without forcing a frontend migration off Vercel.

## Route Classification

### Keep On Google First

These routes are tightly coupled to the Python ADK runtime, streaming agent execution, or Vertex-backed workflows:

- `/a2a`
- `/briefing`
- `/app-builder`
- `/workflows`
- `/workflow-triggers`
- `/ws`
- `/vault`
- `/self-improvement`
- `/initiatives`
- `/reports`
- `/content`
- `/finance`
- `/sales`
- `/compliance`
- `/learning`
- `/kpis`
- `/governance`
- `/data-io`
- `/email-sequences`
- `/monitoring-jobs`
- `/byok`
- `/admin/chat`
- `/api/recruitment`

### Move Behind Cloudflare First

These routes are better candidates for Cloudflare entry and later Cloudflare-native handling:

- `/health`
- `/webhooks`
- `/approvals`
- `/pages`
- `/community`
- `/account`
- `/teams`
- `/integrations`
- `/configuration`
- `/support`
- `/onboarding`
- `/action-history`
- `/suggestions`
- `/api-credentials`
- `/ad-approvals`
- `/outbound-webhooks`

### Route Notes

- `agent-only`
  These paths are tightly bound to Python runtime, ADK orchestration, A2A, SSE, websockets, or Vertex-backed execution.
- `cloudflare-fronted first`
  These paths can safely sit behind the Cloudflare Worker immediately, even if their origin still points at Google in phase 1.
- `cloudflare-native later`
  Webhooks, approvals, pages, lightweight account/configuration endpoints, and API facade routes are the best candidates to eventually move off Google entirely.

## Phase Order

### Phase 1: Edge Front Door

- Keep the frontend on Vercel.
- Point `NEXT_PUBLIC_API_URL` to `https://api.pikar-ai.com`.
- Deploy the Cloudflare Worker in `deployment/cloudflare/edge-api/`.
- Set `AGENT_BACKEND_ORIGIN` to the current Google-hosted backend.
- Leave `PUBLIC_BACKEND_ORIGIN` empty if all routes should proxy to Google initially.

This gives Cloudflare control of the public API domain with minimal risk.

### Phase 2: Public API Split

- Stand up a non-agent public API origin behind Cloudflare.
- Set `PUBLIC_BACKEND_ORIGIN`.
- Keep agent-only paths routed to Google via `AGENT_BACKEND_ORIGIN`.
- Start moving webhooks, approvals, pages, and configuration endpoints off Google.
- First Cloudflare-native webhook target: LinkedIn verification and event intake on `/webhooks/linkedin`.

Recommended first Phase 2 cut:

- deploy a dedicated Cloudflare Worker public origin
- serve `/health/*` natively from that public Worker first
- proxy any not-yet-migrated public routes from the public Worker back to Google

Current Phase 2 progress:

- `/health/live`
- `/health/startup`
- `/health/public`
- `/configuration/mcp-status` via native Cloudflare handling gated behind the edge Worker token
- `/configuration/session-config` via native Cloudflare handling using Supabase anon + caller JWT + RLS
- `/configuration/user-configs` via native Cloudflare handling using Supabase anon + caller JWT + RLS
- `/configuration/social-status` via native Cloudflare handling using Supabase anon + caller JWT + RLS after tightening `connected_accounts` policies
- `/configuration/google-workspace-status` via native Cloudflare handling using Supabase Auth user lookup with the caller JWT
- `/webhooks/linkedin` via native Cloudflare handling for verification and event intake
- `/webhooks/hubspot` via native Cloudflare signature verification plus verified proxying to the current backend while HubSpot business logic remains on Python
- `/webhooks/resend` via native Cloudflare Svix verification plus verified proxying to the current backend while inbox handling remains on Python
- `/webhooks/shopify` via native Cloudflare signature verification plus verified proxying to the current backend while Shopify sync logic remains on Python
- `/webhooks/stripe` via native Cloudflare signature verification plus verified proxying to the current backend while Stripe sync logic remains on Python
- `/webhooks/events` via native Cloudflare handling using Supabase Auth user lookup plus service-role-backed reads
- `/webhooks/inbound/:provider` via native Cloudflare handling using provider webhook secrets, idempotent inserts into `webhook_events`, and `ai_jobs` enqueueing

This enables `PUBLIC_BACKEND_ORIGIN` safely before every public route has been ported.

### Phase 3: Agent-Only Google Service

- Reduce the Google service scope to agent execution and Vertex-backed operations.
- Keep Vertex credentials only on the Google agent service.
- Remove public, commodity, or static-edge concerns from Google.

## Environment Changes

### Vercel

- `NEXT_PUBLIC_API_URL=https://api.pikar-ai.com`
- `BACKEND_URL=https://api.pikar-ai.com`

These are the main frontend cutover variables because the Vercel app already reads `NEXT_PUBLIC_API_URL` throughout the UI and route handlers.

### Cloudflare Worker

- `AGENT_BACKEND_ORIGIN=https://<google-agent-service>`
- `PUBLIC_BACKEND_ORIGIN=https://<public-api-origin>` when ready
- `ALLOWED_ORIGINS=https://pikar-ai.com,https://www.pikar-ai.com,https://pikar-ai.vercel.app`
- optional:
  - `ROUTE_MODE=split`
  - `AGENT_ROUTE_PREFIXES=...`
  - `PUBLIC_ROUTE_PREFIXES=...`

### Cloudflare Deploy Commands

Once Cloudflare auth is fixed:

```powershell
cd deployment/cloudflare/edge-api
npx wrangler deploy
```

Recommended first-phase secret setup:

```powershell
cd deployment/cloudflare/edge-api
npx wrangler secret put AGENT_BACKEND_ORIGIN
```

If and when a separate public API origin exists:

```powershell
cd deployment/cloudflare/edge-api
npx wrangler secret put PUBLIC_BACKEND_ORIGIN
```

### Google Agent Service

- `GOOGLE_APPLICATION_CREDENTIALS=<path or mounted secret>`
- `GOOGLE_CLOUD_PROJECT=<vertex-project-id>`
- `GOOGLE_CLOUD_LOCATION=us-central1`
- `GOOGLE_GENAI_USE_VERTEXAI=1`
- `GEMINI_AGENT_MODEL_PRIMARY=gemini-2.5-pro`
- `GEMINI_AGENT_MODEL_FALLBACK=gemini-2.5-flash`

Recommended stable Gemini model IDs on Vertex at the time of this plan:

- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

The app currently uses `GEMINI_AGENT_MODEL_PRIMARY` and `GEMINI_AGENT_MODEL_FALLBACK`, so that is the cleanest control surface for the Google-only agent service.

## Current Live Status

- Cloudflare MCP auth is working for the `Africantouch.official@gmail.com's Account` account as of April 16, 2026.
- `api.pikar-ai.com` is attached to the `pikar-edge-api` Worker.
- `public-api.pikar-ai.com` is attached to the `pikar-public-api` Worker.
- `api.pikar-ai.com/health/public` and `api.pikar-ai.com/health/live` are currently served through the public Worker via the edge split.
- `GET /webhooks/linkedin?challengeCode=...` is live and native on Cloudflare.
- `POST /webhooks/resend` is live and native on Cloudflare signature verification.
- `POST /webhooks/hubspot` is live and native on Cloudflare signature verification plus verified proxying.
- `POST /webhooks/shopify` is live and native on Cloudflare signature verification plus verified proxying.
- `POST /webhooks/stripe` is live and native on Cloudflare signature verification plus verified proxying.
- `GET /webhooks/events` is live and native through `api.pikar-ai.com`, requires the edge token plus a caller JWT, and direct `public-api` access is blocked.
- `POST /webhooks/inbound/:provider` is live and native on Cloudflare for configured providers; direct probes now return native signature rejection rather than fallback proxying.
- `GET /suggestions` is live and native through `api.pikar-ai.com`, requires the edge token plus a caller JWT, and no longer falls back to Cloud Run.
- `GET /action-history` is live and native through `api.pikar-ai.com`, requires the edge token plus a caller JWT, and no longer falls back to Cloud Run.
- `/api-credentials` list/create/delete is live and native through `api.pikar-ai.com`, requires the edge token plus a caller JWT, and no longer falls back to Cloud Run.
- `GET /integrations/providers` is live and native through `api.pikar-ai.com`, requires the edge token, and no longer falls back to Cloud Run.
- `GET /integrations/:provider/authorize` is now served natively through `api.pikar-ai.com` once the provider's OAuth client credentials are mirrored into `pikar-public-api`, with same-origin popup launch handled by the frontend route `/api/integrations/[provider]/authorize`.
- `GET /integrations/:provider/callback` is now handled natively on Cloudflare using stateless encrypted OAuth state plus Supabase-backed credential persistence, but it requires a shared `ADMIN_ENCRYPTION_KEY` to stay compatible with the Google agent backend.
- `GET /teams/workspace` is now served natively through `api.pikar-ai.com`, preserving first-read workspace creation plus the backend's startup-tier feature gate.
- `GET /teams/members` is now served natively through `api.pikar-ai.com`, preserving the startup-tier feature gate and member/profile shaping used by the team settings UI.
- `GET /teams/invites/details` is now served natively through `api.pikar-ai.com`, returns a native `404` for invalid tokens, and stays blocked on the direct `public-api` hostname.
- `POST /teams/invites` is now served natively through `api.pikar-ai.com`, preserving invite creation plus optional `invited_email` persistence for the newer email helper path.
- `POST /teams/invites/accept` is now served natively through `api.pikar-ai.com`, preserving workspace join semantics and governance audit logging.
- `GET /teams/analytics` is now served natively through `api.pikar-ai.com`, with safe zero-count fallback when optional source tables are absent.
- `GET /teams/shared/initiatives`, `GET /teams/shared/workflows`, and `GET /teams/activity` are now served natively through `api.pikar-ai.com`.
- `GET /account/deletion-status/:confirmationCode` is now served natively through `api.pikar-ai.com`, preserving the unauthenticated capability-token lookup while still blocking direct `public-api` access.
- `GET /onboarding/status`, `POST /onboarding/business-context`, `POST /onboarding/preferences`, `POST /onboarding/agent-setup`, and `POST /onboarding/switch-persona` are now served natively through `api.pikar-ai.com`, while `POST /onboarding/complete` and `POST /onboarding/extract-context` intentionally remain on Cloud Run fallback for now.
- The missing production Supabase team schema was reconciled on April 16, 2026 by applying the canonical workspace, governance, invite-email, and unified-action-history migrations so the Cloudflare-native team routes have their backing tables.
- The missing production `data_deletion_requests` table was also reconciled on April 16, 2026 so the public deletion-status page can resolve requests natively on Cloudflare.
- A custom Cloudflare firewall entrypoint now blocks invalid HTTP methods on the migrated webhook routes for both `api.pikar-ai.com` and `public-api.pikar-ai.com`.
- The edge Worker now applies app-level Durable-Object-backed rate limiting for the migrated edge-only read routes on `api.pikar-ai.com`.

## Remaining Cloud Run Surface

The live split now has three route classes:

- `native on Cloudflare`:
  - `/health/live`
  - `/health/startup`
  - `/health/public`
  - `/webhooks/linkedin`
  - `/webhooks/hubspot`
  - `/webhooks/resend`
  - `/webhooks/shopify`
  - `/webhooks/stripe`
  - `/webhooks/inbound/:provider`
  - `/webhooks/events`
  - `/suggestions`
  - `/action-history`
  - `/api-credentials`
  - `/integrations/providers`
  - `/integrations/:provider/authorize`
  - `/integrations/:provider/callback`
  - `/teams/workspace`
  - `/teams/members`
  - `/teams/invites/details`
  - `/teams/invites`
  - `/teams/invites/accept`
  - `/teams/analytics`
  - `/teams/shared/initiatives`
  - `/teams/shared/workflows`
  - `/teams/activity`
  - `/account/deletion-status/:confirmationCode`
  - `/onboarding/status`
  - `/onboarding/business-context`
  - `/onboarding/preferences`
  - `/onboarding/agent-setup`
  - `/onboarding/switch-persona`
  - `/configuration/mcp-status`
  - `/configuration/user-configs`
  - `/configuration/session-config`
  - `/configuration/social-status`
  - `/configuration/google-workspace-status`

- `direct to Cloud Run through the edge Worker`:
  - `/a2a`
  - `/briefing`
  - `/app-builder`
  - `/workflows`
  - `/workflow-triggers`
  - `/ws`
  - `/vault`
  - `/self-improvement`
  - `/initiatives`
  - `/reports`
  - `/content`
  - `/finance`
  - `/sales`
  - `/compliance`
  - `/learning`
  - `/kpis`
  - `/governance`
  - `/data-io`
  - `/email-sequences`
  - `/monitoring-jobs`
  - `/byok`
  - `/admin/chat`
  - `/api/recruitment`

- `edge -> public Worker -> fallback to Cloud Run unless explicitly native`:
  - `/approvals`
  - `/pages`
  - `/community`
  - `/account`
  - `/teams`
  - `/integrations`
  - `/support`
  - `/onboarding`
  - `/ad-approvals`
  - `/outbound-webhooks`
  - remaining non-native `/configuration/*`
  - remaining non-native `/webhooks/*`

Live probes on April 16, 2026 confirm this split:

- `GET /briefing` returns `x-pikar-edge-target: https://pikar-ai-917671810739.us-central1.run.app`
- `GET /integrations` returns `x-pikar-edge-target: https://public-api.pikar-ai.com`, then `x-pikar-public-route: fallback`, `x-pikar-public-target: https://pikar-ai-917671810739.us-central1.run.app`
- `GET /health/live` returns `x-pikar-edge-target: https://public-api.pikar-ai.com` and `x-pikar-public-route: native`

The current Google-only agent backend remains:

- Cloud Run service: `pikar-ai`
- Project: `pikar-ai-project`
- Region: `us-central1`
- Agent target currently wired behind Cloudflare: `https://pikar-ai-917671810739.us-central1.run.app`
- Vertex mode enabled on the live service:
  - `GOOGLE_CLOUD_PROJECT=pikar-ai-project`
  - `GOOGLE_CLOUD_LOCATION=us-central1`
  - `GOOGLE_GENAI_USE_VERTEXAI=1`
  - `GEMINI_AGENT_MODEL_PRIMARY=gemini-2.5-pro`
  - `GEMINI_AGENT_MODEL_FALLBACK=gemini-2.5-flash`

## Migration Checklist

Recommended migration order for the remaining Cloud Run surface:

1. Public read routes with simple auth/data access
   - remaining `/configuration/*`
2. OAuth and team/account surfaces
   - `/account/*`
   - remaining `/onboarding/*`
3. Public product and community surfaces
   - `/pages/*`
   - `/community/*`
   - `/support/*`
   - `/approvals/*`
   - `/ad-approvals/*`
   - `/outbound-webhooks/*`
4. Business-data APIs that are still backend-owned but are not Vertex-critical
   - `/finance/*`
   - `/sales/*`
   - `/content/*`
   - `/reports/*`
   - `/governance/*`
   - `/learning/*`
   - `/kpis/*`
   - `/data-io/*`
   - `/email-sequences/*`
   - `/monitoring-jobs/*`
   - `/initiatives/*`
5. Keep on Cloud Run unless the agent runtime is deliberately redesigned
   - `/briefing`
   - `/a2a`
   - `/admin/chat`
   - `/self-improvement`
   - `/workflows`
   - `/workflow-triggers`
   - `/app-builder`
   - `/vault`
   - `/ws`
   - `/api/recruitment`

Highest-value next batch:

- remaining `/account/*`
- `/onboarding/complete`
- `/onboarding/extract-context`

## Current Blockers

- The zone currently has the default Cloudflare leaked-credential rate-limit rule plus a custom firewall rule for webhook method enforcement, but it does not yet have project-specific API rate-limit policies.
- On the current Cloudflare Free zone, the dedicated `http_ratelimit` phase only allows one rule and that slot is already occupied by Cloudflare's leaked-credential protection, so an additional project-specific rate-limit rule could not be added through the zone ruleset API.
- Worker-level throttling now covers `GET /action-history`, `GET /api-credentials`, `GET /configuration/mcp-status`, `GET /configuration/session-config`, `GET /configuration/user-configs`, `GET /configuration/social-status`, `GET /configuration/google-workspace-status`, `GET /suggestions`, and `GET /webhooks/events` on `api.pikar-ai.com`.
- Worker-level throttling also covers `GET /integrations/:provider/authorize` and `GET /integrations/:provider/callback` on `api.pikar-ai.com`.
- Worker-level throttling also covers `GET /account/deletion-status/:confirmationCode`, `GET /teams/workspace`, `GET /teams/members`, `GET /teams/invites/details`, `POST /teams/invites`, `POST /teams/invites/accept`, `GET /teams/analytics`, `GET /teams/shared/initiatives`, `GET /teams/shared/workflows`, and `GET /teams/activity` on `api.pikar-ai.com`.
- Worker-level throttling also covers `GET /onboarding/status`, `POST /onboarding/business-context`, `POST /onboarding/preferences`, `POST /onboarding/agent-setup`, and `POST /onboarding/switch-persona` on `api.pikar-ai.com`.
