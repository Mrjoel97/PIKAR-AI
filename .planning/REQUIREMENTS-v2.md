# Requirements: pikar-ai v2.0 Broader App Builder

**Defined:** 2026-03-21
**Core Value:** Users go through a GSD-powered creative workflow (question → research → brief → build → verify → ship) to build landing pages, web apps, and mobile apps — with full creative control over every design decision

## v2.0 Requirements

### Foundation

- [x] **FOUN-01**: Stitch MCP Server runs as a persistent singleton service in FastAPI lifespan (Node.js subprocess, not per-request)
- [x] **FOUN-02**: DB schema created: app_projects, app_screens, screen_variants, design_systems, build_sessions tables
- [x] **FOUN-03**: Prompt enhancer transforms vague user input into structured Stitch-optimized prompts using Gemini + design vocabulary mappings
- [x] **FOUN-04**: Stitch signed URLs (HTML, screenshots) are downloaded immediately and stored in Supabase Storage
- [x] **FOUN-05**: Generated apps can be previewed live in browser via embedded iframe/preview pane
- [ ] **FOUN-06**: Generated apps can be deployed to a public URL with one-click deploy

### GSD Creative Workflow

- [x] **FLOW-01**: User starts an app project and enters GSD-style creative questioning ("What do you want to build?", audience, purpose, style vibe)
- [x] **FLOW-02**: System performs design research — analyzes competitors/inspiration, suggests palettes, layouts, and typography patterns
- [x] **FLOW-03**: System generates a design brief with sitemap, DESIGN.md (colors, fonts, spacing), features per page, and device targets — user approves before building
- [x] **FLOW-04**: System creates a build plan breaking the app into phases per page/screen group with dependencies
- [x] **FLOW-05**: Each build phase follows a generate → preview → iterate → approve loop with GSD-style checkpoint cards
- [ ] **FLOW-06**: After all screens are built, a verification stage shows the complete app for final review
- [ ] **FLOW-07**: Ship stage generates all output targets (web, PWA, mobile, video) and deploys

### Screen Generation

- [x] **SCRN-01**: System generates 2-3 design variants per screen via Stitch MCP for user comparison
- [x] **SCRN-02**: Variants displayed side-by-side in the UI with visual comparison tools
- [x] **SCRN-03**: User can preview any screen in desktop, mobile, and tablet viewports
- [x] **SCRN-04**: System generates device-specific layouts (Stitch deviceType: DESKTOP/MOBILE/TABLET) not just responsive CSS

### Iteration & Refinement

- [x] **ITER-01**: User can describe changes to a screen ("make the hero bigger") and Stitch edit_screens re-generates
- [x] **ITER-02**: Once DESIGN.md is approved, all subsequent screens automatically follow the locked design system
- [x] **ITER-03**: System tracks all iterations per screen with version history and rollback to any previous version
- [x] **ITER-04**: GSD-style approval checkpoint cards at each stage — user must approve before the workflow advances

### Multi-Page Builder

- [ ] **PAGE-01**: Stitch-loop baton pattern autonomously generates multi-page sites: SITE.md sitemap → generate screen → update nav → next
- [ ] **PAGE-02**: System auto-generates navigation linking all pages together
- [ ] **PAGE-03**: Shared components (header, footer, nav) derived from DESIGN.md are reused across all pages
- [ ] **PAGE-04**: User can reorder, add, or remove pages from the sitemap at any point during the build

### Output Targets

- [ ] **OUTP-01**: Stitch HTML converted to modular React/TypeScript components with Tailwind theme extraction
- [ ] **OUTP-02**: PWA output generated with manifest.json, service worker, and mobile meta tags for installable web app
- [ ] **OUTP-03**: Downloadable Capacitor project structure generated for iOS/Android hybrid builds
- [ ] **OUTP-04**: Remotion walkthrough video generated from screenshots with transitions and overlays
- [ ] **OUTP-05**: Generated project packages (React, Tailwind, Capacitor, Remotion) use current stable versions resolved from npm registry at generation time, with fallback to pinned known-good versions

### App Builder UI

- [ ] **BLDR-01**: Builder dashboard listing all app projects with status, current GSD stage, and resume capability
- [x] **BLDR-02**: Live browser preview pane showing generated app in embedded iframe
- [ ] **BLDR-03**: One-click deploy button publishing app to a public URL
- [x] **BLDR-04**: Visual GSD progress bar showing current position in the 7-stage workflow with stage banners

## Future Requirements

### Advanced Features

- **ADVN-01**: AI-suggested design improvements based on UX best practices
- **ADVN-02**: Template library — save and reuse design systems across projects
- **ADVN-03**: Collaborative editing — multiple users on same project
- **ADVN-04**: Custom domain provisioning for deployed apps
- **ADVN-05**: A/B testing variants for landing pages

## Out of Scope

| Feature | Reason |
|---------|--------|
| Native iOS/Android development (Swift/Kotlin) | Capacitor hybrid covers mobile; native requires separate toolchain |
| Backend/server-side code generation | This milestone is UI/frontend generation only |
| E-commerce checkout flows | Complex business logic beyond UI generation scope |
| Drag-and-drop page editor | This is an AI-first builder, not a WYSIWYG editor |
| Custom CSS editing | Users describe changes in natural language, not write code |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUN-01 | Phase 16 | Complete |
| FOUN-02 | Phase 16 | Complete |
| FOUN-03 | Phase 16 | Complete |
| FOUN-04 | Phase 16 | Complete |
| FOUN-05 | Phase 19 | Complete |
| FOUN-06 | Phase 23 | Pending |
| FLOW-01 | Phase 17 | Complete |
| FLOW-02 | Phase 18 | Complete |
| FLOW-03 | Phase 18 | Complete |
| FLOW-04 | Phase 18 | Complete |
| FLOW-05 | Phase 20 | Complete |
| FLOW-06 | Phase 21 | Pending |
| FLOW-07 | Phase 22 | Pending |
| SCRN-01 | Phase 19 | Complete |
| SCRN-02 | Phase 19 | Complete |
| SCRN-03 | Phase 19 | Complete |
| SCRN-04 | Phase 19 | Complete |
| ITER-01 | Phase 20 | Complete |
| ITER-02 | Phase 20 | Complete |
| ITER-03 | Phase 20 | Complete |
| ITER-04 | Phase 20 | Complete |
| PAGE-01 | Phase 21 | Pending |
| PAGE-02 | Phase 21 | Pending |
| PAGE-03 | Phase 21 | Pending |
| PAGE-04 | Phase 21 | Pending |
| OUTP-01 | Phase 22 | Pending |
| OUTP-02 | Phase 22 | Pending |
| OUTP-03 | Phase 22 | Pending |
| OUTP-04 | Phase 22 | Pending |
| OUTP-05 | Phase 22 | Pending |
| BLDR-01 | Phase 23 | Pending |
| BLDR-02 | Phase 19 | Complete |
| BLDR-03 | Phase 23 | Pending |
| BLDR-04 | Phase 17 | Complete |

**Coverage:**
- v2.0 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 — traceability populated after ROADMAP-v2.md created*
