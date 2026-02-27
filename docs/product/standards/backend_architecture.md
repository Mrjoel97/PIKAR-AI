# Backend Architecture Standards

## 1. Supabase Best Practices (`supabase-best-practices`)
**Goal:** Secure, scalable database interactions.

-   **RLS (Row Level Security):**
    -   **CRITICAL:** Must be ENABLED on ALL public tables.
    -   **Policy:** Use `auth.uid()` checks explicitly.
-   **Authentication:**
    -   **Clerk Integration:** Use Third-Party Auth integration.
    -   **Never** use deprecated JWT templates.
-   **Database:**
    -   **Indexes:** Add indexes for ALL columns used in RLS policies.
    -   **Functions:** Use `SECURITY DEFINER` only when necessary and secure.
-   **Edge Functions:**
    -   Always verify JWT.
    -   Handle CORS properly.

## 2. Senior Backend Patterns (`senior-backend`)
**Goal:** Enterprise-grade system design.

-   **API Design:**
    -   Follow REST/RPC standards consistently.
    -   Validate all inputs (Pydantic/Zod).
-   **Database:**
    -   Use migrations for schema changes (no manual SQL).
    -   Optimize queries (avoid N+1).
-   **Security:**
    -   Defense in Depth: Validate at API gateway, Service layer, and Database (RLS).
    -   Secrets: Never commit keys. Use environment variables.
