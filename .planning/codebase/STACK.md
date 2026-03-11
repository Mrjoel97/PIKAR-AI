# Technology Stack

**Analysis Date:** 2026-03-11

## Languages

**Primary:**
- Python 3.10+ - Backend agent system, FastAPI application, business logic
- TypeScript 5.x - Frontend React components and Next.js application
- JavaScript (Node.js) - Remotion video rendering and build tooling

**Secondary:**
- SQL - Supabase PostgreSQL queries via ORM

## Runtime

**Environment:**
- Python 3.10-3.13 (pyproject.toml specifies `>=3.10,<3.14`)
- Node.js (bundled in Docker) - For Remotion video rendering and frontend builds
- Docker containerization for deployment

**Package Managers:**
- `uv` (Astral package manager) v0.8.13 - Primary Python package manager with lockfile `uv.lock`
- `npm` - Node.js dependency management with `package-lock.json` for frontend and remotion-render

## Frameworks

**Core:**
- FastAPI ~0.115.8 - REST API backend framework
- Google ADK >=1.16.0,<2.0.0 - Multi-agent framework from Google
- A2A SDK ~=0.3.9 - Agent-to-Agent protocol for inter-agent communication
- Next.js 16.1.4 - Frontend React framework with app router and TypeScript
- React 19.2.3 - UI component library (both frontend and Remotion)

**Agent/AI:**
- google-genai >=0.2.0 - Google Gemini API client
- google-cloud-aiplatform[evaluation] >=1.118.0,<2.0.0 - Vertex AI integration

**Video Rendering:**
- Remotion ^4.0.421 - Programmatic video rendering (frontend, server-side via subprocess)
- @remotion/transitions ^4.0.422 - Video transition library
- @remotion/cli ^4.0.421 - CLI for rendering
- ffmpeg - System dependency for video encoding in Docker

**Testing:**
- pytest >=8.3.4,<9.0.0 - Python testing framework
- pytest-asyncio >=0.23.8,<1.0.0 - Async test support
- pytest-cov >=5.0.0,<6.0.0 - Code coverage
- vitest ^4.0.18 - JavaScript unit testing (frontend)
- @testing-library/react ^16.3.2 - React component testing
- @testing-library/dom ^10.4.1 - DOM testing utilities
- jsdom ^27.4.0 - DOM implementation for Node.js testing

**Build/Dev:**
- Tailwind CSS ^4 - Utility-first CSS framework (frontend)
- @tailwindcss/postcss ^4 - PostCSS plugin for Tailwind
- postcss - CSS transformation
- ESLint ^9 - JavaScript linting
- eslint-config-next 16.1.4 - Next.js ESLint configuration
- Babel Compiler ^1.0.0 - React Compiler for automatic memoization
- Turbopack - Fast JavaScript bundler (integrated in Next.js 16)

**Linting/Formatting:**
- ruff >=0.4.6,<1.0.0 - Python linter and formatter (Astral)
- ty >=0.0.1a0 - Astral's Rust-based type checker
- codespell >=2.2.0,<3.0.0 - Spell checker for documentation

**Database/ORM:**
- SQLAlchemy >=2.0.0 - Python ORM (in dev dependencies)
- Alembic >=1.13.0 - Database schema migration (in dev dependencies)
- asyncpg >=0.30.0,<1.0.0 - PostgreSQL async driver

**API/Utilities:**
- uvicorn ~=0.34.0 - ASGI application server
- slowapi >=0.1.9 - Rate limiting middleware
- pydantic-settings >=2.0.0 - Configuration management
- pydantic (implicit) - Data validation via pydantic-settings
- python-multipart >=0.0.9 - Multipart form data parsing
- nest-asyncio >=1.6.0,<2.0.0 - Nested asyncio event loop support

**Document Processing:**
- reportlab >=4.4.9 - PDF generation
- pypdf >=6.6.2 - PDF reading/manipulation
- python-docx >=1.1.0 - Word document generation
- python-pptx >=1.0.2 - PowerPoint generation
- openpyxl >=3.1.0 - Excel file handling
- jspdf ^4.1.0 - JavaScript PDF generation (frontend)

**Caching/Async:**
- redis >=5.0.0,<6.0.0 - Redis client for caching and circuit breakers
- redis:alpine - Docker image for Redis service

**API Clients:**
- google-api-python-client >=2.187.0 - Google Sheets, Drive, Gmail APIs
- google-auth >=2.45.0 - Google authentication
- gcsfs >=2024.11.0 - Google Cloud Storage filesystem
- google-cloud-logging >=3.12.0,<4.0.0 - Cloud Logging integration
- supabase >=2.27.2,<3.0.0 - Supabase client library
- @supabase/supabase-js ^2.91.1 - JavaScript Supabase client
- @supabase/auth-helpers-nextjs ^0.15.0 - Supabase auth for Next.js
- @supabase/ssr ^0.8.0 - Supabase SSR support
- stripe >=7.0.0,<8.0.0 - Stripe payment processing
- cryptography >=46.0.3 - Cryptographic operations

