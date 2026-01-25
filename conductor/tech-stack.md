# Pikar AI - Technology Stack

## 1. Overview

Pikar AI leverages a modern and robust technology stack designed for scalability, performance, and seamless integration of AI capabilities. The architecture combines the flexibility of Python for core agent development with the power of Supabase for backend services and Google Cloud for AI models and deployment.

## 2. Core Technologies

### Programming Languages
### Programming Languages
-   **Python:** Primary language for the entire backend, including AI agents (`ExecutiveAgent`, `SpecializedAgents`), Service Layer (`app/services`), and API Server (`FastAPI`).
-   **TypeScript:** Used for the Frontend (`React`) and optional Supabase Edge Function scripts if needed.

### AI/ML Framework & Models
-   **Google ADK (Agent Development Kit):** The foundational framework for building, orchestrating, and deploying AI agents.
-   **External Skills System:** Integration of 57+ domain-specific skills via npx and custom skill creator.
-   **Google Gemini 1.5 Pro, Google Gemini 1.5 Flash:** Advanced generative AI models from Google, serving as the core intelligence for all AI agents.
-   **Google `text-embedding-004`:** Used for generating embeddings for the Knowledge Vault's RAG system, enabling semantic search capabilities.

### Backend Services
### Backend Services
-   **FastAPI/Uvicorn:** The primary backend service implementing the Agent-to-Agent (A2A) protocol, business services (`app/services`), and orchestrating the AI agent ecosystem. Written in Python.
-   **Supabase:** Provides the PostgreSQL database, Authentication, Realtime subscriptions, and Vector store. (Edge Functions are supported but secondary to the main FastAPI application).

### Database
-   **PostgreSQL with `pgvector`:** The central database solution, integrated with Supabase, providing robust relational data storage and advanced vector indexing for efficient RAG operations.

### Authentication
-   **Supabase Auth:** Provides secure and scalable user authentication and authorization services.

### Frontend
-   **Next.js:** The React framework for the web, enabling server-side rendering and static site generation.
-   **React:** The declarative JavaScript library for building dynamic and interactive user interfaces.
-   **TypeScript:** Enhances code quality and maintainability for frontend development.
-   **TailwindCSS:** A utility-first CSS framework for rapid and consistent UI styling.
-   **Lucide React:** A consistent and lightweight icon library.

### Testing
-   **Vitest:** A blazing fast unit test framework powered by Vite.
-   **React Testing Library:** Simple and complete testing utilities that encourage good testing practices.

### Deployment & Infrastructure
-   **Google Cloud Run:** Serverless platform for deploying containerized applications, offering auto-scaling and simplified management.
-   **Terraform:** Infrastructure as Code (IaC) tool used for provisioning and managing Google Cloud resources.

### Real-time Capabilities
-   **Supabase Realtime:** Enables real-time updates and communication within the application, crucial for interactive agent experiences and live dashboards.

### Observability
-   **OpenTelemetry:** Standardized framework for collecting telemetry data (traces, metrics, logs).
-   **Google Cloud Trace:** Distributed tracing service for monitoring application performance and debugging.
-   **Google Cloud Logging:** Centralized logging service for collecting and analyzing application logs.
-   **BigQuery:** Data warehouse for advanced analytics and storage of observability data.

## 3. Best Practices & Standards

### Frontend Best Practices
-   **React Modernization:**
    -   Must use Functional Components and Hooks (no Class Components).
    -   Adopt React 18 Concurrent features (Suspense, Transitions) where beneficial.
    -   Strict Mode enabled to catch double-invocation bugs.
-   **Vercel & Next.js Performance:**
    -   **No Waterfalls:** Eliminate request chains; use `Promise.all` or parallel data fetching.
    -   **Bundle Optimization:** No barrel exports (`index.ts` re-exports). Use `next/dynamic` for heavy components.
    -   **Server Components:** Prefer Server Components for data fetching to reduce client JS.
-   **UI/UX:**
    -   Follow `ui-ux-pro-max` guidelines for accessibility and touch targets (44px+).
    -   Visuals: Use `nano-banana` for high-fidelity asset generation.
    -   3D/Video: Use `threejs-fundamentals` and `remotion` for immersive experiences.

### Backend Best Practices
-   **Supabase Security:**
    -   **RLS (Row Level Security):** ENABLED on all public tables.
    -   **Auth:** Use Clerk integration patterns; never use deprecated JWT templates.
    -   **Performance:** Add indexes for all columns used in RLS policies.
    -   **Logic:** Minimize joins in RLS; use `SECURITY DEFINER` carefully.
-   **Architecture:**
    -   Follow `senior-backend` patterns for scalable design.
    -   Use `fastapi-templates` for rapid, standard service creation.

### Meta-Skills & Process
-   **Systematic Debugging:**
    -   Mandatory 4-Phase Protocol: Root Cause -> Pattern -> Hypothesis -> Fix.
    -   "No Fixes Without Root Cause Investigation First."
-   **Pre-Action:**
    -   **Using Superpowers:** Always check available skills before starting a task.
-   **Documentation:**
    -   **Writing Skills:** Documentation should be TDD-based (Test-Driven Documentation) where possible.
