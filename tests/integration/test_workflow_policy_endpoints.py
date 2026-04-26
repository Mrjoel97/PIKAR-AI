"""Integration tests for workflow policy/readiness endpoints."""

from fastapi.testclient import TestClient

from app import fast_api_app
import app.agents.strategic.tools as strategic_tools
import app.routers.initiatives as initiatives_router
import app.routers.onboarding as onboarding_router
import app.routers.workflows as workflows_router


def _override_user_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


class _StubWorkflowEngineError:
    async def start_workflow(self, **_kwargs):
        return {
            "error": "Template 'Draft Workflow' is not published for real-user starts",
            "error_code": "template_not_published",
            "lifecycle_status": "draft",
        }


class _StubWorkflowEngineNotReady:
    async def start_workflow(self, **_kwargs):
        return {
            "error": "Workflow 'Lead Generation Workflow' is not ready for execution",
            "error_code": "workflow_not_ready",
            "readiness": {"status": "blocked", "reason_codes": ["integration_missing"]},
        }


class _StubWorkflowEngineReadinessUnavailable:
    async def start_workflow(self, **_kwargs):
        return {
            "error": "Workflow readiness check failed",
            "error_code": "workflow_readiness_unavailable",
        }


class _StubKernelWorkflowStartFailed:
    async def start_workflow_mission(self, **_kwargs):
        return {
            "error": "Workflow orchestration failed to start",
            "error_code": "workflow_start_failed",
            "details": {"status": 400, "error": "Missing Supabase environment variables"},
        }


class _StubInitiativeService:
    async def get_initiative(self, _initiative_id, user_id=None):
        return {
            "id": "init-1",
            "metadata": {
                "desired_outcomes": "Acquire 10 customers",
                "timeline": "60 days",
            },
        }

    async def update_initiative(self, _initiative_id, metadata=None, user_id=None, **kwargs):
        return {
            "id": "init-1",
            "metadata": metadata or {},
            **kwargs,
        }


class _StubQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self._filters[key] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        class _Resp:
            pass

        rows = list(self._rows)
        status = self._filters.get("status")
        if status is not None:
            rows = [row for row in rows if row.get("status") == status]
        resp = _Resp()
        resp.data = rows
        return resp


class _StubReadinessClient:
    def __init__(self, workflow_rows, journey_rows):
        self._workflow_rows = workflow_rows
        self._journey_rows = journey_rows

    def table(self, name):
        if name == "workflow_readiness":
            return _StubQuery(self._workflow_rows)
        if name == "journey_readiness":
            return _StubQuery(self._journey_rows)
        raise AssertionError(f"Unexpected table name: {name}")


