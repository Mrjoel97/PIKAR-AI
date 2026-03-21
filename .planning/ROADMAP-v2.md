# Roadmap: pikar-ai v2.0 Broader App Builder

**Milestone:** v2.0 Broader App Builder
**Phases:** 16–23 (8 phases)
**Granularity:** Standard
**Requirements mapped:** 34/34
**Created:** 2026-03-21

---

## Phases

- [x] **Phase 16: Foundation** — Stitch MCP singleton service, DB schema, prompt enhancer, and asset persistence layer (completed 2026-03-21)
- [ ] **Phase 17: Creative Questioning Engine** — GSD-style discovery flow and build session state machine for the 7-stage workflow
- [ ] **Phase 18: Design Brief & Research** — Competitor analysis, design system generation, sitemap creation, user approval, and build plan
- [ ] **Phase 19: Screen Generation & Preview** — Generate 2-3 variants via Stitch MCP, side-by-side comparison UI, multi-device preview, live browser preview
- [ ] **Phase 20: Iteration Loop** — Screen editing, design system lock, version history with rollback, GSD approval checkpoints
- [ ] **Phase 21: Multi-Page Builder** — Stitch-loop baton pattern, auto-navigation, shared components, page reordering, verification stage
- [ ] **Phase 22: React Conversion & Output Targets** — HTML-to-React/TS pipeline, PWA output, Capacitor project generation, Remotion walkthrough video, ship stage
- [ ] **Phase 23: App Builder Dashboard & Deploy** — Project dashboard with status/resume, one-click deploy to public URL, GSD progress indicators

---

## Phase Details

### Phase 16: Foundation
**Goal**: The infrastructure beneath every other phase exists and works — Stitch MCP speaks to FastAPI reliably, the DB schema is live, Stitch assets are persisted permanently, and vague user prompts are enriched before hitting Stitch
**Depends on**: Nothing (first phase of v2.0)
**Requirements**: FOUN-01, FOUN-02, FOUN-03, FOUN-04
**Success Criteria** (what must be TRUE):
  1. FastAPI starts and the Stitch MCP subprocess is alive for the process lifetime — sending a tool call to the running server returns a valid Stitch response without spawning a new Node.js process
  2. The DB tables (app_projects, app_screens, screen_variants, design_systems) exist in Supabase with RLS policies applied; a test project and screen row can be inserted and read back
  3. Stitch-generated HTML and screenshot files are downloaded within the same tool call that generates them and retrievable via a permanent Supabase Storage URL — not a short-lived Stitch signed URL
  4. A vague description ("bakery website") passed through the prompt enhancer returns a structured Stitch-optimized specification containing color hints, typography direction, and section breakdown
**Plans**: 3 plans
Plans:
- [ ] 16-01-PLAN.md — DB schema migration (5 tables, RLS, stitch-assets Storage bucket)
- [ ] 16-02-PLAN.md — StitchMCPService singleton + FastAPI lifespan wiring + ADK tool wrappers
- [ ] 16-03-PLAN.md — Asset persistence service + Gemini prompt enhancer + wire into app_builder tools

### Phase 17: Creative Questioning Engine
**Goal**: Users can start a new app project and be guided through GSD-style creative discovery — the system asks the right questions, records answers, and the build session state machine tracks the user's position in the 7-stage workflow
**Depends on**: Phase 16
**Requirements**: FLOW-01, BLDR-04
**Success Criteria** (what must be TRUE):
  1. A user opening the app builder is presented with structured discovery questions (purpose, audience, style vibe) via choice cards — not an open text box
  2. The system records answers and creates an app_project row with a draft status and the captured creative brief
  3. A GSD-style progress bar with 7 labeled stages is visible in the UI, with the current stage highlighted — users know exactly where they are in the workflow
  4. Completing the questioning stage advances the build session state machine to the next stage and that transition is reflected immediately in the progress bar
**Plans**: 2 plans
Plans:
- [ ] 17-01-PLAN.md — FastAPI router (POST /app-builder/projects, GET /app-builder/projects/{id}, PATCH /app-builder/projects/{id}/stage) + router registration
- [ ] 17-02-PLAN.md — Multi-step choice-card wizard, GsdProgressBar component, app-builder layout, /app-builder/new page

