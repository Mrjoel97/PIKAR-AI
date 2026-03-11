# External Integrations

**Analysis Date:** 2026-03-11

## APIs & External Services

**Google AI Services:**
- Gemini API / Vertex AI - Primary LLM for agent reasoning
  - SDK: `google-genai` >=0.2.0
  - Client files: `app/integrations/google/client.py`
  - Auth modes:
    - Vertex AI (preferred): `GOOGLE_APPLICATION_CREDENTIALS` + `GOOGLE_CLOUD_PROJECT`
    - Gemini API (fallback): `GOOGLE_API_KEY`
  - Fallback models: `gemini-2.5-pro` (primary), `gemini-2.5-flash` (fallback)
  - Enabled via environment: `GOOGLE_GENAI_USE_VERTEXAI`

**Google Workspace Integration:**
- Google Sheets API - Sheet manipulation, data retrieval
  - Integration: `app/integrations/google/sheets.py`
  - Client: `google-api-python-client`
  - Authentication: OAuth tokens via Supabase provider tokens

- Google Drive API - Document access, file management
  - Integration: `app/integrations/google/docs.py` (for Google Docs)
  - Client: `google-api-python-client`
  - Authentication: OAuth tokens via Supabase provider tokens

- Google Forms API - Form creation and responses
  - Integration: `app/integrations/google/forms.py`
  - Client: `google-api-python-client`
  - Authentication: OAuth tokens via Supabase provider tokens

- Gmail API - Email sending and management
  - Integration: `app/integrations/google/gmail.py`
  - Client: `google-api-python-client`
  - Authentication: OAuth tokens via Supabase provider tokens

- Google Calendar API - Calendar event management
  - Integration: `app/integrations/google/calendar.py`
  - Client: `google-api-python-client`
  - Authentication: OAuth tokens via Supabase provider tokens

**Video/Media Services:**
- Remotion - Programmatic video generation and rendering
  - SDK: `remotion` ^4.0.421
  - Implementation: `remotion-render/` directory
  - Config: `REMOTION_RENDER_ENABLED`, `REMOTION_RENDER_TIMEOUT`, `REMOTION_RENDER_SCALE`
  - Dependencies: FFmpeg, Node.js (in Docker)
  - Integration files: `app/services/director_service.py`, `app/services/vertex_video_service.py`

**Payment Processing:**
- Stripe - Payment collection and checkout
  - SDK: `stripe` >=7.0.0,<8.0.0
  - Configuration: `STRIPE_API_KEY`
  - Implementation: `app/mcp/tools/stripe_payments.py`
  - Features: Payment links, checkout sessions, invoice generation
  - Used for: Landing page monetization, product payment integration

**Optional/Third-Party APIs:**
- Tavily - Web search API (optional)
  - Config: `TAVILY_API_KEY` (commented in example)

- Firecrawl - Web scraping/crawling (optional)
  - Config: `FIRECRAWL_API_KEY` (commented in example)

## Data Storage

**Databases:**
- PostgreSQL (via Supabase)
  - Connection: `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`
  - Client: `supabase-py` >=2.27.2,<3.0.0
  - Async driver: `asyncpg` >=0.30.0,<1.0.0
  - Service files: `app/services/supabase_client.py`, `app/services/supabase.py`
  - Schema management: Alembic migrations (`app/database/run_migration.py`)
  - Tables: sessions, session_events, session_version_history (configurable via settings)
  - Pool configuration: `SUPABASE_MAX_CONNECTIONS` (default 50), `SUPABASE_TIMEOUT` (default 60s)

**File Storage:**
- Google Cloud Storage (optional)
  - Config: `LOGS_BUCKET_NAME`
  - Client: `gcsfs` >=2024.11.0
  - Integration: `google-cloud-logging` >=3.12.0,<4.0.0

- Local filesystem - Default file handling in development

