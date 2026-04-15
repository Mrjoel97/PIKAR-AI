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

## Known Blocker

The Cloudflare plugin in this session is not currently authenticated. API attempts return `10000 Authentication error`, so remote Cloudflare deployment must wait until that account/plugin auth is fixed.
