# Cloudflare Public API

This Worker is the Phase 2 public origin behind the main edge Worker:

- frontend on `Vercel`
- edge entry on `Cloudflare` at `api.pikar-ai.com`
- public origin on `Cloudflare Workers`
- agent execution on `Google` with Vertex AI

## Purpose

Use this Worker as `PUBLIC_BACKEND_ORIGIN` for the edge Worker.

It serves migrated public routes natively on Cloudflare and safely proxies any
remaining public traffic to the current Google backend until each route is
ported over intentionally.

## Initial Native Routes

- `GET /health/live`
- `GET /health/startup`
- `GET /health/public`
- `GET /suggestions` when called through the main edge Worker
- `GET /action-history` when called through the main edge Worker
- `GET /api-credentials`
- `POST /api-credentials`
- `DELETE /api-credentials/:name`
- `GET /integrations/providers` when called through the main edge Worker
- `POST /approvals/create` when called through the main edge Worker
- `GET /approvals/pending/list` when called through the main edge Worker
- `GET /approvals/history` when called through the main edge Worker
- `GET /approvals/:token` when called through the main edge Worker
- `POST /approvals/:token/decision` when called through the main edge Worker
- `GET /ad-approvals/pending` when called through the main edge Worker
- `GET /ad-approvals/:approvalId` when called through the main edge Worker
- `POST /ad-approvals/:approvalId/decide` with native Cloudflare auth and validation, plus verified proxying for approve execution
- `GET /outbound-webhooks/events` when called through the main edge Worker
- `GET /outbound-webhooks/endpoints` when called through the main edge Worker
- `POST /outbound-webhooks/endpoints` when called through the main edge Worker
- `PATCH /outbound-webhooks/endpoints/:endpointId` when called through the main edge Worker
- `DELETE /outbound-webhooks/endpoints/:endpointId` when called through the main edge Worker
- `GET /outbound-webhooks/endpoints/:endpointId/deliveries` when called through the main edge Worker
- `POST /outbound-webhooks/endpoints/:endpointId/test` when called through the main edge Worker
- `GET /pages` when called through the main edge Worker
- `POST /pages/import` when called through the main edge Worker
- `GET /pages/:pageId` when called through the main edge Worker
- `PATCH /pages/:pageId` when called through the main edge Worker
- `DELETE /pages/:pageId` when called through the main edge Worker
- `POST /pages/:pageId/publish` when called through the main edge Worker
- `POST /pages/:pageId/unpublish` when called through the main edge Worker
- `POST /pages/:pageId/duplicate` when called through the main edge Worker
- `POST /pages/:pageId/submit` with native Cloudflare validation and verified proxying to the current backend form handler
- `GET /integrations/:provider/authorize` when called through the main edge Worker
- `GET /integrations/:provider/callback` with native OAuth token exchange and credential persistence for providers whose client credentials are mirrored into the Worker
- `GET /onboarding/status` when called through the main edge Worker
- `POST /onboarding/business-context` when called through the main edge Worker
- `POST /onboarding/preferences` when called through the main edge Worker
- `POST /onboarding/agent-setup` when called through the main edge Worker
- `POST /onboarding/switch-persona` when called through the main edge Worker
- `POST /onboarding/complete` when called through the main edge Worker
- `POST /onboarding/extract-context` with native Cloudflare validation and sanitized proxying to the current backend model call
- `GET /community/posts` when called through the main edge Worker
- `POST /community/posts` when called through the main edge Worker
- `GET /community/posts/:postId` when called through the main edge Worker
- `POST /community/posts/:postId/comments` when called through the main edge Worker
- `POST /community/posts/:postId/upvote` when called through the main edge Worker
- `GET /support/tickets` when called through the main edge Worker
- `POST /support/tickets` when called through the main edge Worker
- `PATCH /support/tickets/:ticketId` when called through the main edge Worker
- `DELETE /support/tickets/:ticketId` when called through the main edge Worker
- `GET /teams/workspace` when called through the main edge Worker
- `GET /teams/members` when called through the main edge Worker
- `GET /teams/invites/details` when called through the main edge Worker
- `POST /teams/invites` when called through the main edge Worker
- `POST /teams/invites/accept` when called through the main edge Worker
- `GET /teams/analytics` when called through the main edge Worker
- `GET /teams/shared/initiatives` when called through the main edge Worker
- `GET /teams/shared/workflows` when called through the main edge Worker
- `GET /teams/activity` when called through the main edge Worker
- `POST /account/facebook-deletion-callback` when called through the main edge Worker
- `POST /account/export` when called through the main edge Worker
- `DELETE /account/delete` when called through the main edge Worker
- `GET /account/deletion-status/:confirmationCode` when called through the main edge Worker
- `GET /configuration/mcp-status` when called through the main edge Worker
- `GET /configuration/session-config` when called through the main edge Worker
- `GET /configuration/user-configs` when called through the main edge Worker
- `GET /configuration/social-status` when called through the main edge Worker
- `GET /configuration/google-workspace-status` when called through the main edge Worker
- `GET /configuration/settings` when called through the main edge Worker
- `PATCH /configuration/settings` when called through the main edge Worker
- `GET /finance/invoices` when called through the main edge Worker
- `GET /finance/assumptions` when called through the main edge Worker
- `GET /finance/revenue-timeseries` when called through the main edge Worker
- `GET /sales/contacts` when called through the main edge Worker
- `GET /sales/contacts/activities` when called through the main edge Worker
- `GET /sales/connected-accounts` when called through the main edge Worker
- `GET /sales/campaigns` when called through the main edge Worker
- `GET /sales/page-analytics` when called through the main edge Worker
- `GET /content/bundles` when called through the main edge Worker
- `GET /content/bundles/deliverables` when called through the main edge Worker
- `GET /content/campaigns` when called through the main edge Worker
- `GET /webhooks/linkedin`
- `POST /webhooks/linkedin`
- `POST /webhooks/hubspot` with native Cloudflare signature verification, then verified proxying to the current backend
- `POST /webhooks/resend` with native Cloudflare signature verification, then verified proxying to the current backend
- `POST /webhooks/shopify` with native Cloudflare signature verification, then verified proxying to the current backend
- `POST /webhooks/stripe` with native Cloudflare signature verification, then verified proxying to the current backend
- `POST /webhooks/inbound/:provider`
- `GET /webhooks/events` when called through the main edge Worker

