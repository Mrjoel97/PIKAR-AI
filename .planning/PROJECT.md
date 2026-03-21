# Project: pikar-ai

## What This Is

A multi-agent AI executive system ("Chief of Staff") built on Google ADK that orchestrates 10 specialized agents through a central ExecutiveAgent. It empowers non-technical users to transform business ideas into operational ventures via intelligent agent-led workflows, with a Next.js frontend and FastAPI/Supabase backend.

## Core Value

Users can describe what they want in natural language and the system autonomously generates, manages, and grows their business operations — including now building the digital assets (landing pages, web apps, mobile apps) they need.

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

- [ ] Stitch MCP integration for AI-powered UI generation
- [ ] Prompt enhancement pipeline
- [ ] Multi-device screen generation
- [ ] User screen preview, selection, and iteration workflow
- [ ] Design system persistence per project
- [ ] Multi-page site builder (stitch-loop)
- [ ] React component conversion pipeline
- [ ] PWA and hybrid mobile output
- [ ] Remotion video generation from screens
- [ ] Frontend app builder UI

### Out of Scope

- Native iOS/Android development (Swift/Kotlin) — Stitch generates HTML/CSS, not native code; Capacitor hybrid covers mobile
- Backend/server-side code generation — this milestone is UI/frontend generation only
- E-commerce checkout flows — complex business logic beyond UI generation scope
- Custom domain provisioning — deployment infra is a separate concern

## Context

- Existing `app/mcp/tools/stitch.py` has a basic REST API integration with local HTML fallback (5 style presets)
- Existing `app/mcp/tools/landing_page.py` is a template engine (3 styles, string interpolation)
- Both tools are wired into Marketing and Content agents via `app/mcp/agent_tools.py`
- Frontend has `LandingPagesWidget.tsx` for listing/managing pages
- Supabase `landing_pages` table stores pages with `html_content`, `metadata` (contains react_content)
- Google stitch-skills repo provides: prompt enhancement, design-md, react-components, stitch-loop, remotion, shadcn-ui skills
- Stitch MCP tools: `generate_screen_from_text`, `edit_screens`, `list_projects`, `get_project`, `get_screen`
- Stitch outputs include `htmlCode.downloadUrl`, `screenshot.downloadUrl`, `outputComponents`
- The user wants creative control: preview multiple design options, select preferred, iterate before finalizing

## Constraints

- **MCP Protocol**: Stitch integration must use MCP Server tools, not REST API
- **Existing DB**: Must extend the Supabase schema (new tables/columns), not replace existing `landing_pages` table
- **Agent Architecture**: New tools must follow the existing ADK tool pattern (sync wrappers in `agent_tools.py`)
- **Python Backend**: Stitch MCP client must run in Python (not Node.js) — may need httpx-based MCP client or Python MCP SDK
- **Stitch API Key**: Requires user to configure Stitch API key (already have `configure_stitch_api_key` tool)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Supabase migrations are source of truth (not Alembic) | Supabase has 96 migrations vs 1 stale Alembic file | ✓ Good |
| Stitch MCP over REST API | MCP provides richer tools (edit_screens, project management) and follows the stitch-skills standard | — Pending |
| User screen preview before creation | Users need creative control — preview variants, iterate, then finalize | — Pending |
| Capacitor for hybrid mobile | Generates native-like mobile from React output without requiring native dev skills | — Pending |
| Design system persistence per project | Ensures visual consistency across multi-page apps, follows stitch-skills DESIGN.md pattern | — Pending |

---
*Last updated: 2026-03-21 after v2.0 milestone initialization*
