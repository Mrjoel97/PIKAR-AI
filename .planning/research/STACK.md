# Stack Research

**Domain:** Real-world integrations for multi-agent AI executive system
**Researched:** 2026-04-04
**Confidence:** HIGH (libraries verified against existing codebase patterns; async compatibility confirmed)

## Existing Stack (DO NOT add)
- FastAPI + Google ADK + Gemini models (Pro/Flash)
- Supabase (PostgreSQL + Auth + Storage + Realtime + pgvector)
- Redis with circuit breaker (`app/services/cache.py`)
- httpx (async HTTP — used in MCP tools)
- stripe SDK (payment links, webhooks)
- Google APIs (Calendar, Gmail, Sheets, Docs, Search Console, GA4) via OAuth
- Social platform APIs (Twitter, LinkedIn, Facebook, Instagram, YouTube)
- Vertex AI (Veo 3, Imagen, TTS)
- Tavily, Firecrawl (web search/scrape)
- Resend (email sending)

## New Libraries

### CRM
| Library | Version | Auth | Rate Limits | Notes |
|---------|---------|------|-------------|-------|
| `hubspot-api-client` | 10.x | OAuth2 / Private App Token | 100 req/10s (OAuth) | Official SDK, sync — wrap with `asyncio.to_thread()` |

### Financial (extending existing Stripe)
| Library | Version | Auth | Rate Limits | Notes |
|---------|---------|------|-------------|-------|
| `stripe` (already installed) | — | `STRIPE_API_KEY` | 100 read/sec | Extend: `PaymentIntent.list()`, `BalanceTransaction.list()`, `Invoice.list()` with `auto_pagination` |

### Project Management
| Library | Version | Auth | Rate Limits | Notes |
|---------|---------|------|-------------|-------|
| `httpx` (already installed) | — | OAuth2 / API Key | 1,500 req/hr (complexity-based) | Linear: direct GraphQL to `api.linear.app/graphql` |
| `asana` | 5.x | OAuth2 / PAT | 1,500 req/min | Official SDK, sync — wrap with `asyncio.to_thread()` |

### Advertising (REAL MONEY — requires approval processes)
| Library | Version | Auth | Rate Limits | Notes |
|---------|---------|------|-------------|-------|
| `google-ads` | 25.x | OAuth2 (Manager Account + dev token) | Per-operation limits | CRITICAL: requires Google Ads developer token approval |
| `facebook-business` | 20.x | System User Token / OAuth | Tier-based | CRITICAL: requires Business Verification + App Review |

### E-commerce
| Library | Version | Auth | Rate Limits | Notes |
|---------|---------|------|-------------|-------|
| `httpx` (already installed) | — | OAuth2 / Custom App Token | 1000 pts/sec (GraphQL) | Shopify: prefer GraphQL Admin API over REST |

### Document Generation
| Library | Version | Auth | Rate Limits | Notes |
|---------|---------|------|-------------|-------|
| `weasyprint` | 62.x | N/A | N/A | HTML→PDF — needs system deps (cairo, pango). Best for styled reports. |
| `python-pptx` | 1.x | N/A | N/A | PowerPoint slide generation for pitch decks |

### Communication
| Library | Version | Auth | Rate Limits | Notes |
|---------|---------|------|-------------|-------|
| `slack-sdk` | 3.x | Bot Token (xoxb-) | Tier-based (1-100/min) | Has `AsyncWebClient` — native async support |
| `httpx` (already installed) | — | Azure AD OAuth2 | 30 req/sec/app/tenant | MS Teams via Graph API `v1.0` |

### Data
| Library | Version | Auth | Rate Limits | Notes |
|---------|---------|------|-------------|-------|
| `asyncpg` (already installed) | — | Connection string | Connection pool limits | External Postgres — strict read-only, timeouts |
| `google-cloud-bigquery` | 3.x | Service Account / OAuth | 100 concurrent queries | Already adjacent to existing Google libs |
| `polars` | 1.x | N/A | N/A | Fast CSV parsing, lower memory than pandas |

### Webhook Infrastructure
| Library | Version | Auth | Rate Limits | Notes |
|---------|---------|------|-------------|-------|
| `hmac` + `hashlib` (stdlib) | — | N/A | N/A | HMAC-SHA256 webhook verification |
| `httpx` (already installed) | — | N/A | Self-imposed | Outbound delivery with retry |

## Libraries NOT to Add
- `celery` / `dramatiq` — overkill; extend existing `ai_jobs` + `workflow_trigger_service`
- `sqlalchemy` — Supabase is the ORM layer
- `requests` — use `httpx` (async)
- `boto3` — no AWS services needed
- `pdfkit` / `xhtml2pdf` — `weasyprint` is more capable and maintained
- Any separate message queue — extend existing Redis + ai_jobs pattern