All other paths fall back to `FALLBACK_BACKEND_ORIGIN`.

## Environment Variables

### Required

- `FALLBACK_BACKEND_ORIGIN`
  Example: `https://pikar-ai-917671810739.us-central1.run.app`
- `INTERNAL_PROXY_TOKEN`
  Shared secret used by the edge Worker so native configuration routes are only available through `https://api.pikar-ai.com`
- `SUPABASE_URL`
  Example: `https://your-project.supabase.co`
- `SUPABASE_ANON_KEY`
  Required for Cloudflare-native reads that rely on Supabase RLS with the caller JWT
- `SUPABASE_SERVICE_ROLE_KEY`
  Required for Cloudflare-native inbound webhook handlers that must resolve users and insert system-owned event rows
- `ADMIN_ENCRYPTION_KEY`
  Required for native OAuth callbacks that encrypt provider access tokens before writing `integration_credentials`, and for outbound webhook secret previews on `GET /outbound-webhooks/endpoints`
- `LINKEDIN_WEBHOOK_SECRET`
  Required for native LinkedIn webhook signature verification
- `HUBSPOT_CLIENT_SECRET`
  Required for native HubSpot webhook signature verification on `POST /webhooks/hubspot`
- `HUBSPOT_WEBHOOK_SECRET`
  Also accepted for native HubSpot webhook verification to match the existing generic webhook naming convention
