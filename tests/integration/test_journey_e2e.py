"""Integration-style test for journey -> initiative -> workflow start flow."""

from fastapi.testclient import TestClient

from app import fast_api_app
import app.routers.initiatives as initiatives_router
import app.routers.onboarding as onboarding_router
import app.services.supabase as supabase_service
import app.agents.strategic.tools as strategic_tools


def _override_user_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


class _StubJourneyQuery:
    def __init__(self, rows):
        self._rows = rows
        self._use_single = False
        self._limit = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def single(self):
        self._use_single = True
        return self

    def limit(self, value):
        self._limit = value
        return self

    def execute(self):
        class _Resp:
            pass

        r = _Resp()
        if self._use_single:
            r.data = self._rows[0] if self._rows else None
        else:
            r.data = self._rows[: self._limit] if self._limit else self._rows
        return r


class _StubSupabaseClient:
    def __init__(self, rows):
        self.rows = rows

    def table(self, _name):
        return _StubJourneyQuery(self.rows)


class _StubInitiativeService:
    def __init__(self):
        self.store = {
            "init-1": {
                "id": "init-1",
                "title": "First Client Acquisition",
                "metadata": {
                    "journey_id": "journey-1",
                    "desired_outcomes": "Acquire first 3 clients",
                    "timeline": "90 days",
                },
            }
        }

    async def create_initiative(self, **kwargs):
        created = {"id": "init-1", **kwargs}
        self.store["init-1"] = created
        return created

    async def get_initiative(self, initiative_id, user_id=None):
        return self.store.get(initiative_id)

    async def update_initiative(self, initiative_id, metadata=None, user_id=None, **kwargs):
        initiative = self.store[initiative_id]
        initiative["metadata"] = {**(initiative.get("metadata") or {}), **(metadata or {})}
        initiative.update(kwargs)
        return initiative

    async def list_templates(self, persona=None, category=None):
        return [{"id": "tmpl-1", "persona": persona or "solopreneur", "category": category or "sales", "name": "Lead Generation Workflow"}]


def test_journey_to_workflow_e2e(monkeypatch):
    stub_service = _StubInitiativeService()
    journey_rows = [
        {
            "id": "journey-1",
            "persona": "solopreneur",
            "title": "First Client Acquisition",
            "description": "Acquire first paying customers.",
            "stages": [{"name": "Research", "status": "pending"}],
            "kpis": ["Conversion rate"],
            "primary_workflow_template_name": "Lead Generation Workflow",
        }
    ]

    def _client_factory():
        return _StubSupabaseClient(journey_rows)

    async def _fake_start_journey_workflow(_initiative_id: str):
        return {
            "success": True,
            "workflow_execution_id": "exec-1",
            "template_name": "Lead Generation Workflow",
            "message": "Journey workflow started.",
            "requirements_satisfied": True,
            "missing_inputs": [],
        }

    monkeypatch.setattr(initiatives_router, "InitiativeService", lambda: stub_service)
    monkeypatch.setattr(initiatives_router, "get_service_client", _client_factory)
    monkeypatch.setattr(supabase_service, "get_service_client", _client_factory)
    monkeypatch.setattr(strategic_tools, "start_journey_workflow", _fake_start_journey_workflow)

    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            journeys_resp = client.get("/initiatives/templates?persona=solopreneur")
            assert journeys_resp.status_code in (200, 400)

            create_resp = client.post(
                "/initiatives/from-journey",
                json={
                    "journey_id": "journey-1",
                    "desired_outcomes": "Acquire first 3 clients",
                    "timeline": "90 days",
                },
            )
            assert create_resp.status_code == 200
            initiative_id = create_resp.json()["initiative"]["id"]
            assert initiative_id == "init-1"

            start_resp = client.post(f"/initiatives/{initiative_id}/start-journey-workflow")
            assert start_resp.status_code == 200
            payload = start_resp.json()
            assert payload["success"] is True
            assert payload["workflow_execution_id"] == "exec-1"
    finally:
        fast_api_app.app.dependency_overrides.clear()
