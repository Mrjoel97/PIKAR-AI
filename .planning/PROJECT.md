# Project: pikar-ai

## What This Is

A multi-agent AI executive system ("Chief of Staff") built on Google ADK that orchestrates 10 specialized agents through a central ExecutiveAgent. It empowers non-technical users to transform business ideas into operational ventures via intelligent agent-led workflows — including an AI-powered app builder that takes users from a vague idea to a deployable web/mobile app through a guided creative workflow. Frontend is Next.js 16 with React 19, backend is FastAPI/Supabase.

## Core Value

Users describe what they want in natural language and the system autonomously generates, manages, and grows their business operations — now including building the digital assets (landing pages, web apps, mobile apps) they need through a GSD-style creative workflow.

## Current Milestone: v4.0 Production Scale & Persona Readiness

**Goal:** Close every gap identified in the production readiness audit — infrastructure scalability for 1000+ concurrent users, differentiated persona UIs, distributed rate limiting, error tracking, observability, and security hardening — bringing every subsystem to production-grade.

**Target features:**
- Multi-worker uvicorn with process manager, concurrency limits, and request timeouts
- Distributed SSE connection tracking via Redis, backpressure, and multi-replica awareness
- Per-persona differentiated dashboards, navigation, widgets, and feature gating on frontend
- Comprehensive feature flag system with Redis-backed storage, gradual rollout, and management UI
- Sentry integration (Python + Next.js), APM, alerting, distributed tracing via OpenTelemetry
- Thread pool sizing for Supabase blocking calls, connection pool tuning, async hot paths
- Redis-backed distributed rate limiting replacing all per-process limiters
- Security hardening: CSP, Referrer-Policy, request body limits, CORS tightening
- JWT verification caching, reduced auth round-trips, token validation optimization
- Redis connection pool scaling (20→200), per-operation monitoring
- Per-user LLM token budgets, cost tracking, burst queue for Gemini API calls
- Persona-tier enforcement with subscription/billing hooks

## Requirements

### Validated

- ✓ Workflow execution standardization — v1.0
- ✓ Redis circuit breakers for cache lookups — v1.0
- ✓ Deterministic argument mapping for workflow tools — v1.0
- ✓ Database schema alignment with codebase — v1.1
- ✓ Async event-loop safety across all services — v1.1
- ✓ Frontend-backend API and type alignment — v1.1
- ✓ Security headers and production hardening — v1.1
- ✓ Configuration system unification — v1.1
- ✓ Stitch MCP singleton integration with DB schema and asset persistence — v2.0
- ✓ GSD creative workflow engine (7-stage guided flow) — v2.0
- ✓ Creative questioning and design research — v2.0
- ✓ Design brief with user-approved design system — v2.0
- ✓ Screen variant generation and side-by-side preview — v2.0
- ✓ Iteration loop with version history and rollback — v2.0
- ✓ Multi-page builder with baton-loop pattern — v2.0
- ✓ React/TypeScript conversion pipeline — v2.0
- ✓ Output targets (PWA, Capacitor, Remotion video) — v2.0
- ✓ Ship pipeline with SSE progress streaming — v2.0

### Active

**v4.0 Production Scale & Persona Readiness:**
- [ ] Multi-worker app server with process management and concurrency controls
- [ ] Distributed SSE connection tracking and backpressure
- [ ] Per-persona differentiated frontend dashboards and feature gating
- [ ] Comprehensive feature flag system with gradual rollout
- [ ] Error tracking (Sentry) and observability (OpenTelemetry, APM, alerting)
- [ ] Database scalability (thread pool, connection tuning, async hot paths)
- [ ] Distributed rate limiting (Redis-backed)
- [ ] Security hardening (CSP, request limits, CORS)
- [ ] Auth optimization (JWT caching, reduced round-trips)
- [ ] Redis connection scaling and monitoring
- [ ] LLM cost control (per-user token budgets, burst queue)
- [ ] Persona-tier enforcement

**v3.0 Admin Panel (Phases 14-15, remaining):**
- [ ] Billing dashboard, approval oversight, permissions, role management