**Caching:**
- Redis - In-memory cache for performance
  - Service: redis:alpine (Docker)
  - Connection: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_MAX_CONNECTIONS`
  - Client: `redis` >=5.0.0,<6.0.0
  - Implementation: `app/services/cache.py`
  - Features:
    - Circuit breaker pattern for fault tolerance
    - TTL-based expiration (configurable per category)
    - User config caching, session metadata, persona caching
  - TTL settings (in seconds):
    - User config: 3600 (1 hour)
    - Session metadata: 1800 (30 minutes)
    - Persona: 7200 (2 hours)
    - Default: 3600 (1 hour)

## Authentication & Identity

**Auth Provider:**
- Supabase Auth - User authentication and OAuth provider management
  - URL: `SUPABASE_URL`
  - Keys:
    - Anonymous key: `SUPABASE_ANON_KEY` (frontend, limited access)
    - Service role key: `SUPABASE_SERVICE_ROLE_KEY` (backend, full access)
  - Implementation: `app/app_utils/auth.py`
  - Frontend integration: `@supabase/auth-helpers-nextjs` ^0.15.0
  - SSR support: `@supabase/ssr` ^0.8.0

**OAuth Providers (via Supabase):**
- Google OAuth - User login and workspace integration
  - Provides: `provider_token` (access token), `provider_refresh_token`
  - Used for: Google Workspace API authentication

- Social login options (configured but optional):
  - YouTube, LinkedIn, Facebook, TikTok
  - Config: YouTube_Client_ID/Secret, LinkedIn_Client_ID/Secret, etc. (in comments)

**Token Management:**
- JWT - Token-based authentication
  - Implementation: `PyJWT` >=2.8.0
  - Service-to-service auth: `WORKFLOW_SERVICE_SECRET` (for Supabase Edge Function → FastAPI)

## Monitoring & Observability

**Error Tracking:**
- Not detected - No explicit error tracking service configured

**Logs:**
- Google Cloud Logging - Structured logging in production
  - Client: `google-cloud-logging` >=3.12.0,<4.0.0
  - Integration via OpenTelemetry

**Distributed Tracing:**
- OpenTelemetry (partial)
  - Integration: `opentelemetry-instrumentation-google-genai` >=0.1.0,<1.0.0
  - Provides instrumentation for Gemini API calls

**Standard Logging:**
- Python logging - Application logs
  - Configuration: `logging.basicConfig()` in `app/config/settings.py`
  - File: `app/fast_api_app.py` (health monitoring, pre-warm operations)

## CI/CD & Deployment

**Hosting:**
- Google Cloud Run - Container orchestration
  - Deployment configured in `pyproject.toml`
  - Port handling: `$PORT` environment variable (default 8000 in local, overridden by Cloud Run)
  - Non-root user execution (appuser)

**CI Pipeline:**
- Google Cloud Build - Build automation
  - Configured via `cicd_runner` in `pyproject.toml`

**Container Registry:**
- Docker - Containerization
  - Base image: `python:3.11-slim`
  - Container names: `pikar-backend`, `pikar-frontend`, `pikar-redis`
  - Health checks: Python subprocess for backend, curl for frontend
  - Log rotation: JSON file driver with 10m max size, 3 files max

**Docker Compose:**
- Local development orchestration
  - File: `docker-compose.yml`
  - Services:
    - Backend (FastAPI): port 8000, depends_on redis
    - Frontend (Next.js): port 3000, depends_on backend
    - Redis: port 6379
  - Profiles: `frontend`, `full` (allows running backend-only)
  - Network: `pikar-network` (bridge driver)
  - Volumes: Hot-reload for app code, remotion-render, frontend src

## Environment Configuration

**Required env vars (startup validation):**
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key
- `GOOGLE_API_KEY` OR (`GOOGLE_APPLICATION_CREDENTIALS` + `GOOGLE_CLOUD_PROJECT`)
- `REDIS_HOST` - Redis server address (default: localhost)
- `REDIS_PORT` - Redis server port (default: 6379)

**Optional env vars:**
- `REDIS_PASSWORD` - Redis authentication
- `REDIS_DB` - Redis database number (default: 0)
- `REDIS_MAX_CONNECTIONS` - Connection pool size (default: 20)
- `LOGS_BUCKET_NAME` - GCS bucket for logs
- Social OAuth credentials (YouTube, LinkedIn, Facebook, TikTok)
- `SCHEDULER_SECRET` - Cloud Scheduler authentication
- `STRIPE_API_KEY` - Stripe API key
- `TAVILY_API_KEY` - Web search API
- `FIRECRAWL_API_KEY` - Web crawling API

**Frontend-specific (public, safe for client):**
- `NEXT_PUBLIC_SUPABASE_URL` - Frontend Supabase URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Frontend anon key
- `NEXT_PUBLIC_API_URL` - Backend API URL (development: http://localhost:8000)

**Workflow Runtime Configuration:**
- `WORKFLOW_SERVICE_SECRET` - Secure random for workflow service auth
- `WORKFLOW_STRICT_TOOL_RESOLUTION` - Enable strict tool resolution (default: true)
- `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD` - Critical tool safety (default: true)
- `WORKFLOW_ALLOW_FALLBACK_SIMULATION` - Allow fallback simulation (default: false)
- `WORKFLOW_ENFORCE_READINESS_GATE` - Enforce readiness checks (default: true)
- `BACKEND_API_URL` - Workflow engine backend URL

**Remotion Configuration:**
- `REMOTION_RENDER_ENABLED` - Enable video rendering (default: 1)
- `REMOTION_RENDER_TIMEOUT` - Render timeout in seconds (default: 300)
- `DIRECTOR_RENDER_FPS` - Video frames per second (default: 24)
- `REMOTION_RENDER_SCALE` - Render scale factor (default: 0.5)

**Development Configuration:**
- `LOCAL_DEV_BYPASS` - Skip validation in development (set to "1")
- `SKIP_ENV_VALIDATION` - Disable startup validation
- `ENVIRONMENT` - Environment type ("production" or "development")

**Secrets location:**
- `.env` file (not committed)
- `secrets/` directory (mounted as read-only in Docker)
- Google Cloud Secret Manager (for production)
- Supabase project settings for API keys

## Webhooks & Callbacks

**Incoming:**
- Not explicitly detected in current codebase
- Potential usage in workflow systems (requires verification in workflow handlers)

**Outgoing:**
- Not explicitly detected in current codebase
- Stripe webhook endpoints may be configured but not yet implemented
- Social media publishing callbacks (optional feature)

**Event Handling:**
- Server-Sent Events (SSE) - Real-time updates
  - Client: `@microsoft/fetch-event-source` ^2.0.1
  - Implementation: `app/sse_utils.py` (bidirectional event streaming)

---

*Integration audit: 2026-03-11*
