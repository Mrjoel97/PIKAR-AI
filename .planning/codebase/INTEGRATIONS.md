# External Integrations

**Analysis Date:** 2026-03-20

## APIs & External Services

### Google AI / Vertex AI
- **Gemini LLM** - Core agent intelligence (multi-agent orchestration)
  - SDK/Client: `google-adk`, `google-genai`
  - Models: `gemini-2.5-pro` (primary), `gemini-2.5-flash` (fallback)
  - Auth: `GOOGLE_API_KEY` (dev) or `GOOGLE_APPLICATION_CREDENTIALS` + `GOOGLE_CLOUD_PROJECT` (prod/Vertex)
  - Config: `app/agents/shared.py` (model selection, retry options, generation configs)
  - Retry: 5 attempts, 2s initial delay, 2x exponential backoff, 60s max

- **Vertex AI Imagen** - Image generation
  - SDK/Client: `google-genai` (Vertex AI mode)
  - Models: `imagen-4.0-fast-generate-001` (primary), `imagen-4.0-generate-001` (fallback)
  - Auth: `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION`
  - Implementation: `app/services/vertex_image_service.py`

- **Vertex AI Veo** - Video generation
  - SDK/Client: `google-genai` (Vertex AI mode)
  - Models: `veo-3.1-fast-generate-preview` (primary), `veo-3.1-generate-preview` (fallback)
  - Auth: `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION`
  - Implementation: `app/services/vertex_video_service.py`
  - Polling: Configurable interval (2-8s), 600s timeout

- **GenAI Embeddings** - Vector embeddings for RAG
  - SDK/Client: `google-genai`
  - Model: `text-embedding-004` (768 dimensions)
  - Auth: Same as Gemini (Vertex AI or API key)
  - Implementation: `app/rag/embedding_service.py`

- **Google Cloud Speech-to-Text** - Voice transcription
  - SDK/Client: `google-cloud-speech`
  - Auth: `GOOGLE_APPLICATION_CREDENTIALS`
  - Implementation: `app/services/speech_to_text_service.py`
  - Fallback: REST API using existing credentials when client library unavailable

- **Google Cloud Text-to-Speech** - Voiceover generation
  - SDK/Client: `google-cloud-texttospeech`
  - Auth: `GOOGLE_APPLICATION_CREDENTIALS`
  - Implementation: `app/services/voiceover_service.py`
  - Graceful degradation: Returns structured failure without breaking video generation

- **Google Cloud Logging** - Structured logging
  - SDK/Client: `google-cloud-logging`
  - Auth: `GOOGLE_APPLICATION_CREDENTIALS`
  - Implementation: Optional import in `app/fast_api_app.py`

- **OpenTelemetry GenAI Instrumentation** - AI call tracing
  - SDK/Client: `opentelemetry-instrumentation-google-genai`
  - Data sink: BigQuery via GCS (configured in `deployment/terraform/telemetry.tf`)

### Google Workspace
- **Gmail** - Email sending and inbox management
  - SDK/Client: `google-api-python-client` (Gmail API v1)
  - Auth: OAuth2 user tokens (provider_token + refresh_token from tool context)
  - Implementation: `app/integrations/google/gmail.py`, `app/integrations/google/gmail_reader.py`
  - Agent tools: `app/agents/tools/gmail.py`, `app/agents/tools/gmail_inbox.py`

- **Google Calendar** - Event management and scheduling
  - SDK/Client: `google-api-python-client` (Calendar API v3)
  - Auth: OAuth2 user tokens
  - Implementation: `app/integrations/google/calendar.py`
  - Agent tools: `app/agents/tools/calendar_tool.py`

- **Google Sheets** - Spreadsheet operations
  - SDK/Client: `google-api-python-client` (Sheets API v4)
  - Auth: OAuth2 user tokens
  - Implementation: `app/integrations/google/sheets.py`
  - Agent tools: `app/agents/tools/google_sheets.py`
  - Persistence: Spreadsheet connections tracked in `app/services/spreadsheet_connection_service.py`