### Phase 18: Design Brief & Research
**Goal**: Before any screens are generated, the system researches the design space and produces a user-approved design brief — users see a sitemap, a design system document, and a build plan before a single pixel is generated
**Depends on**: Phase 17
**Requirements**: FLOW-02, FLOW-03, FLOW-04
**Success Criteria** (what must be TRUE):
  1. Given a completed creative brief, the system surfaces competitor/inspiration references and suggests a color palette, typography pairings, and layout patterns the user can review
  2. The system generates a DESIGN.md document (colors, fonts, spacing) and a SITE.md sitemap and presents both to the user for review — neither is used to drive generation until the user approves
  3. The user can edit the proposed design system and sitemap before approving — approval is an explicit action, not automatic
  4. After approval, the system produces a build plan that breaks the app into per-page/per-screen phases with visible dependencies — the user sees what will be built and in what order
**Plans**: TBD

### Phase 19: Screen Generation & Preview
**Goal**: Users can trigger screen generation and see multiple design variants side-by-side, preview any variant on desktop, mobile, and tablet, and inspect the live HTML in an embedded browser pane
**Depends on**: Phase 18
**Requirements**: SCRN-01, SCRN-02, SCRN-03, SCRN-04, FOUN-05, BLDR-02
**Success Criteria** (what must be TRUE):
  1. For any screen in the build plan, the system generates 2-3 distinct design variants via Stitch MCP — not sequential overwrites but parallel alternatives the user can compare
  2. Variants are displayed side-by-side in the UI with visual comparison tools so users can see the differences without switching views
  3. Any variant can be previewed at desktop, mobile, and tablet viewport sizes — not just scaled screenshots but Stitch-generated device-specific layouts for each form factor
  4. The selected variant renders as a live HTML page inside an embedded iframe/preview pane in the app builder UI — the user can interact with it as they would a real web page
**Plans**: TBD

### Phase 20: Iteration Loop
**Goal**: Users can request natural-language changes to any screen and see a re-generated result; once the design system is approved it enforces visual consistency across all screens automatically; every iteration is saved with rollback capability and the workflow only advances via explicit user approval
**Depends on**: Phase 19
**Requirements**: ITER-01, ITER-02, ITER-03, ITER-04, FLOW-05
**Success Criteria** (what must be TRUE):
  1. A user can type "make the hero section taller and use a darker background" and the screen re-generates via Stitch edit_screens — the change is reflected in the preview within the same session
  2. After the design system is locked (user-approved DESIGN.md), all subsequent screen generations for the project automatically include those color, font, and spacing constraints — no two screens look like they came from different design directions
  3. Every iteration creates a new screen_variant row; the user can view the full version history for any screen and roll back to any previous version from the UI
  4. At each build phase boundary, a GSD-style checkpoint card blocks workflow advancement until the user explicitly approves the current output — iterating more and approving are distinct actions
**Plans**: TBD

### Phase 21: Multi-Page Builder
**Goal**: Users can build complete multi-page sites autonomously — the stitch-loop baton pattern generates pages sequentially using the shared design system and sitemap, navigation links all pages together, and users retain control over page structure at any point
**Depends on**: Phase 20
**Requirements**: PAGE-01, PAGE-02, PAGE-03, PAGE-04, FLOW-06
**Success Criteria** (what must be TRUE):
  1. Given an approved SITE.md sitemap, the system autonomously generates each page in sequence using the stitch-loop baton pattern — progress is visible via SSE streaming as each page completes
  2. Generated pages are automatically linked together via navigation — clicking a nav link in the preview opens the correct page, not a 404
  3. Header, footer, and navigation components derived from DESIGN.md are visually consistent across all pages — shared components are not regenerated per page but applied from the design system
  4. The user can reorder, add, or remove pages from the sitemap at any point during the build — changes are reflected in the build plan and subsequent generation uses the updated sitemap
  5. After all pages are built, a verification stage renders the complete multi-page app for final review before the user proceeds to export
**Plans**: TBD

