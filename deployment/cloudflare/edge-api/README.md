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
