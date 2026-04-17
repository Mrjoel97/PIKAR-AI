# Cloudflare Finish Checklist

This document is the canonical checklist for finishing the Cloudflare migration.

Use this instead of breaking the remaining work into short sprint notes. The goal is to finish the migration in one coordinated push while preserving the intended final split:

- `Vercel`: frontend
- `Cloudflare`: public API, routing, verification, edge security, public business-data APIs
- `Google Cloud Run`: agent execution only, backed by Vertex AI / Gemini

## Current Target State

The repo is already past the mid-migration stage:

- `api.pikar-ai.com` is fronted by the Cloudflare edge Worker.
- `public-api.pikar-ai.com` is fronted by the Cloudflare public Worker.
- Commodity public routes are already native on Cloudflare.
- Business-data reads already migrated:
  - `/finance/*`
  - `/sales/*`
  - `/content/*`
  - `/reports/*`
  - `/governance/audit-log`
  - `/governance/portfolio-health`
  - `/governance/approval-chains*`
  - `/learning/courses`
  - `/learning/progress`
  - `/kpis/persona`

The finish line is to remove the remaining non-agent Cloud Run dependency, then reduce Google to the intentional agent-only surface.

## Done Definition

The migration is only complete when all of the following are true:

- Every non-agent route family is either:
  - native on Cloudflare, or
  - intentionally retained on Google with an explicit architecture reason
- `docs/deployment/cloudflare-gateway-plan.md` reflects the real final split
- live probes confirm the final routing behavior for every remaining prefix
- worker-level rate limiting covers the final native route surface
- the public Worker deploy path no longer ends with the current Cloudflare route-attach auth failure, or that limitation is explicitly documented as accepted and worked around
- Cloud Run is reduced to the intentional agent-only runtime

## Finish Checklist

### 1. Remaining business-data route families

- [x] Migrate `/data-io/*` to the public Worker
- [ ] Migrate `/email-sequences/*` to the public Worker
- [ ] Migrate `/monitoring-jobs/*` to the public Worker
- [ ] Reconcile `/initiatives/*` and split it into:
  - Cloudflare-safe routes that should migrate now
  - agent-coupled routes that should intentionally remain on Google

### 2. Remaining partial route families already behind the public Worker

- [ ] Finish the remaining non-native `/governance/*` routes
- [ ] Finish the remaining non-native `/learning/*` routes
- [ ] Finish the remaining non-read `/configuration/*` routes
- [ ] Finish the remaining non-native `/webhooks/*` backend handling

### 3. Edge and public Worker hardening

- [ ] Add worker-level rate limiting for every newly migrated remaining route family
- [ ] Verify direct `public-api.pikar-ai.com` access remains blocked for protected native routes
- [ ] Verify edge-only token enforcement and caller JWT enforcement still match the current public Worker security model
- [ ] Reconcile any remaining secrets or bindings needed by the final native route families

### 4. Deployment and auth cleanup

- [ ] Fix the Wrangler custom-token route-attach issue that currently ends public Worker deploys with `/zones/.../workers/routes` `10000 Authentication error`
- [ ] Verify Cloudflare MCP account operations and inspection continue to work normally after the auth cleanup
- [ ] Confirm the final deploy flow is documented and repeatable without ad hoc workarounds

### 5. Final live-route audit

- [ ] Produce a final prefix inventory marked as:
  - `native on Cloudflare`
  - `fallback through public Worker`
  - `intentional Google-only`
- [ ] Run live probes for every remaining top-level prefix and record the observed headers
- [ ] Update `docs/deployment/cloudflare-gateway-plan.md` so it matches the observed live state exactly

### 6. Cloud Run reduction

- [ ] Remove any remaining non-agent public/backend responsibilities from Cloud Run
- [ ] Keep only the intended Google-only surface:
  - `/a2a`
  - `/briefing`
  - `/app-builder`
  - `/workflows`
  - `/workflow-triggers`
  - `/ws`
  - `/vault`
  - `/self-improvement`
  - `/byok`
  - `/admin/chat`
  - `/api/recruitment`
  - any explicitly justified `/initiatives/*` subset if still agent-coupled after reconciliation
- [ ] Reconfirm Vertex configuration is only required for the final Google-only service

## Recommended Execution Order

Run the remaining work in this order:

1. `/email-sequences/*`
2. `/monitoring-jobs/*`
3. remaining `/governance/*`
4. remaining `/learning/*`
5. remaining `/configuration/*`
6. remaining `/webhooks/*`
7. `/initiatives/*` reconciliation and migration
8. Wrangler auth and deploy-flow cleanup
9. final live-route audit and Cloud Run reduction

## Canonical Tracking Rules

- Keep this file as the single finish checklist for the Cloudflare migration.
- Update this file whenever a remaining route family moves from fallback or Google to native Cloudflare.
- Keep `docs/deployment/cloudflare-gateway-plan.md` as the live architecture and routing reference.
- Do not create new short sprint docs for the remaining Cloudflare migration unless this checklist is first updated to point to them explicitly.