- mirrored OAuth client credentials for any provider you want to authorize natively, such as:
  - `HUBSPOT_CLIENT_ID`
  - `HUBSPOT_CLIENT_SECRET`
  - `SHOPIFY_CLIENT_ID`
  - `SHOPIFY_CLIENT_SECRET`
  - `STRIPE_CLIENT_ID`
  - `STRIPE_CLIENT_SECRET`
  - `LINEAR_CLIENT_ID`
  - `LINEAR_CLIENT_SECRET`
  - `ASANA_CLIENT_ID`
  - `ASANA_CLIENT_SECRET`
  - `SLACK_CLIENT_ID`
  - `SLACK_CLIENT_SECRET`
  - `BIGQUERY_CLIENT_ID`
  - `BIGQUERY_CLIENT_SECRET`
  - `GOOGLE_ADS_CLIENT_ID`
  - `GOOGLE_ADS_CLIENT_SECRET`
  - `META_ADS_CLIENT_ID`
  - `META_ADS_CLIENT_SECRET`
- provider webhook secrets such as `GITHUB_WEBHOOK_SECRET`, `HUBSPOT_WEBHOOK_SECRET`, `RESEND_WEBHOOK_SECRET`, `SHOPIFY_WEBHOOK_SECRET`, `SLACK_WEBHOOK_SECRET`, or another `<PROVIDER>_WEBHOOK_SECRET`
  Required for native generic inbound webhook verification on `POST /webhooks/inbound/:provider`
- `RESEND_WEBHOOK_SECRET`
  Required for native Resend Svix verification on `POST /webhooks/resend`
- `SHOPIFY_WEBHOOK_SECRET`
  Required for native Shopify webhook verification on `POST /webhooks/shopify`
- `STRIPE_WEBHOOK_SECRET`
  Required for native Stripe webhook verification on `POST /webhooks/stripe`

### Optional

- `ALLOWED_ORIGINS`
  Example: `https://pikar-ai.com,https://www.pikar-ai.com,https://pikar-ai.vercel.app`
- `OAUTH_STATE_SECRET`
  Recommended dedicated secret for stateless OAuth state tokens on native `/integrations/:provider/authorize` and `/integrations/:provider/callback`; if omitted, the Worker falls back to `INTERNAL_PROXY_TOKEN`
- mirrored configuration secrets for native status reporting:
  - `TAVILY_API_KEY`
  - `FIRECRAWL_API_KEY`
  - `STITCH_API_KEY`
  - `STRIPE_API_KEY`
  - `CANVA_API_KEY`
  - `RESEND_API_KEY`
  - `HUBSPOT_API_KEY`
  - `SCHEDULER_SECRET`
- mirrored social OAuth provider secrets for native connection-status reporting:
  - `TWITTER_CLIENT_ID`
  - `TWITTER_CLIENT_SECRET`
  - `LINKEDIN_CLIENT_ID`
  - `LINKEDIN_CLIENT_SECRET`
  - `FACEBOOK_APP_ID`
  - `FACEBOOK_APP_SECRET`
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `TIKTOK_CLIENT_KEY`
  - `TIKTOK_CLIENT_SECRET`

## Deploy

```powershell
cd deployment/cloudflare/public-api
npx wrangler deploy
```

Set the fallback origin before or after the first deploy:

```powershell
cd deployment/cloudflare/public-api
npx wrangler secret put FALLBACK_BACKEND_ORIGIN
npx wrangler secret put INTERNAL_PROXY_TOKEN
```

## Phase 2 Wiring

After this Worker is deployed, copy its hostname and set it on the edge Worker:

```powershell
cd deployment/cloudflare/edge-api
npx wrangler secret put INTERNAL_PROXY_TOKEN
npx wrangler secret put PUBLIC_BACKEND_ORIGIN
npx wrangler deploy
```

This turns on the public-origin split while keeping unported public routes safe
via fallback proxying.