**Deferred from v2.0 (Phase 23, not yet planned):**
- [ ] Builder dashboard with project status and resume capability
- [ ] One-click deploy to public URL

### Out of Scope

- Multi-tenant admin (multiple admin teams) — founder-only for now, expandable later
- Real-time WebSocket monitoring — SSE/polling sufficient for admin use
- Custom admin theming — uses existing app design system
- Admin mobile app — desktop-first admin panel
- Native iOS/Android development (Swift/Kotlin) — Capacitor hybrid covers mobile
- Backend/server-side code generation — UI/frontend generation only
- E-commerce checkout flows — beyond UI generation scope

## Context

- 10 specialized ADK agents (financial, content, strategic, sales, marketing, operations, HR, compliance, support, data)
- Frontend: Next.js 16, React 19, Tailwind CSS 4, Supabase auth, fetchEventSource SSE chat
- Backend: FastAPI, Google ADK, Gemini models with Pro→Flash fallback, Redis with circuit breaker
- App Builder: Stitch MCP singleton (Node.js subprocess), 15+ API routes, SSE streaming for build/ship, ~14,900 LOC Python + ~1,800 LOC TypeScript
- Existing chat uses `useAgentChat` hook with `@microsoft/fetch-event-source` — admin chat follows same pattern
- Existing health endpoints: /health/live, /health/connections, /health/cache, /health/embeddings, /health/video
- Persona-based routing (solopreneur/startup/sme/enterprise) but no true RBAC exists
- slowapi rate limiting already in use across routers
- Full design spec: `docs/superpowers/specs/2026-03-21-admin-panel-design.md`

## Constraints

- **Existing Infra**: Must use existing patterns (ADK agents, fetchEventSource SSE, Supabase migrations, Cloud Scheduler)
- **Python AI**: Admin agent must be a Google ADK agent on FastAPI (not a separate Node.js AI SDK setup)
- **Schema Extension**: Add new admin tables via Supabase migrations, do not modify existing tables
- **Security**: API keys encrypted with Fernet, admin emails never exposed in client bundle
- **Backward Compat**: Admin panel must not affect existing user-facing routes or functionality

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Supabase migrations are source of truth (not Alembic) | Supabase has 96 migrations vs 1 stale Alembic file | ✓ Good |
| AI-first admin (chat-centered, not dashboard-centered) | Solo founder efficiency — one interface for all admin domains | ✓ Good |
| Google ADK AdminAgent (not Vercel AI SDK) | Consistent with existing chat infra, direct backend service access | ✓ Good |
| Two-layer auth (env allowlist + DB roles) | Bootstrap via env, transition to DB, OR logic for flexibility | ✓ Good |
| Fernet encryption for integration API keys | Application-layer encryption, key in env/Secret Manager, supports rotation | ✓ Good |
| Cloud Scheduler for health monitoring loop | Consistent with existing scheduled_endpoints.py pattern | ✓ Good |
| Server-side admin email check (not NEXT_PUBLIC_) | Prevents leaking admin identities in client bundle | ✓ Good |
| is_admin() SECURITY DEFINER function | Avoids circular self-referencing RLS on user_roles table | ✓ Good |
| Individual message rows (not JSONB blob) | Avoids write amplification, enables partial loading/querying | ✓ Good |
| Stitch MCP over REST API | MCP provides richer tools (edit_screens, project management) and follows stitch-skills standard | ✓ Good |
| GSD-style creative workflow | Guided discovery → brief → build → verify, not just "prompt → generate" — differentiates from v0/Bolt/Lovable | ✓ Good |
| User screen preview before creation | Creative control — preview variants, iterate, then finalize | ✓ Good |
| Capacitor for hybrid mobile | Native-like mobile from React output without requiring native dev skills | ✓ Good |
| Design system persistence per project | Visual consistency across multi-page apps, follows stitch-skills DESIGN.md pattern | ✓ Good |
| Prompt enhancer for screen generation | Gemini transforms vague user input into Stitch-optimized prompts with domain vocabulary | ✓ Good |
| Self-contained npm version resolution per generator | Avoids cross-service imports in parallel wave execution | ✓ Good |

---
*Last updated: 2026-03-25 after v4.0 Production Scale milestone started*