def test_workflows_start_returns_reason_code_details(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_KILL_SWITCH", "false")
    monkeypatch.setenv("WORKFLOW_CANARY_ENABLED", "false")
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: _StubWorkflowEngineError())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/workflows/start", json={"template_name": "Draft Workflow"})
        assert response.status_code == 409
        payload = response.json()
        assert payload["details"]["error_code"] == "template_not_published"
        assert payload["details"]["lifecycle_status"] == "draft"
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_workflows_start_returns_workflow_not_ready(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_KILL_SWITCH", "false")
    monkeypatch.setenv("WORKFLOW_CANARY_ENABLED", "false")
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: _StubWorkflowEngineNotReady())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/workflows/start", json={"template_name": "Lead Generation Workflow"})
        assert response.status_code == 409
        payload = response.json()
        assert payload["details"]["error_code"] == "workflow_not_ready"
        assert payload["details"]["readiness"]["status"] == "blocked"
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_workflows_start_returns_readiness_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_KILL_SWITCH", "false")
    monkeypatch.setenv("WORKFLOW_CANARY_ENABLED", "false")
    monkeypatch.setattr(
        workflows_router,
        "get_workflow_engine",
        lambda: _StubWorkflowEngineReadinessUnavailable(),
    )
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/workflows/start", json={"template_name": "Lead Generation Workflow"})
        assert response.status_code == 503
        payload = response.json()
        assert payload["details"]["error_code"] == "workflow_readiness_unavailable"
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_workflows_start_returns_workflow_start_failed_as_503(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_KILL_SWITCH", "false")
    monkeypatch.setenv("WORKFLOW_CANARY_ENABLED", "false")
    monkeypatch.setattr(
        workflows_router,
        "_get_agent_kernel",
        lambda: _StubKernelWorkflowStartFailed(),
    )
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/workflows/start", json={"template_name": "Social Media Campaign Workflow"})
        assert response.status_code == 503
        payload = response.json()
        assert payload["details"]["error_code"] == "workflow_start_failed"
        assert payload["details"]["details"]["status"] == 400
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_initiative_start_journey_maps_workflow_policy_errors(monkeypatch) -> None:
    async def _fake_start_journey_workflow(_initiative_id: str):
        return {
            "success": False,
            "error": "Workflow is blocked by readiness",
            "error_code": "workflow_not_ready",
            "readiness": {"status": "blocked", "reason_codes": ["integration_missing"]},
        }

    monkeypatch.setattr(initiatives_router, "InitiativeService", lambda: _StubInitiativeService())
    monkeypatch.setattr(strategic_tools, "start_journey_workflow", _fake_start_journey_workflow)
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/initiatives/init-1/start-journey-workflow")
        assert response.status_code == 409
        payload = response.json()
        assert payload["details"]["error_code"] == "workflow_not_ready"
        assert payload["details"]["readiness"]["status"] == "blocked"
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_initiative_start_journey_maps_template_not_published(monkeypatch) -> None:
    async def _fake_start_journey_workflow(_initiative_id: str):
        return {
            "success": False,
            "error": "Template is not published",
            "error_code": "template_not_published",
            "lifecycle_status": "draft",
        }

    monkeypatch.setattr(initiatives_router, "InitiativeService", lambda: _StubInitiativeService())
    monkeypatch.setattr(strategic_tools, "start_journey_workflow", _fake_start_journey_workflow)
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/initiatives/init-1/start-journey-workflow")
        assert response.status_code == 409
        payload = response.json()
        assert payload["details"]["error_code"] == "template_not_published"
        assert payload["details"]["lifecycle_status"] == "draft"
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_initiative_start_journey_maps_readiness_unavailable(monkeypatch) -> None:
    async def _fake_start_journey_workflow(_initiative_id: str):
        return {
            "success": False,
            "error": "Readiness lookup failed",
            "error_code": "workflow_readiness_unavailable",
        }

    monkeypatch.setattr(initiatives_router, "InitiativeService", lambda: _StubInitiativeService())
    monkeypatch.setattr(strategic_tools, "start_journey_workflow", _fake_start_journey_workflow)
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/initiatives/init-1/start-journey-workflow")
        assert response.status_code == 503
        payload = response.json()
        assert payload["details"]["error_code"] == "workflow_readiness_unavailable"
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_workflow_readiness_endpoint_can_include_journey_view(monkeypatch) -> None:
    workflow_rows = [
        {
            "template_id": "tpl-1",
            "template_name": "Lead Generation Workflow",
            "template_version": 3,
            "status": "ready",
        },
        {
            "template_id": "tpl-2",
            "template_name": "Product Launch Workflow",
            "template_version": 1,
            "status": "blocked",
        },
    ]
    journey_rows = [
        {
            "journey_id": "journey-1",
            "persona": "solopreneur",
            "title": "First Client Acquisition",
            "template_name": "Lead Generation Workflow",
            "readiness_status": "ready",
            "blockers": [],
        }
    ]

    monkeypatch.setattr(
        workflows_router,
        "get_service_client",
        lambda: _StubReadinessClient(workflow_rows, journey_rows),
    )
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.get("/workflows/readiness?status=ready&include_journeys=true")
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert payload["workflows"][0]["template_name"] == "Lead Generation Workflow"
        assert payload["journey_count"] == 1
        assert payload["journeys"][0]["journey_id"] == "journey-1"
    finally:
        fast_api_app.app.dependency_overrides.clear()


class _StubWorkflowEnginePersonaBlocked:
    async def start_workflow(self, **_kwargs):
        return {
            "error": "Workflow is not available for this persona",
            "error_code": "workflow_persona_not_allowed",
            "reason_code": "persona_not_allowed",
            "persona": "startup",
            "personas_allowed": ["enterprise"],
        }


def test_workflows_start_returns_persona_forbidden_details(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_KILL_SWITCH", "false")
    monkeypatch.setenv("WORKFLOW_CANARY_ENABLED", "false")
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: _StubWorkflowEnginePersonaBlocked())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post(
                "/workflows/start",
                headers={"x-pikar-persona": "startup"},
                json={"template_name": "Enterprise Controls"},
            )
        assert response.status_code == 403
        payload = response.json()
        assert payload["details"]["error_code"] == "workflow_persona_not_allowed"
        assert payload["details"]["reason_code"] == "persona_not_allowed"
        assert payload["details"]["persona"] == "startup"
        assert payload["details"]["personas_allowed"] == ["enterprise"]
    finally:
        fast_api_app.app.dependency_overrides.clear()