- **Google Docs** - Document operations
  - SDK/Client: `google-api-python-client` (Docs API v1)
  - Auth: OAuth2 user tokens
  - Implementation: `app/integrations/google/docs.py`
  - Agent tools: `app/agents/tools/docs.py`

- **Google Forms** - Form management
  - SDK/Client: `google-api-python-client`
  - Auth: OAuth2 user tokens
  - Implementation: `app/integrations/google/forms.py`
  - Agent tools: `app/agents/tools/forms.py`

### Search & Web Scraping (MCP Layer)
- **Tavily** - Web search API
  - SDK/Client: httpx (direct REST calls)
  - Auth: `TAVILY_API_KEY`
  - Rate limit: 30 requests/minute (configurable via `MCP_SEARCH_RATE_LIMIT`)
  - Implementation: `app/mcp/tools/web_search.py`
  - Config: `app/mcp/config.py`

- **Firecrawl** - Web scraping API
  - SDK/Client: httpx (direct REST calls)
  - Auth: `FIRECRAWL_API_KEY`
  - Rate limit: 10 requests/minute (configurable via `MCP_SCRAPE_RATE_LIMIT`)
  - Implementation: `app/mcp/tools/web_scrape.py`, `app/mcp/tools/sitemap_crawler.py`
  - Config: `app/mcp/config.py`

### Payments
- **Stripe** - Payment processing
  - SDK/Client: `stripe` Python SDK >=7.0.0
  - Auth: `STRIPE_API_KEY`
  - Implementation: `app/mcp/tools/stripe_payments.py`
  - Features: Payment links, checkout sessions, product management
  - Lazy-loaded SDK for optional integration

### Email (Transactional)
- **Resend** - Transactional email delivery
  - SDK/Client: httpx (direct REST calls to `https://api.resend.com/emails`)
  - Auth: `RESEND_API_KEY`
  - From address: `RESEND_FROM_EMAIL` (default: `noreply@pikar.ai`)
  - Implementation: `app/mcp/integrations/email_service.py`
  - Config: `app/mcp/config.py`

### CRM
- **HubSpot** - CRM integration for lead management
  - SDK/Client: httpx (direct REST calls to `https://api.hubapi.com`)
  - Auth: `HUBSPOT_API_KEY`
  - Implementation: `app/mcp/integrations/crm_service.py`
  - Features: Contact creation, deal management

### Social Media Platforms
- **LinkedIn** - Social publishing and webhook events
  - Auth: OAuth2 (`LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`)
  - Scopes: `openid`, `profile`, `w_member_social`
  - Webhook handler: `app/routers/webhooks.py`, `app/social/linkedin_webhook.py`
  - OAuth connector: `app/social/connector.py`

- **Twitter/X** - Social publishing
  - Auth: OAuth2 PKCE (`TWITTER_CLIENT_ID`, `TWITTER_CLIENT_SECRET`)
  - Scopes: `tweet.read`, `tweet.write`, `users.read`, `offline.access`
  - OAuth connector: `app/social/connector.py`

- **Facebook** - Page management and publishing
  - Auth: OAuth2 (`FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`)
  - Scopes: `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`, `read_insights`
  - OAuth connector: `app/social/connector.py`

- **Instagram** - Content publishing
  - Auth: OAuth2 (`INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`)
  - Scopes: `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`
  - OAuth connector: `app/social/connector.py`

