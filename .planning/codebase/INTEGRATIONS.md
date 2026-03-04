# External Integrations

**Analysis Date:** 2026-03-04

## APIs & External Services

**Google AI Platform (Gemini + Vertex AI):**
- Google Vertex AI / Gemini - primary LLM and media generation backbone
  - SDK/Client: `google-genai`, `google-cloud-aiplatform`, ADK model wrappers (`app/agents/shared.py`)
  - Auth: `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
  - Endpoints/features: chat generation, embeddings, Veo video generation (`app/services/vertex_video_service.py`)

**Google Workspace APIs:**
- Docs/Sheets/Drive/Gmail/Calendar/Forms/Slides integrations
  - SDK/Client: `google-api-python-client`, credentials wrapper in `app/integrations/google/client.py`
  - Auth: Supabase provider tokens + optional OAuth client ID/secret env vars
  - Scopes: resolved via `GOOGLE_WORKSPACE_SCOPES`

**Payments and Revenue APIs:**
- Stripe - revenue stats, balance retrieval, inbound webhook processing
  - SDK/Client: `stripe` Python SDK (`app/services/stripe_revenue_service.py`)
  - Auth: `STRIPE_API_KEY`; webhook verification via `STRIPE_WEBHOOK_SECRET`
  - Endpoints used: balance transactions, invoices, subscriptions, webhook events

**Accounting / Banking APIs:**
- QuickBooks Online (`oauth.platform.intuit.com`, `quickbooks.api.intuit.com`)
- Xero (`identity.xero.com`, `api.xero.com`)
- Plaid (`sandbox/development/production.plaid.com`)
  - Integration method: async HTTP via `httpx` in `app/services/finance_connectors.py`
  - Auth: per-user connector credentials from `user_configurations` + env fallback

**Research/Automation APIs (optional):**
- Tavily, Firecrawl, Stitch, Canva MCP tools (`app/mcp/config.py`, `app/mcp/tools/*`)
- SendGrid + HubSpot integration services (`app/mcp/integrations/email_service.py`, `app/mcp/integrations/crm_service.py`)

## Data Storage

**Databases:**
- Supabase Postgres (primary store)
  - Connection: `SUPABASE_URL` + service role key
  - Client: centralized singleton in `app/services/supabase_client.py`
  - Migrations: `supabase/migrations/*.sql`

**File Storage:**
- Supabase storage and vault-linked assets for media/document workflows
  - Integration points in vault/media services and routers (`app/routers/vault.py`, `app/services/*media*`)

**Caching:**
- Redis cache-aside service (`app/services/cache.py`)
  - Connection: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, optional password
  - Cached entities: user config, session metadata, persona data

## Authentication & Identity

**Auth Provider:**
- Supabase Auth for bearer token validation and session identity (`app/app_utils/auth.py`)
  - Backend verification: `supabase.auth.get_user(token)`
  - Frontend session client: `frontend/src/lib/supabase/client.ts`

**OAuth Integrations:**
- Google OAuth tokens from Supabase session used for Workspace APIs (`provider_token`, `provider_refresh_token`)
- Social provider configs supported via env/UI save flows (`frontend/src/app/api/configuration/*`)

**Service-to-Service Auth:**
- Internal backend callbacks protected by `WORKFLOW_SERVICE_SECRET` (`verify_service_auth` in `app/app_utils/auth.py`)

## Monitoring & Observability

**Error/Health Monitoring:**
- Health suite: `/health/live`, `/health/connections`, `/health/cache`, `/health/embeddings`, `/health/video` (`app/routers/health.py`)
- Structured and middleware request logging (`app/middleware/logging_middleware.py`)

**Telemetry/Cloud Logging:**
- Optional Google Cloud Logging and artifact bucket usage (`app/fast_api_app.py`)
- OpenTelemetry-related dependencies configured in `pyproject.toml`

## CI/CD & Deployment

**Hosting:**
- Backend target: Google Cloud Run (`Makefile` deploy target)
- Frontend target: Next.js runtime (local native or containerized in compose profile)

**CI Pipeline:**
- GitHub Actions workflow currently validates workflow templates (`.github/workflows/ci.yml`)
- Cloud Build configs exist for broader deployment flow (`.cloudbuild/*.yaml`)

## Environment Configuration

**Development:**
- Root `.env` plus app-level `app/.env` patterns are supported
- Local services: backend on `:8000`, frontend on `:3000`, Redis on `:6379`
- Optional Supabase local edge function env (`supabase/functions/.env.example`)

**Staging:**
- Terraform-managed GCP setup under `deployment/terraform/dev`
- Separate cloud project and secrets expected

**Production:**
- Secrets via environment variables and service account files under `secrets/` (not committed)
- Strict workflow guard rails controlled by `WORKFLOW_*` flags
- Recommended strict auth mode via `REQUIRE_STRICT_AUTH=1`

## Webhooks & Callbacks

**Incoming:**
- Stripe webhook endpoint: `POST /webhooks/stripe` (`app/routers/webhooks.py`)
  - Verification: `stripe.Webhook.construct_event` when `STRIPE_WEBHOOK_SECRET` is configured
  - Events handled: payment/customer/invoice/subscription lifecycle hooks

**Outgoing:**
- Backend to Supabase Functions: `/functions/v1/{name}` via `EdgeFunctionClient.invoke_function` (`app/services/edge_functions.py`)
- Workflow orchestration callbacks: `execute-workflow`, `send-notification`, analytics trackers
- Backend scheduled callback endpoint: `/business-health/recompute-scheduled`

---

*Integration audit: 2026-03-04*
*Update when adding/removing external services*
