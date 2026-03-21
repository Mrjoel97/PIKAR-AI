# Project: pikar-ai

## What This Is

A multi-agent AI executive system ("Chief of Staff") built on Google ADK that orchestrates 10 specialized agents through a central ExecutiveAgent. It empowers non-technical users to transform business ideas into operational ventures via intelligent agent-led workflows, with a Next.js frontend and FastAPI/Supabase backend.

## Core Value

Users can describe what they want in natural language and the system autonomously generates, manages, and grows their business operations — including now building the digital assets (landing pages, web apps, mobile apps) they need.

## Current Milestone: v3.0 Admin Panel

**Goal:** Build an AI-first admin panel for founder management of the platform, centered around an AI Admin Assistant (Google ADK agent) with tiered autonomy, API health monitoring with self-healing, user impersonation, and external tool integrations.

**Target features:**
- Two-layer admin authorization (env allowlist + database user_roles table)
- AI Admin Assistant agent with 30+ tools across 7 domains, tiered autonomy (auto/confirm/blocked)
- System & API health monitoring with self-healing capabilities (Cloud Scheduler loop)
- User management with search, suspend/unsuspend, persona switching
- Admin impersonation (view + interactive modes) to test any user's experience
- External integrations (Sentry, PostHog, CodeRabbit, GitHub, Stripe) via server-side proxy
- Fernet-encrypted API key storage managed from the UI
- Usage analytics dashboards (DAU, MAU, agent effectiveness, retention)
- Cross-user approval oversight with admin override
- Agent configuration editor with version history and rollback
- Feature flag toggles, workflow template management
- Billing/revenue dashboard (MRR, churn, LTV)
- Comprehensive audit trail for all admin, AI agent, and impersonation actions
- Configurable agent permissions UI

## Current Milestone: v2.0 Broader App Builder

**Goal:** Transform the template-based landing page feature into an AI-powered app builder using Google Stitch MCP, enabling users to generate, preview, iterate, and deploy landing pages, multi-page web apps, and hybrid mobile apps from natural language descriptions.

**Target features:**
- Stitch MCP Server integration replacing REST API and template-based generation
- Prompt enhancement pipeline (vague descriptions → professional UI specifications)
- Multi-device generation (desktop, mobile, tablet) via Stitch deviceType
- User-facing screen preview and selection UI — users choose preferred designs before the app is created
- Iterative screen refinement — users can request changes and re-generate individual screens
- Persistent design system per project (DESIGN.md pattern for visual consistency)
- Multi-page autonomous site builder (stitch-loop baton pattern with SITE.md)
- React component conversion pipeline with AST validation and Tailwind theme extraction
- PWA output for mobile-optimized installable web apps
- Hybrid native output via Capacitor for iOS/Android builds
- Remotion walkthrough video generation from Stitch screenshots
- DB schema updates for multi-page projects, design systems, and screen variants

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

### Active

**v3.0 Admin Panel (Phases 7-15, in progress):**
- [ ] Admin authorization, AI Admin Assistant, health monitoring, user management
- [ ] Impersonation, integrations, analytics, config editor, billing, approvals

**v2.0 Broader App Builder (Phases 16+, defining requirements):**
- [ ] Stitch MCP integration for AI-powered UI generation
- [ ] Prompt enhancement pipeline
- [ ] Multi-device screen generation (desktop, mobile, tablet)
- [ ] User screen preview, selection, and iteration workflow
- [ ] Design system persistence per project
- [ ] Multi-page site builder (stitch-loop)
- [ ] React component conversion pipeline
- [ ] PWA and hybrid mobile output (Capacitor)
- [ ] Remotion video generation from screens
- [ ] Frontend app builder UI

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
- Existing chat uses `useAgentChat` hook with `@microsoft/fetch-event-source` — admin chat will follow same pattern
- Existing health endpoints: /health/live, /health/connections, /health/cache, /health/embeddings, /health/video
- Persona-based routing (solopreneur/startup/sme/enterprise) but no true RBAC exists
- Existing scheduled endpoints via Cloud Scheduler (`app/services/scheduled_endpoints.py`)
- Existing approval workflow with magic-link tokens (`/approval/[token]`)
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
| AI-first admin (chat-centered, not dashboard-centered) | Solo founder efficiency — one interface for all admin domains | — Pending |
| Google ADK AdminAgent (not Vercel AI SDK) | Consistent with existing chat infra, direct backend service access | — Pending |
| Two-layer auth (env allowlist + DB roles) | Bootstrap via env, transition to DB, OR logic for flexibility | — Pending |
| Fernet encryption for integration API keys | Application-layer encryption, key in env/Secret Manager, supports rotation | — Pending |
| Cloud Scheduler for health monitoring loop | Consistent with existing scheduled_endpoints.py pattern | — Pending |
| Server-side admin email check (not NEXT_PUBLIC_) | Prevents leaking admin identities in client bundle | — Pending |
| is_admin() SECURITY DEFINER function | Avoids circular self-referencing RLS on user_roles table | — Pending |
| Individual message rows (not JSONB blob) | Avoids write amplification, enables partial loading/querying | — Pending |

| Stitch MCP over REST API | MCP provides richer tools (edit_screens, project management) and follows the stitch-skills standard | — Pending |
| User screen preview before creation | Users need creative control — preview variants, iterate, then finalize | — Pending |
| Capacitor for hybrid mobile | Native-like mobile from React output without requiring native dev skills | — Pending |
| Design system persistence per project | Ensures visual consistency across multi-page apps, follows stitch-skills DESIGN.md pattern | — Pending |

---
*Last updated: 2026-03-21 after v2.0 Broader App Builder milestone added*