### Phase 22: React Conversion & Output Targets
**Goal**: Users can export their built app in any target format — modular React/TypeScript components, an installable PWA, a downloadable Capacitor hybrid project for iOS/Android, and a Remotion walkthrough video — and the ship stage bundles and deploys everything
**Depends on**: Phase 21
**Requirements**: OUTP-01, OUTP-02, OUTP-03, OUTP-04, OUTP-05, FLOW-07
**Success Criteria** (what must be TRUE):
  1. Stitch-generated HTML for any screen can be converted to modular React/TypeScript components with a Tailwind theme config extracted from the inline styles — the output is a downloadable ZIP with one component per screen section
  2. A PWA export generates a valid manifest.json, a service worker, and all required mobile meta tags — the exported app can be installed from a browser on Android and iOS as a home screen app
  3. A Capacitor export generates a complete project scaffold (capacitor.config.ts, package.json, platform configs) that a developer can download and run with `npx cap add ios && npx cap add android` without additional configuration
  4. A Remotion walkthrough video is generated from the app's screenshots with transitions and title overlays — the user can download the rendered MP4
  5. Generated package.json files reference current stable versions of React, Tailwind, Capacitor, and Remotion resolved from npm at generation time — not hardcoded versions that go stale
  6. The ship stage generates all selected output targets and initiates deployment in a single user action — the user does not manually trigger each export format separately
**Plans**: TBD

### Phase 23: App Builder Dashboard & Deploy
**Goal**: Users have a central dashboard to manage all their app projects, resume work mid-build, and publish any completed app to a live public URL in one click
**Depends on**: Phase 22
**Requirements**: BLDR-01, BLDR-03, FOUN-06
**Success Criteria** (what must be TRUE):
  1. The app builder dashboard lists all of the user's projects with their title, current GSD stage, status indicator (draft/generating/ready/exported), and a resume button — users can see all projects at a glance
  2. Clicking resume on a project in any stage returns the user to the exact GSD stage they left off — the build session state is restored, not restarted
  3. Any project in ready or exported status can be published to a public URL via a one-click deploy button — the URL is live within seconds and displayed to the user without any manual configuration
**Plans**: TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 16. Foundation | 3/3 | Complete | 2026-03-21 |
| 17. Creative Questioning Engine | 0/2 | Planned | - |
| 18. Design Brief & Research | 0/TBD | Not started | - |
| 19. Screen Generation & Preview | 0/TBD | Not started | - |
| 20. Iteration Loop | 0/TBD | Not started | - |
| 21. Multi-Page Builder | 0/TBD | Not started | - |
| 22. React Conversion & Output Targets | 0/TBD | Not started | - |
| 23. App Builder Dashboard & Deploy | 0/TBD | Not started | - |

---

## Coverage Map

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUN-01 | Phase 16 | Pending |
| FOUN-02 | Phase 16 | Pending |
| FOUN-03 | Phase 16 | Pending |
| FOUN-04 | Phase 16 | Pending |
| FLOW-01 | Phase 17 | Pending |
| BLDR-04 | Phase 17 | Pending |
| FLOW-02 | Phase 18 | Pending |
| FLOW-03 | Phase 18 | Pending |
| FLOW-04 | Phase 18 | Pending |
| SCRN-01 | Phase 19 | Pending |
| SCRN-02 | Phase 19 | Pending |
| SCRN-03 | Phase 19 | Pending |
| SCRN-04 | Phase 19 | Pending |
| FOUN-05 | Phase 19 | Pending |
| BLDR-02 | Phase 19 | Pending |
| ITER-01 | Phase 20 | Pending |
| ITER-02 | Phase 20 | Pending |
| ITER-03 | Phase 20 | Pending |
| ITER-04 | Phase 20 | Pending |
| FLOW-05 | Phase 20 | Pending |
| PAGE-01 | Phase 21 | Pending |
| PAGE-02 | Phase 21 | Pending |
| PAGE-03 | Phase 21 | Pending |
| PAGE-04 | Phase 21 | Pending |
| FLOW-06 | Phase 21 | Pending |
| OUTP-01 | Phase 22 | Pending |
| OUTP-02 | Phase 22 | Pending |
| OUTP-03 | Phase 22 | Pending |
| OUTP-04 | Phase 22 | Pending |
| OUTP-05 | Phase 22 | Pending |
| FLOW-07 | Phase 22 | Pending |
| BLDR-01 | Phase 23 | Pending |
| BLDR-03 | Phase 23 | Pending |
| FOUN-06 | Phase 23 | Pending |

**Coverage: 34/34 requirements mapped**

---

*Roadmap created: 2026-03-21*
*Milestone: v2.0 Broader App Builder*
*Phase range: 16–23 (v3.0 Admin Panel occupies Phases 7–15)*