- **YouTube** - Video upload and management
  - Auth: OAuth2 (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`)
  - Scopes: `youtube.upload`, `youtube`
  - OAuth connector: `app/social/connector.py`

- **TikTok** - Video publishing
  - Auth: OAuth2 (`TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`)
  - Scopes: `user.info.basic`, `video.publish`, `video.upload`
  - OAuth connector: `app/social/connector.py`

### SEO & Analytics
- **Google Search Console** - SEO data
  - Auth: `GOOGLE_SEO_SERVICE_ACCOUNT_JSON`
  - Implementation: `app/mcp/tools/google_seo.py`
  - Agent tools: `app/agents/tools/google_seo.py`

- **Google Analytics 4** - Analytics data
  - Auth: `GOOGLE_ANALYTICS_PROPERTY_ID` + service account
  - Implementation: `app/mcp/tools/google_seo.py`
  - Agent tools: `app/agents/tools/social_analytics.py`

### Landing Pages
- **Google Stitch** - Landing page generation
  - SDK/Client: httpx (REST calls to `https://stitch.withgoogle.com/api`)
  - Auth: `STITCH_API_KEY`
  - Implementation: `app/mcp/tools/stitch.py`, `app/mcp/tools/landing_page.py`

### Media (MCP Layer)
- **Canva** - Media design integration
  - Implementation: `app/mcp/tools/canva_media.py`
  - Agent tools: `app/agents/tools/media.py`

## Data Storage

### Primary Database
- **Supabase (PostgreSQL)**
  - Client: `supabase` Python SDK (singleton pattern in `app/services/supabase_client.py`)
  - Connection: `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (backend), `SUPABASE_ANON_KEY` (frontend)
  - Max connections: `SUPABASE_MAX_CONNECTIONS` (default: 50)
  - Timeout: `SUPABASE_TIMEOUT` (default: 60s)
  - Async wrapper: `app/services/supabase_async.py` (wraps sync client for async context)
  - Schema: 110 migration files in `supabase/migrations/`
  - RAG client: Separate client in `app/rag/knowledge_vault.py`
  - Frontend client: `frontend/src/lib/supabase/client.ts` (browser), `frontend/src/lib/supabase/server.ts` (server)

### Caching
- **Redis**
  - Client: `redis.asyncio` (async Redis with connection pooling)
  - Connection: `REDIS_HOST` (default: localhost), `REDIS_PORT` (default: 6379), `REDIS_PASSWORD` (optional)
  - Implementation: `app/services/cache.py` (CacheService with circuit breaker)
  - Circuit breaker: Automatic fallback to direct DB queries when Redis unavailable
  - TTL tiers: User config, session meta, persona (configurable)
  - Production: Google Cloud Memorystore Redis 7.0 (1GB BASIC tier)
  - Development: Docker `redis:alpine` container

### File Storage
- **Google Cloud Storage** - Artifact storage
  - Client: `gcsfs`
  - Bucket: `LOGS_BUCKET_NAME` (Terraform-managed)
  - Usage: ADK artifact service, telemetry logs
  - Implementation: `GcsArtifactService` in `app/fast_api_app.py`

- **Supabase Storage** - User file uploads
  - Migration: `supabase/migrations/0018_create_storage.sql`
  - Frontend file router: `app/routers/files.py`

### Vector Storage (RAG)
- **Supabase pgvector** - Vector embeddings for knowledge vault
  - Embedding model: `text-embedding-004` (768 dimensions)
  - Tables: `agent_knowledge` (via `app/rag/knowledge_vault.py`)
  - Services: `app/rag/embedding_service.py`, `app/rag/search_service.py`, `app/rag/ingestion_service.py`

## Authentication & Identity

### Primary Auth Provider
- **Supabase Auth** - User authentication
  - Frontend: `@supabase/auth-helpers-nextjs`, `@supabase/ssr`
  - Backend: JWT verification via `app/app_utils/auth.py`
  - JWT secret: `SUPABASE_JWT_SECRET` (required in production, min 32 chars)
  - Auth modes:
    - Strict (`REQUIRE_STRICT_AUTH=1`) - Production recommended, rejects invalid tokens
    - Permissive (default) - Development, allows anonymous access
  - Anonymous chat: `ALLOW_ANONYMOUS_CHAT=1` (development only)
  - Auth flows: Login, signup, forgot password, reset password, OAuth callback
  - Pages: `frontend/src/app/auth/` (login, signup, forgot-password, reset-password, callback)

### OAuth (Social/Google Workspace)
- **Google OAuth** - Workspace API access (Gmail, Calendar, Sheets, Docs)
  - Credential flow: Provider token + refresh token stored in session state
  - Client: `app/integrations/google/client.py` (`get_google_credentials()`)

- **Social Media OAuth** - Platform connections
  - Connector: `app/social/connector.py` (centralized OAuth2 flows)
  - Supported: LinkedIn, Twitter, Facebook, Instagram, YouTube, TikTok
  - Token storage: `connected_accounts` table (via `supabase/migrations/0010_connected_accounts.sql`)

### Service-to-Service Auth
- **Scheduler Secret** - Cloud Scheduler to backend
  - Header: `X-Scheduler-Secret`
  - Env: `SCHEDULER_SECRET`
  - Implementation: `app/services/scheduled_endpoints.py`

- **Workflow Service Secret** - Edge functions to backend
  - Env: `WORKFLOW_SERVICE_SECRET` (min 32 chars in production)

## Monitoring & Observability

### Error Tracking
- Structured exception handling via `app/exceptions.py` (PikarError hierarchy)
- Global exception handlers in `app/fast_api_app.py` (PikarError, HTTP, Validation, Generic)
- Production: Sanitized error responses (no internal details leaked)
- Debug mode: `DEBUG=true` for detailed error responses

### Logs
- Python `logging` module throughout
- Google Cloud Logging (optional, imported when available)
- Request logging middleware: Request ID, User ID, Session ID on every request
- Response header: `X-Request-ID` for client correlation
- Health check endpoints excluded from verbose logging
- Interaction logging: `app/services/interaction_logger.py` (fire-and-forget async)
- MCP audit logging: `app/mcp/security/audit_logger.py` (all external API calls logged)

### Telemetry
- OpenTelemetry GenAI instrumentation (`opentelemetry-instrumentation-google-genai`)
- BigQuery dataset for telemetry data (Terraform: `deployment/terraform/telemetry.tf`)
- GCS bucket for telemetry logs (Terraform: `deployment/terraform/storage.tf`)

### Health Endpoints
- `/health/live` - Liveness probe (no dependencies)
- `/health/connections` - Supabase pools + cache health + config readiness
- `/health/cache` - Redis + circuit breaker state + hit/miss rates
- `/health/embeddings` - Gemini embedding availability + latency
- `/health/video` - Veo + Remotion configuration check
- `/health/workflows/readiness` - Tool/integration readiness report

## CI/CD & Deployment

### Backend Hosting
- **Google Cloud Run** (us-central1)
  - Memory: 4Gi
  - CPU throttling: Disabled
  - Deployment: `make deploy` (gcloud beta run deploy)
  - Health check: Python urllib probe at `/health/live` (30s interval, 90s start period)

### Frontend Hosting
- **Vercel** - Next.js deployment
  - Config: `vercel.json` (framework: nextjs)
  - Build: `cd frontend && npm run build`
  - Rewrites: `/api/backend/:path*` -> `${NEXT_PUBLIC_API_URL}/:path*`
  - Security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
  - Allowed origins: `pikar-ai.com`, `pikar-ai.vercel.app`, and project-specific Vercel URLs

### CI Pipeline
- **Google Cloud Build** (Terraform-managed: `deployment/terraform/build_triggers.tf`)
- **GitHub Integration** (Terraform: `deployment/terraform/github.tf`)

### Infrastructure as Code
- **Terraform** (`deployment/terraform/`)
  - Redis: `redis.tf` (Cloud Memorystore)
  - Storage: `storage.tf` (GCS buckets, Artifact Registry)
  - Service: `service.tf` (Cloud Run)
  - IAM: `iam.tf`, `service_accounts.tf`
  - Telemetry: `telemetry.tf` (BigQuery)
  - Secrets: `secrets.tf` (Secret Manager)
  - APIs: `apis.tf` (enabled GCP APIs)

### Container
- **Docker** - Backend containerization
  - Base image: `python:3.11-slim`
  - Includes: Node.js, npm, ffmpeg, Chromium libs (for Remotion)
  - Non-root user: `appuser` (UID 10001)
  - Build: `uv sync --frozen` + `npm ci` (remotion-render)

## Environment Configuration

**Required env vars (all environments):**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY`

**Required env vars (production only):**
- `SUPABASE_JWT_SECRET`
- `WORKFLOW_SERVICE_SECRET`
- `SCHEDULER_SECRET`
- `APP_URL`
- `ALLOWED_ORIGINS`
- `BACKEND_API_URL`
- `WORKFLOW_STRICT_TOOL_RESOLUTION=true`
- `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD=true`
- `WORKFLOW_ALLOW_FALLBACK_SIMULATION=false`
- `WORKFLOW_ENFORCE_READINESS_GATE=true`

**Optional integration env vars:**
- `TAVILY_API_KEY` - Web search
- `FIRECRAWL_API_KEY` - Web scraping
- `STRIPE_API_KEY` - Payments
- `RESEND_API_KEY` - Transactional email
- `HUBSPOT_API_KEY` - CRM
- `STITCH_API_KEY` - Landing pages
- `GOOGLE_SEO_SERVICE_ACCOUNT_JSON` - Search Console
- `GOOGLE_ANALYTICS_PROPERTY_ID` - GA4
- `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` - LinkedIn OAuth + webhooks
- `TWITTER_CLIENT_ID` / `TWITTER_CLIENT_SECRET` - Twitter/X OAuth
- `FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET` - Facebook OAuth
- `INSTAGRAM_APP_ID` / `INSTAGRAM_APP_SECRET` - Instagram OAuth
- `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` - YouTube OAuth
- `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET` - TikTok OAuth

**Secrets location:**
- Development: `.env` file at project root, `secrets/` directory for service account JSON
- Production: Google Secret Manager (Terraform: `deployment/terraform/secrets.tf`), Cloud Run env vars

## Webhooks & Callbacks

### Incoming Webhooks
- `POST /webhooks/linkedin` - LinkedIn event notifications (HMAC-SHA256 verification)
  - Implementation: `app/routers/webhooks.py`
  - Verification: `app/social/linkedin_webhook.py`
- `GET /webhooks/linkedin` - LinkedIn URL verification (challenge-response)
- `POST /api/webhooks/events` - Frontend webhook relay (Next.js API route at `frontend/src/app/api/webhooks/events/`)

### Scheduled Triggers (Cloud Scheduler)
- `POST /scheduled/daily-report` - Daily business report generation
- `POST /scheduled/weekly-digest` - Weekly digest email generation
  - Auth: `X-Scheduler-Secret` header
  - Implementation: `app/services/scheduled_endpoints.py`

### Supabase Edge Functions (Outgoing/Internal)
- `execute-workflow` - Workflow step execution (`supabase/functions/execute-workflow/`)
- `send-notification` - Notification delivery (`supabase/functions/send-notification/`)
- `generate-widget` - Widget generation (`supabase/functions/generate-widget/`)
- `cleanup-sessions` - Session cleanup (`supabase/functions/cleanup-sessions/`)
- `page-analytics-track` - Page analytics (`supabase/functions/page-analytics-track/`)
- Invocation: `app/services/edge_functions.py` (EdgeFunctionClient via httpx)

### SSE Streaming (Outgoing)
- `POST /a2a/app/run_sse` - Agent chat streaming
  - Media type: `text/event-stream`
  - Keepalive: 10s interval
  - Max duration: 300s (configurable via `SSE_MAX_DURATION_S`)
  - Connection limits: Per-user rate limiting (`app/services/sse_connection_limits.py`)
  - Widget extraction: Post-processes ADK events for frontend widget rendering

### MCP Security Layer
- All MCP external calls (Tavily, Firecrawl, Resend, HubSpot, Stripe) are:
  - PII-filtered before sending (`app/mcp/security/pii_filter.py`)
  - Audit-logged (`app/mcp/security/audit_logger.py`)
  - Rate-limited (configurable per service)
  - Payload-summarized for audit (`app/mcp/security/external_call_guard.py`)

---

*Integration audit: 2026-03-20*