**OpenTelemetry:**
- opentelemetry-instrumentation-google-genai >=0.1.0,<1.0.0 - Tracing for Google Genai

**Frontend UI/Animation:**
- framer-motion ^12.29.0 - Animation library
- lucide-react ^0.563.0 - Icon component library (tree-shaken via modularizeImports)
- react-markdown ^10.1.0 - Markdown rendering
- remark-gfm ^4.0.1 - GitHub-flavored markdown extension
- reactflow ^11.11.4 - Node-based UI for workflows
- @heroicons/react ^2.2.0 - Hero icon library
- sonner ^2.0.7 - Toast notification library
- @microsoft/fetch-event-source ^2.0.1 - Server-sent events client

**Other:**
- PyJWT >=2.8.0 - JWT token handling
- python-dotenv (implicit) - Environment variable loading
- httpx (implicit from supabase) - HTTP client

## Configuration

**Environment:**
Configuration is loaded from:
1. `.env` file at project root (mounted in Docker at `/code/.env`)
2. `.env` file in `app/` directory (for app-specific overrides)
3. Environment variables set at runtime

Key configuration categories:
- **Google AI:** `GOOGLE_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`
- **Supabase:** `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- **Redis:** `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_DB`, `REDIS_MAX_CONNECTIONS`
- **Stripe:** `STRIPE_API_KEY`
- **Remotion:** `REMOTION_RENDER_ENABLED`, `REMOTION_RENDER_TIMEOUT`, `REMOTION_RENDER_SCALE`
- **Workflow Runtime:** `WORKFLOW_SERVICE_SECRET`, `WORKFLOW_STRICT_TOOL_RESOLUTION`, `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD`

Validation occurs at startup via `app.config.validation.validate_startup()` - see `app/config/validation.py` for required/optional variables.

**Build:**
- `pyproject.toml` - Python project metadata and dependency configuration (PEP 517 format)
- `uv.lock` - Locked Python dependency versions
- `frontend/package.json` - Frontend npm dependencies
- `frontend/package-lock.json` - Locked npm versions
- `remotion-render/package-lock.json` - Locked remotion rendering dependencies
- `frontend/tsconfig.json` - TypeScript configuration with path aliases (`@/*` → `./src/*`)
- `frontend/next.config.ts` - Next.js configuration (Turbopack, React Compiler, image optimization)
- `frontend/postcss.config.mjs` - PostCSS configuration for Tailwind CSS
- `frontend/eslint.config.mjs` - ESLint v9 flat configuration
- `frontend/vitest.config.mts` - Vitest configuration
- `pyproject.toml` tool sections:
  - `[tool.ruff]` - Python linter config (line-length 88, selects E/F/W/I/C/B/UP/RUF)
  - `[tool.ty]` - Type checker configuration
  - `[tool.codespell]` - Spell checker exclusions
  - `[tool.pytest.ini_options]` - Pytest configuration
  - `[tool.hatch.build.targets.wheel]` - Build configuration
  - `[tool.agent-starter-pack]` - Generation metadata (ADK template context)

## Platform Requirements

**Development:**
- Docker Desktop (for container-based development)
- Python 3.10+ (local development without Docker)
- Node.js/npm (bundled in Docker for Remotion)
- FFmpeg (bundled in Docker for video rendering)
- Redis (runs in Docker via `redis:alpine`)
- PostgreSQL (via Supabase - cloud or local)

**Production:**
- Deployment target: Google Cloud Run (configured in `pyproject.toml` as `deployment_target`)
- Cloud Build for CI/CD (`cicd_runner`)
- Docker containerization via `Dockerfile` (Python 3.11-slim base)
- Health checks: Python subprocess check for backend, curl for frontend
- Service architecture:
  - **Backend:** `pikar-backend` container (FastAPI + uvicorn on port 8000)
  - **Frontend:** `pikar-frontend` container (Next.js on port 3000)
  - **Cache:** `pikar-redis` container (redis:alpine on port 6379)
  - Network: `pikar-network` bridge for inter-container communication

**Key Runtime Details:**
- Non-root user execution (appuser, UID 10001) for security
- Shared Docker volumes for hot-reload in development
- Masked node_modules to prevent Windows/Linux conflicts
- Google DNS (8.8.8.8, 8.8.4.4) in containers for reliable resolution
- Environment-specific behavior:
  - `LOCAL_DEV_BYPASS=1` - Skips validation in development
  - `SKIP_ENV_VALIDATION=1` - Disables startup validation
  - Production mode fails fast on validation errors

---

*Stack analysis: 2026-03-11*
