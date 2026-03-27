"""Comprehensive Locust load test for Pikar-AI authenticated API scenarios.

Usage:
    # Set env vars for test user credentials and Supabase config:
    export SUPABASE_URL=https://your-project.supabase.co
    export SUPABASE_ANON_KEY=eyJ...
    export LOAD_TEST_EMAIL=loadtest@example.com
    export LOAD_TEST_PASSWORD=your-password
    # Optionally override the backend host (defaults to localhost:8000):
    export PIKAR_HOST=http://localhost:8000

    # Run against local backend
    locust -f tests/load_test/locustfile.py --host http://localhost:8000

    # Run headless (100 users, spawn 10/s, run 5 minutes)
    locust -f tests/load_test/locustfile.py --host http://localhost:8000 \
        --headless -u 100 -r 10 --run-time 5m

    # Run with web UI on custom port
    locust -f tests/load_test/locustfile.py --host http://localhost:8000 --web-port 8089
"""

import json
import logging
import os
import time
import uuid
from typing import Any

import requests
from locust import HttpUser, between, events, tag, task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pikar-loadtest")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
LOAD_TEST_EMAIL = os.environ.get("LOAD_TEST_EMAIL", "")
LOAD_TEST_PASSWORD = os.environ.get("LOAD_TEST_PASSWORD", "")

# Chat prompts that exercise different agent branches
CHAT_PROMPTS = [
    "Give me a summary of today's briefing",
    "What are our active initiatives?",
    "Draft a quick marketing email for our product launch",
    "Analyze our revenue trends for this quarter",
    "What compliance tasks are pending?",
    "Create a content brief for a blog post about AI productivity",
    "How are our customer support tickets trending?",
    "Run a quick competitive analysis on our market",
    "What workflows are currently running?",
    "Generate a financial forecast for next month",
]

# Shorter prompts for high-frequency SSE tests (faster agent responses)
QUICK_PROMPTS = [
    "Hello",
    "What time is it?",
    "List my pending tasks",
    "Show my calendar for today",
    "What's new?",
]


