# Cloudflare Edge API

This Worker is the public API entrypoint for the split deployment model:

- frontend on `Vercel`
- edge routing on `Cloudflare`
- agent execution on `Google` with Vertex AI

## Deploy Intent

Use this Worker to expose `https://api.pikar-ai.com` without sending browsers directly to Google.

## Environment Variables

### Required

- `AGENT_BACKEND_ORIGIN`
  Example: `https://agents.pikar-ai.com`

### Optional

- `PUBLIC_BACKEND_ORIGIN`
  Example: `https://public-api.pikar-ai.com`
- `ALLOWED_ORIGINS`
  Example: `https://pikar-ai.com,https://www.pikar-ai.com,https://pikar-ai.vercel.app`
- `ROUTE_MODE`
  Allowed values: `split`, `agent-only`
- `AGENT_ROUTE_PREFIXES`
  Comma-separated override for agent-only paths
- `PUBLIC_ROUTE_PREFIXES`
  Comma-separated override for public/API-edge paths

## Worker-Level Rate Limiting

This Worker now applies app-level rate limiting through a Durable Object for
the Cloudflare-native edge-only read routes on `https://api.pikar-ai.com`.

Current limits:

- `GET /account/deletion-status/:confirmationCode`: `60` requests per IP per `60` seconds
- `POST /account/facebook-deletion-callback`: `5` requests per IP per `60` seconds
- `POST /account/export`: `3` requests per IP per `60` seconds
- `DELETE /account/delete`: `3` requests per IP per `60` seconds
- `GET /configuration/mcp-status`: `30` requests per IP per `60` seconds
- `GET /configuration/session-config`: `120` requests per IP per `60` seconds
- `GET /configuration/user-configs`: `120` requests per IP per `60` seconds
- `GET /configuration/social-status`: `120` requests per IP per `60` seconds
- `GET /configuration/google-workspace-status`: `120` requests per IP per `60` seconds
- `GET /configuration/settings`: `120` requests per IP per `60` seconds
- `PATCH /configuration/settings`: `20` requests per IP per `60` seconds
- `GET /data-io/tables`: `60` requests per IP per `60` seconds
- `POST /data-io/upload`: `10` requests per IP per `60` seconds
- `POST /data-io/validate`: `20` requests per IP per `60` seconds
- `POST /data-io/commit`: `5` requests per IP per `60` seconds
- `GET /data-io/export/:tableName`: `10` requests per IP per `60` seconds
- `GET /monitoring-jobs`: `120` requests per IP per `60` seconds
- `POST /monitoring-jobs`: `20` requests per IP per `60` seconds
- `PATCH /monitoring-jobs/:jobId`: `30` requests per IP per `60` seconds
- `DELETE /monitoring-jobs/:jobId`: `20` requests per IP per `60` seconds
- `GET /email-sequences`: `120` requests per IP per `60` seconds
- `POST /email-sequences`: `20` requests per IP per `60` seconds
- `GET /email-sequences/:sequenceId`: `120` requests per IP per `60` seconds
- `PATCH /email-sequences/:sequenceId/status`: `30` requests per IP per `60` seconds
- `DELETE /email-sequences/:sequenceId`: `10` requests per IP per `60` seconds
- `POST /email-sequences/:sequenceId/enroll`: `20` requests per IP per `60` seconds
- `DELETE /email-sequences/enrollments/:enrollmentId`: `20` requests per IP per `60` seconds
- `GET /email-sequences/:sequenceId/performance`: `60` requests per IP per `60` seconds
- `GET /integrations/:provider/authorize`: `60` requests per IP per `60` seconds
- `GET /integrations/:provider/callback`: `60` requests per IP per `60` seconds
- `POST /approvals/create`: `5` requests per IP per `60` seconds
- `GET /approvals/pending/list`: `60` requests per IP per `60` seconds
- `GET /approvals/history`: `60` requests per IP per `60` seconds
- `GET /approvals/:token`: `5` requests per IP per `60` seconds
- `POST /approvals/:token/decision`: `5` requests per IP per `60` seconds
- `GET /ad-approvals/pending`: `60` requests per IP per `60` seconds
- `GET /ad-approvals/:approvalId`: `30` requests per IP per `60` seconds
- `POST /ad-approvals/:approvalId/decide`: `10` requests per IP per `60` seconds
- `GET /outbound-webhooks/events`: `60` requests per IP per `60` seconds
- `GET /outbound-webhooks/endpoints`: `120` requests per IP per `60` seconds
- `POST /outbound-webhooks/endpoints`: `20` requests per IP per `60` seconds
- `PATCH /outbound-webhooks/endpoints/:endpointId`: `30` requests per IP per `60` seconds
- `DELETE /outbound-webhooks/endpoints/:endpointId`: `20` requests per IP per `60` seconds
- `GET /outbound-webhooks/endpoints/:endpointId/deliveries`: `60` requests per IP per `60` seconds
- `POST /outbound-webhooks/endpoints/:endpointId/test`: `10` requests per IP per `60` seconds
- `GET /finance/invoices`: `120` requests per IP per `60` seconds
- `GET /finance/assumptions`: `120` requests per IP per `60` seconds
- `GET /finance/revenue-timeseries`: `60` requests per IP per `60` seconds
- `GET /sales/contacts`: `120` requests per IP per `60` seconds
- `GET /sales/contacts/activities`: `60` requests per IP per `60` seconds
- `GET /sales/connected-accounts`: `120` requests per IP per `60` seconds
- `GET /sales/campaigns`: `120` requests per IP per `60` seconds
- `GET /sales/page-analytics`: `60` requests per IP per `60` seconds
- `GET /content/bundles`: `120` requests per IP per `60` seconds
- `GET /content/bundles/deliverables`: `120` requests per IP per `60` seconds
- `GET /content/campaigns`: `120` requests per IP per `60` seconds
- `GET /governance/audit-log`: `60` requests per IP per `60` seconds
- `GET /governance/portfolio-health`: `60` requests per IP per `60` seconds
- `GET /governance/approval-chains`: `60` requests per IP per `60` seconds
- `GET /governance/approval-chains/:chainId`: `60` requests per IP per `60` seconds
- `GET /learning/courses`: `120` requests per IP per `60` seconds
- `GET /learning/progress`: `120` requests per IP per `60` seconds
- `GET /kpis/persona`: `120` requests per IP per `60` seconds
- `GET /reports`: `120` requests per IP per `60` seconds
- `GET /reports/categories`: `120` requests per IP per `60` seconds
- `GET /reports/:reportId`: `120` requests per IP per `60` seconds
- `GET /pages`: `120` requests per IP per `60` seconds
- `POST /pages/import`: `10` requests per IP per `60` seconds
- `GET /pages/:pageId`: `120` requests per IP per `60` seconds
- `PATCH /pages/:pageId`: `30` requests per IP per `60` seconds
- `DELETE /pages/:pageId`: `30` requests per IP per `60` seconds
- `POST /pages/:pageId/publish`: `20` requests per IP per `60` seconds
- `POST /pages/:pageId/unpublish`: `20` requests per IP per `60` seconds
- `POST /pages/:pageId/duplicate`: `10` requests per IP per `60` seconds
- `POST /pages/:pageId/submit`: `30` requests per IP per `60` seconds
- `GET /onboarding/status`: `120` requests per IP per `60` seconds
- `POST /onboarding/business-context`: `30` requests per IP per `60` seconds
- `POST /onboarding/preferences`: `30` requests per IP per `60` seconds
- `POST /onboarding/agent-setup`: `30` requests per IP per `60` seconds
- `POST /onboarding/switch-persona`: `30` requests per IP per `60` seconds
- `POST /onboarding/complete`: `10` requests per IP per `60` seconds
- `POST /onboarding/extract-context`: `10` requests per IP per `60` seconds
- `GET /community/posts`: `120` requests per IP per `60` seconds
- `POST /community/posts`: `30` requests per IP per `60` seconds
- `GET /community/posts/:postId`: `120` requests per IP per `60` seconds
- `POST /community/posts/:postId/comments`: `30` requests per IP per `60` seconds
- `POST /community/posts/:postId/upvote`: `60` requests per IP per `60` seconds
- `GET /support/tickets`: `120` requests per IP per `60` seconds
- `POST /support/tickets`: `30` requests per IP per `60` seconds
- `PATCH /support/tickets/:ticketId`: `30` requests per IP per `60` seconds
- `DELETE /support/tickets/:ticketId`: `30` requests per IP per `60` seconds
- `GET /teams/invites/details`: `60` requests per IP per `60` seconds
- `POST /teams/invites`: `30` requests per IP per `60` seconds
- `POST /teams/invites/accept`: `30` requests per IP per `60` seconds
- `GET /teams/workspace`: `120` requests per IP per `60` seconds
- `GET /teams/members`: `120` requests per IP per `60` seconds
- `GET /teams/analytics`: `60` requests per IP per `60` seconds
- `GET /teams/shared/initiatives`: `120` requests per IP per `60` seconds
- `GET /teams/shared/workflows`: `120` requests per IP per `60` seconds
- `GET /teams/activity`: `60` requests per IP per `60` seconds
- `GET /webhooks/events`: `60` requests per IP per `60` seconds

When a request is throttled, the Worker returns `429` with `Retry-After` plus
`x-pikar-rate-limit-*` headers.

## Recommended First Deployment

For the first cutover, use:

- `ROUTE_MODE=split`
- `AGENT_BACKEND_ORIGIN=https://<current-google-backend>`
- leave `PUBLIC_BACKEND_ORIGIN` unset

That gives Cloudflare control of the public API domain while still proxying all traffic to Google underneath.

## Wrangler Commands

Once Cloudflare auth is fixed, deploy with:

```powershell
cd deployment/cloudflare/edge-api
npx wrangler deploy
```

Set vars/secrets before deploy:

```powershell
cd deployment/cloudflare/edge-api
npx wrangler secret put AGENT_BACKEND_ORIGIN
npx wrangler secret put PUBLIC_BACKEND_ORIGIN
```

Non-secret vars can be kept in `wrangler.toml` or set per environment.

## Route Attachment

After deploy, attach the Worker to the API hostname you want to expose, for example:

- `api.pikar-ai.com/*`

## Health Check

The Worker exposes:

- `GET /health/edge`

This returns a simple JSON payload so you can verify that Cloudflare is serving traffic before the backend cutover.
