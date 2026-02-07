# Fix for Agent Connection Port Mismatch and 404 Error

The user encountered a persistent 404 error when connecting to the agent backend, even after correcting the route path. The investigation revealed that the application was communicating with the wrong backend port.

## Issue Diagnosis
1.  **Frontend Misconfiguration:** The frontend environment (`.env.local`) was configured with `NEXT_PUBLIC_API_URL=http://localhost:8001`.
2.  **Backend Status:** The `pikar-backend` service (running in Docker) is listening on port **8000** (mapped to 8000 internally).
3.  **Ghost Service:** Port 8001 was open and responding (likely a stale process or another service), but it did not have the correct A2A routes configured, returning 404.
4.  **Route Verification:** A debug probe confirmed that the backend on port 8000 correctly handles requests (responds 200 OK to probes) and has `A2A routes initialized successfully`.

## Applied Fixes
1.  **Corrected Port in `.env.local`:** Updated `frontend/.env.local` to point to the correct backend port:
    ```properties
    NEXT_PUBLIC_API_URL=http://localhost:8000
    ```
2.  **Verified Backend Functionality:** Confirmed via logs that `pikar-backend` on port 8000 has loaded the `a2a` and `adk` components successfully.

## Required One-Time Action
**Restart Frontend Server:** Because environment variables in `.env.local` are loaded at startup, the user MUST restart their frontend development server (`npm run dev`) for the changes to take effect.

Once restarted, the frontend will direct requests to `http://localhost:8000/a2a/app/run_sse`, which is the correctly configured endpoint.
