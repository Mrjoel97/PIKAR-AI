# Cloudflare Deferred Provider Follow-Ups

This document tracks Cloudflare-native provider work that is intentionally
deferred so it does not become an unowned migration gap.

Status as of April 17, 2026:

- The Cloudflare edge/public Worker split is live.
- The remaining missing items below are optional provider integrations, not
  hidden Cloud Run dependencies.
- Their routes now fail locally on Cloudflare rather than falling through to
  Google.

## Deferred Items

### 1. GitHub inbound webhooks

Current state:

- `POST /webhooks/inbound/github` is Cloudflare-native.
- The live `pikar-public-api` Worker does not yet have
  `GITHUB_WEBHOOK_SECRET`.
- Live behavior currently returns `500` with `Webhook secret not configured`.

To finish later:

- Add `GITHUB_WEBHOOK_SECRET` to the source of truth for production secrets.
- Mirror `GITHUB_WEBHOOK_SECRET` into `pikar-public-api`.
- Re-probe `POST /webhooks/inbound/github` and confirm signature rejection
  rather than configuration failure.
- If GitHub webhook delivery is business-critical, add one explicit end-to-end
  validation note here after production verification.

### 2. Slack inbound webhooks

Current state:

- `POST /webhooks/inbound/slack` is Cloudflare-native.
- The live `pikar-public-api` Worker does not yet have
  `SLACK_WEBHOOK_SECRET`.
- Live behavior currently returns `500` with `Webhook secret not configured`.

To finish later:

- Add `SLACK_WEBHOOK_SECRET` to the source of truth for production secrets.
- Mirror `SLACK_WEBHOOK_SECRET` into `pikar-public-api`.
- Re-probe `POST /webhooks/inbound/slack` and confirm signature rejection
  rather than configuration failure.
- Validate any Slack-specific header and body expectations against the live app
  configuration before calling it complete.

### 3. Stripe native provider authorization

Current state:

- The Stripe authorize path is Cloudflare-native:
  `GET /integrations/stripe/authorize`
- The live `pikar-public-api` Worker does not yet have
  `STRIPE_CLIENT_ID` or `STRIPE_CLIENT_SECRET`.
- HubSpot and Shopify OAuth credentials are already mirrored; Stripe is the
  remaining OAuth provider gap currently in scope.

To finish later:

- Add `STRIPE_CLIENT_ID` and `STRIPE_CLIENT_SECRET` to the production secret
  source of truth.
- Mirror both into `pikar-public-api`.
- Run a signed-in live test through `/api/integrations/stripe/authorize` from
  the frontend.
- Confirm redirect, callback persistence, and post-connect status all stay on
  the Cloudflare-owned path.

## Completion Rule

This follow-up can be considered complete when:

- GitHub and Slack webhook routes no longer return configuration errors.
- Stripe authorize is fully configured on Cloudflare.
- `docs/deployment/cloudflare-gateway-plan.md` is updated if any of the above
  become production-ready.