# ---------------------------------------------------------------------------
# Supabase auth helper
# ---------------------------------------------------------------------------
def authenticate_supabase(email: str, password: str) -> dict[str, Any]:
    """Sign in to Supabase and return the session (access_token, refresh_token, user)."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set for authenticated tests. "
            "See the module docstring for usage."
        )

    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        },
        json={"email": email, "password": password},
        timeout=15,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Supabase auth failed ({resp.status_code}): {resp.text}"
        )

    data = resp.json()
    logger.info("Authenticated as %s (user_id=%s)", email, data["user"]["id"])
    return data


def refresh_supabase_token(refresh_token: str) -> dict[str, Any]:
    """Refresh an expired Supabase JWT."""
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        },
        json={"refresh_token": refresh_token},
        timeout=15,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Token refresh failed ({resp.status_code}): {resp.text}"
        )
    return resp.json()


# ---------------------------------------------------------------------------
# Listener: log summary at test end
# ---------------------------------------------------------------------------
@events.quitting.add_listener
def _on_quitting(environment, **kwargs):
    if environment.stats.total.fail_ratio > 0.05:
        logger.warning(
            "FAIL RATIO %.1f%% exceeds 5%% threshold",
            environment.stats.total.fail_ratio * 100,
        )


# ===========================================================================
# Main User class — authenticated scenarios
# ===========================================================================
class PikarUser(HttpUser):
    """Simulates an authenticated Pikar-AI user exercising core API flows.

    Weighted tasks mirror real usage patterns:
    - Dashboard/read endpoints are most frequent
    - Chat (SSE) is lower frequency due to AI inference cost
    - Workflow operations are periodic
    """

    wait_time = between(2, 6)

    # Auth state
    _access_token: str = ""
    _refresh_token: str = ""
    _user_id: str = ""
    _token_expires_at: float = 0.0

    # Session tracking
    _session_id: str = ""
    _cached_templates: list[dict] = []

    def on_start(self):
        """Authenticate with Supabase before starting tasks."""
        if not LOAD_TEST_EMAIL or not LOAD_TEST_PASSWORD:
            logger.warning(
                "LOAD_TEST_EMAIL / LOAD_TEST_PASSWORD not set — "
                "skipping auth, requests will be anonymous"
            )
            self._user_id = f"anon-{uuid.uuid4().hex[:8]}"
            self._session_id = f"session-{uuid.uuid4()}"
            return

        try:
            session = authenticate_supabase(LOAD_TEST_EMAIL, LOAD_TEST_PASSWORD)
            self._access_token = session["access_token"]
            self._refresh_token = session["refresh_token"]
            self._user_id = session["user"]["id"]
            self._token_expires_at = time.time() + session.get("expires_in", 3600) - 60
            self._session_id = f"loadtest-{uuid.uuid4()}"
            logger.info("User %s ready, session %s", self._user_id, self._session_id)
        except Exception as e:
            logger.error("Auth failed: %s — falling back to anonymous", e)
            self._user_id = f"anon-{uuid.uuid4().hex[:8]}"
            self._session_id = f"session-{uuid.uuid4()}"

    def _ensure_token(self):
        """Refresh the token if it's about to expire."""
        if self._refresh_token and time.time() > self._token_expires_at:
            try:
                session = refresh_supabase_token(self._refresh_token)
                self._access_token = session["access_token"]
                self._refresh_token = session["refresh_token"]
                self._token_expires_at = time.time() + session.get("expires_in", 3600) - 60
                logger.info("Token refreshed for user %s", self._user_id)
            except Exception as e:
                logger.error("Token refresh failed: %s", e)

    @property
    def _is_anonymous(self) -> bool:
        return not self._access_token

    def _auth_headers(self) -> dict[str, str]:
        """Return headers with a valid Bearer token."""
        self._ensure_token()
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _get_authed(self, path: str, name: str | None = None):
        """GET an auth-protected endpoint, treating 401/403/404 as success in anonymous mode."""
        with self.client.get(
            path,
            name=name or path,
            headers=self._auth_headers(),
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code in (401, 403, 404) and self._is_anonymous:
                resp.success()  # Expected without credentials
            else:
                resp.failure(f"HTTP {resp.status_code}")

    # -----------------------------------------------------------------------
    # Health checks (lightweight, always pass, good baseline)
    # -----------------------------------------------------------------------
    @tag("health")
    @task(3)
    def health_live(self):
        """Liveness probe — no dependencies."""
        self.client.get("/health/live", name="/health/live")

    @tag("health")
    @task(1)
    def health_connections(self):
        """Connection health — Supabase + cache."""
        self.client.get("/health/connections", name="/health/connections")

    # -----------------------------------------------------------------------
    # SSE Chat — the core interaction (AI inference, most expensive)
    # -----------------------------------------------------------------------
    @tag("chat")
    @task(5)
    def chat_sse(self):
        """Send a chat message via SSE and consume the full event stream."""
        import random

        prompt = random.choice(CHAT_PROMPTS)
        payload = {
            "session_id": self._session_id,
            "user_id": self._user_id,
            "new_message": {"parts": [{"text": prompt}]},
            "agent_mode": random.choice(["auto", "collab", "ask"]),
        }

        start = time.time()
        with self.client.post(
            "/a2a/app/run_sse",
            name="/a2a/app/run_sse [chat]",
            headers=self._auth_headers(),
            json=payload,
            catch_response=True,
            stream=True,
        ) as resp:
            if resp.status_code == 200:
                event_count = 0
                has_error = False
                for line in resp.iter_lines():
                    if line:
                        event_count += 1
                        decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                        # Check for error events in the SSE stream
                        if decoded.startswith("data: "):
                            try:
                                data = json.loads(decoded[6:])
                                if isinstance(data, dict) and data.get("error"):
                                    has_error = True
                                    resp.failure(f"SSE error: {data['error']}")
                            except json.JSONDecodeError:
                                pass

                elapsed_ms = (time.time() - start) * 1000
                if not has_error:
                    resp.success()
                    logger.debug(
                        "Chat SSE completed: %d events in %.0fms", event_count, elapsed_ms
                    )
            elif resp.status_code == 429:
                resp.failure("Rate limited (429)")
            elif resp.status_code == 503:
                resp.failure("Server at capacity (503)")
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @tag("chat")
    @task(2)
    def chat_sse_quick(self):
        """Lightweight chat — quick prompt, tests SSE connection churn."""
        import random

        payload = {
            "session_id": self._session_id,
            "user_id": self._user_id,
            "new_message": {"parts": [{"text": random.choice(QUICK_PROMPTS)}]},
            "agent_mode": "auto",
        }

        with self.client.post(
            "/a2a/app/run_sse",
            name="/a2a/app/run_sse [quick]",
            headers=self._auth_headers(),
            json=payload,
            catch_response=True,
            stream=True,
        ) as resp:
            if resp.status_code == 200:
                # Consume stream but don't track individual events
                for _ in resp.iter_lines():
                    pass
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    # -----------------------------------------------------------------------
    # Briefing — daily briefing dashboard
    # -----------------------------------------------------------------------
    @tag("briefing")
    @task(6)
    def get_briefing(self):
        """Fetch today's briefing — common dashboard load."""
        self._get_authed("/briefing/today")

    @tag("briefing")
    @task(3)
    def get_dashboard_summary(self):
        """Dashboard summary aggregation."""
        self._get_authed("/briefing/dashboard-summary")

    @tag("briefing")
    @task(1)
    def get_briefing_preferences(self):
        """Briefing preferences — lightweight read."""
        self._get_authed("/briefing/preferences")

    # -----------------------------------------------------------------------
    # Workflows — template listing, execution listing, start
    # -----------------------------------------------------------------------
    @tag("workflows")
    @task(4)
    def list_workflow_templates(self):
        """Browse available workflow templates."""
        with self.client.get(
            "/workflows/templates",
            name="/workflows/templates",
            headers=self._auth_headers(),
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    self._cached_templates = resp.json()
                except Exception:
                    self._cached_templates = []
                resp.success()
            elif resp.status_code in (401, 403) and self._is_anonymous:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @tag("workflows")
    @task(3)
    def list_workflow_executions(self):
        """List recent workflow executions."""
        self._get_authed("/workflows/executions")

    @tag("workflows")
    @task(1)
    def workflow_execution_stats(self):
        """Get workflow execution statistics."""
        self._get_authed("/workflows/executions/stats")

    @tag("workflows")
    @task(1)
    def workflow_readiness(self):
        """Check workflow readiness status."""
        self._get_authed("/workflows/readiness")

    @tag("workflows")
    @task(1)
    def start_workflow(self):
        """Start a workflow from a template (write operation)."""
        import random

        if not self._cached_templates:
            return  # Skip if no templates fetched yet

        template = random.choice(self._cached_templates)
        template_id = template.get("id") or template.get("template_id")
        if not template_id:
            return

        payload = {
            "template_id": template_id,
            "user_id": self._user_id,
            "inputs": {"test_run": True, "source": "load_test"},
        }

        with self.client.post(
            "/workflows/start",
            name="/workflows/start",
            headers=self._auth_headers(),
            json=payload,
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            elif resp.status_code in (401, 403, 422):
                resp.success()  # 401/403 in anon mode, 422 for test payloads
            else:
                resp.failure(f"HTTP {resp.status_code}")

    # -----------------------------------------------------------------------
    # Departments — org chart & department activity
    # -----------------------------------------------------------------------
    @tag("departments")
    @task(4)
    def list_departments(self):
        """List all departments."""
        self._get_authed("/departments")

    @tag("departments")
    @task(2)
    def department_activity(self):
        """Department activity feed."""
        self._get_authed("/departments/activity")

    @tag("departments")
    @task(1)
    def department_decision_log(self):
        """Department decision log."""
        self._get_authed("/departments/decision-log")

    # -----------------------------------------------------------------------
    # Initiatives — strategic initiatives
    # -----------------------------------------------------------------------
    @tag("initiatives")
    @task(3)
    def list_initiatives(self):
        """List all initiatives."""
        self._get_authed("/initiatives")

    @tag("initiatives")
    @task(1)
    def list_initiative_templates(self):
        """List initiative templates."""
        self._get_authed("/initiatives/templates")

    # -----------------------------------------------------------------------
    # Reports
    # -----------------------------------------------------------------------
    @tag("reports")
    @task(3)
    def list_reports(self):
        """List generated reports."""
        self._get_authed("/reports")

    @tag("reports")
    @task(1)
    def report_categories(self):
        """List report categories."""
        self._get_authed("/reports/categories")

    # -----------------------------------------------------------------------
    # Finance
    # -----------------------------------------------------------------------
    @tag("finance")
    @task(2)
    def finance_invoices(self):
        """List invoices."""
        self._get_authed("/finance/invoices")

    @tag("finance")
    @task(1)
    def finance_revenue(self):
        """Revenue timeseries."""
        self._get_authed("/finance/revenue-timeseries")

    # -----------------------------------------------------------------------
    # Content
    # -----------------------------------------------------------------------
    @tag("content")
    @task(2)
    def list_bundles(self):
        """List content bundles."""
        self._get_authed("/content/bundles")

    @tag("content")
    @task(1)
    def list_campaigns(self):
        """List campaigns."""
        self._get_authed("/content/campaigns")

    # -----------------------------------------------------------------------
    # Approvals
    # -----------------------------------------------------------------------
    @tag("approvals")
    @task(2)
    def list_pending_approvals(self):
        """List pending approvals."""
        self._get_authed("/approvals/pending/list")

    @tag("approvals")
    @task(1)
    def approval_history(self):
        """Approval history."""
        self._get_authed("/approvals/history")

    # -----------------------------------------------------------------------
    # Onboarding status
    # -----------------------------------------------------------------------
    @tag("onboarding")
    @task(1)
    def onboarding_status(self):
        """Check onboarding completion status."""
        self._get_authed("/onboarding/status")

    # -----------------------------------------------------------------------
    # Configuration — session config (loaded on every page)
    # -----------------------------------------------------------------------
    @tag("config")
    @task(3)
    def session_config(self):
        """Session config — loaded on every frontend page navigation."""
        self._get_authed("/configuration/session-config")

    @tag("config")
    @task(1)
    def mcp_status(self):
        """MCP integration status."""
        self._get_authed("/configuration/mcp-status")

    # -----------------------------------------------------------------------
    # Sales
    # -----------------------------------------------------------------------
    @tag("sales")
    @task(1)
    def sales_contacts(self):
        """Sales contacts list."""
        self._get_authed("/sales/contacts")

    # -----------------------------------------------------------------------
    # Support
    # -----------------------------------------------------------------------
    @tag("support")
    @task(1)
    def support_tickets(self):
        """List support tickets."""
        self._get_authed("/support/tickets")


# ===========================================================================
# High-frequency chat-only user (stress test SSE concurrency)
# ===========================================================================
class ChatHeavyUser(HttpUser):
    """Simulates a power user who sends many chat messages.

    Use this to stress-test SSE connection limits and AI inference throughput.
    Run with: locust -f locustfile.py --host ... -t ChatHeavyUser
    """

    wait_time = between(1, 3)
    weight = 1  # Lower weight — spawn fewer of these

    _access_token: str = ""
    _refresh_token: str = ""
    _user_id: str = ""
    _token_expires_at: float = 0.0
    _session_id: str = ""

    def on_start(self):
        if LOAD_TEST_EMAIL and LOAD_TEST_PASSWORD:
            try:
                session = authenticate_supabase(LOAD_TEST_EMAIL, LOAD_TEST_PASSWORD)
                self._access_token = session["access_token"]
                self._refresh_token = session["refresh_token"]
                self._user_id = session["user"]["id"]
                self._token_expires_at = time.time() + session.get("expires_in", 3600) - 60
            except Exception as e:
                logger.error("ChatHeavyUser auth failed: %s", e)
                self._user_id = f"anon-{uuid.uuid4().hex[:8]}"
        else:
            self._user_id = f"anon-{uuid.uuid4().hex[:8]}"
        self._session_id = f"heavy-{uuid.uuid4()}"

    def _auth_headers(self) -> dict[str, str]:
        if self._refresh_token and time.time() > self._token_expires_at:
            try:
                session = refresh_supabase_token(self._refresh_token)
                self._access_token = session["access_token"]
                self._refresh_token = session["refresh_token"]
                self._token_expires_at = time.time() + session.get("expires_in", 3600) - 60
            except Exception:
                pass
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    @tag("chat", "stress")
    @task(3)
    def rapid_chat(self):
        """Rapid-fire chat to test SSE connection limits."""
        import random

        payload = {
            "session_id": self._session_id,
            "user_id": self._user_id,
            "new_message": {"parts": [{"text": random.choice(QUICK_PROMPTS)}]},
            "agent_mode": "auto",
        }

        with self.client.post(
            "/a2a/app/run_sse",
            name="/a2a/app/run_sse [rapid]",
            headers=self._auth_headers(),
            json=payload,
            catch_response=True,
            stream=True,
        ) as resp:
            if resp.status_code == 200:
                for _ in resp.iter_lines():
                    pass
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited (429) — SSE connection limit hit")
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @tag("chat", "stress")
    @task(1)
    def new_session_chat(self):
        """Start a brand-new session each time — tests session creation overhead."""
        import random

        fresh_session = f"fresh-{uuid.uuid4()}"
        payload = {
            "session_id": fresh_session,
            "user_id": self._user_id,
            "new_message": {"parts": [{"text": random.choice(CHAT_PROMPTS)}]},
            "agent_mode": "auto",
        }

        with self.client.post(
            "/a2a/app/run_sse",
            name="/a2a/app/run_sse [new-session]",
            headers=self._auth_headers(),
            json=payload,
            catch_response=True,
            stream=True,
        ) as resp:
            if resp.status_code == 200:
                for _ in resp.iter_lines():
                    pass
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
