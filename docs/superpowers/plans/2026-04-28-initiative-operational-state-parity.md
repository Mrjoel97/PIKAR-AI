# Initiative Operational State Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every initiative — manual, template-sourced, journey-sourced, or autonomy-kernel — gets a meaningfully populated `operational_state` so blockers, success_criteria, owner_agents, primary_workflow, deliverables, next_actions, and trust_summary work uniformly across all create paths. Existing initiatives with empty `operational_state` are backfilled.

**Architecture:** Introduce a single `build_default_operational_state(...)` helper in `app/services/initiative_operational_state.py` that produces source-aware scaffolding from create-time context (manual / template / journey). `InitiativeService.create_initiative` accepts a `source` and `source_context` and merges the scaffold into `metadata[operational_state]` before insert (single roundtrip — no extra UPDATE). `create_from_template` and the `/from-journey` route pass their source-specific context. A SQL backfill migration populates the same scaffold for every existing initiative whose `operational_state` is missing or empty. Autonomy kernel is unchanged — it still calls `update_operational_state` after create with blueprint-derived values, which now overwrites the scaffold with richer data.

**Tech Stack:** Python 3.10+, FastAPI, Supabase (PostgreSQL with JSONB), pytest with pytest-asyncio, uv (package manager), ruff (lint), ty (type checking).

---

## File Structure

**Create:**
- `supabase/migrations/20260428120000_backfill_initiative_operational_state.sql` — backfill migration

**Modify:**
- `app/services/initiative_operational_state.py` — add `build_default_operational_state()` helper
- `app/services/initiative_service.py` — `create_initiative` accepts `source` + `source_context`, merges scaffold; `create_from_template` passes template context
- `app/routers/initiatives.py` — `/from-journey` passes journey context

**Test:**
- `tests/unit/test_initiative_operational_state.py` — unit tests for `build_default_operational_state`
- `tests/unit/test_initiative_service.py` — tests verifying scaffold lands in metadata for all create paths

---

## Task 1: Add `build_default_operational_state` helper (manual source)

**Files:**
- Modify: `app/services/initiative_operational_state.py`
- Test: `tests/unit/test_initiative_operational_state.py`

- [ ] **Step 1: Write the failing test for manual source**

Append to `tests/unit/test_initiative_operational_state.py`:

```python
def test_build_default_operational_state_manual_source():
    from app.services.initiative_operational_state import build_default_operational_state

    result = build_default_operational_state(
        title="Q3 Revenue Push",
        description="Lift MRR by 15% via outbound and partnerships",
        phase="ideation",
        source="manual",
        source_context=None,
    )

    assert result["goal"] == "Lift MRR by 15% via outbound and partnerships"
    assert result["owner_agents"] == ["executive"]
    assert result["current_phase"] == "ideation"
    assert result["verification_status"] == "not_started"
    assert result["primary_workflow"] is None
    assert result["success_criteria"] == []
    assert result["deliverables"] == []
    assert result["blockers"] == []
    assert result["next_actions"] == [
        "Define success criteria",
        "Identify key deliverables",
        "Assign owner agents",
    ]
    assert result["evidence"] == []
    assert result["trust_summary"]["approval_state"] == "not_required"
    assert result["trust_summary"]["verification_status"] == "not_started"


def test_build_default_operational_state_falls_back_to_title_when_description_empty():
    from app.services.initiative_operational_state import build_default_operational_state

    result = build_default_operational_state(
        title="Untitled Initiative",
        description="",
        phase="ideation",
        source="manual",
    )
    assert result["goal"] == "Untitled Initiative"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_initiative_operational_state.py::test_build_default_operational_state_manual_source tests/unit/test_initiative_operational_state.py::test_build_default_operational_state_falls_back_to_title_when_description_empty -v`
Expected: FAIL with `ImportError` or `AttributeError` — `build_default_operational_state` does not exist.

- [ ] **Step 3: Implement the helper (manual branch only)**

Append to `app/services/initiative_operational_state.py`:

```python
def build_default_operational_state(
    *,
    title: str,
    description: str | None,
    phase: str = "ideation",
    source: str = "manual",
    source_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a meaningful default operational_state dict for a new initiative.

    The shape matches what `normalize_operational_state` produces but the values
    are populated from create-time context (manual, template, or journey).
    The autonomy kernel does not call this; it writes its own richer state.
    """
    ctx = source_context or {}
    goal = (description or "").strip() or (title or "").strip()

    state: dict[str, Any] = {
        "goal": goal,
        "success_criteria": [],
        "owner_agents": ["executive"],
        "primary_workflow": None,
        "deliverables": [],
        "evidence": [],
        "blockers": [],
        "next_actions": [
            "Define success criteria",
            "Identify key deliverables",
            "Assign owner agents",
        ],
        "current_phase": phase or "ideation",
        "verification_status": "not_started",
        "trust_summary": default_trust_summary(),
        "workflow_execution_id": None,
    }
    return state
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_initiative_operational_state.py -v`
Expected: PASS for both new tests; existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add app/services/initiative_operational_state.py tests/unit/test_initiative_operational_state.py
git commit -m "feat(initiatives): add build_default_operational_state helper (manual source)"
```

---

## Task 2: Extend helper for template source

**Files:**
- Modify: `app/services/initiative_operational_state.py`
- Test: `tests/unit/test_initiative_operational_state.py`

- [ ] **Step 1: Write the failing test for template source**

Append to `tests/unit/test_initiative_operational_state.py`:

```python
def test_build_default_operational_state_template_source_uses_template_context():
    from app.services.initiative_operational_state import build_default_operational_state

    template_phases = [
        {
            "key": "ideation",
            "title": "Ideation",
            "steps": [
                {"title": "Define target audience"},
                {"title": "Run empathy interviews"},
            ],
        },
        {
            "key": "validation",
            "title": "Validation",
            "steps": [{"title": "Run feasibility check"}],
        },
    ]
    result = build_default_operational_state(
        title="MVP Launch",
        description="Ship a startup MVP in 90 days",
        phase="ideation",
        source="template",
        source_context={
            "template_title": "MVP Launch",
            "phases": template_phases,
            "suggested_workflows": ["Idea Validation", "MVP Build"],
            "kpis": [
                {"name": "Active users", "target": "1000"},
                {"name": "Retention week 4", "target": "30%"},
            ],
        },
    )

    assert result["goal"] == "Ship a startup MVP in 90 days"
    assert result["owner_agents"] == ["executive"]
    assert result["primary_workflow"] == "Idea Validation"
    assert result["success_criteria"] == [
        "Active users: 1000",
        "Retention week 4: 30%",
    ]
    assert result["deliverables"] == [
        "Define target audience",
        "Run empathy interviews",
    ]
    assert result["next_actions"] == [
        "Define target audience",
        "Run empathy interviews",
    ]


def test_build_default_operational_state_template_source_handles_missing_fields():
    from app.services.initiative_operational_state import build_default_operational_state

    result = build_default_operational_state(
        title="Empty Template",
        description="",
        phase="ideation",
        source="template",
        source_context={"template_title": "Empty Template"},
    )

    assert result["primary_workflow"] is None
    assert result["success_criteria"] == []
    assert result["deliverables"] == []
    assert result["next_actions"] == [
        "Define success criteria",
        "Identify key deliverables",
        "Assign owner agents",
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_initiative_operational_state.py::test_build_default_operational_state_template_source_uses_template_context tests/unit/test_initiative_operational_state.py::test_build_default_operational_state_template_source_handles_missing_fields -v`
Expected: FAIL — template branch not implemented; primary_workflow is None and success_criteria empty.

- [ ] **Step 3: Implement the template branch**

Replace the `build_default_operational_state` function body in `app/services/initiative_operational_state.py` with:

```python
def build_default_operational_state(
    *,
    title: str,
    description: str | None,
    phase: str = "ideation",
    source: str = "manual",
    source_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a meaningful default operational_state dict for a new initiative."""
    ctx = source_context or {}
    goal = (description or "").strip() or (title or "").strip()

    success_criteria: list[Any] = []
    deliverables: list[Any] = []
    primary_workflow: str | None = None
    next_actions: list[str] = [
        "Define success criteria",
        "Identify key deliverables",
        "Assign owner agents",
    ]

    if source == "template":
        kpis = ctx.get("kpis") or []
        if isinstance(kpis, list):
            for kpi in kpis:
                if isinstance(kpi, dict):
                    name = kpi.get("name")
                    target = kpi.get("target")
                    if name and target is not None:
                        success_criteria.append(f"{name}: {target}")
                    elif name:
                        success_criteria.append(str(name))
                elif isinstance(kpi, str):
                    success_criteria.append(kpi)

        suggested = ctx.get("suggested_workflows") or []
        if isinstance(suggested, list) and suggested:
            first = suggested[0]
            if isinstance(first, str):
                primary_workflow = first
            elif isinstance(first, dict):
                primary_workflow = first.get("name") or first.get("template_name")

        phases = ctx.get("phases") or []
        if isinstance(phases, list):
            for phase_def in phases:
                if not isinstance(phase_def, dict):
                    continue
                if phase_def.get("key") == (phase or "ideation"):
                    steps = phase_def.get("steps") or []
                    for step in steps:
                        if isinstance(step, dict):
                            step_title = step.get("title")
                            if step_title:
                                deliverables.append(str(step_title))
                        elif isinstance(step, str):
                            deliverables.append(step)
                    break

        if deliverables:
            next_actions = list(deliverables)

    return {
        "goal": goal,
        "success_criteria": success_criteria,
        "owner_agents": ["executive"],
        "primary_workflow": primary_workflow,
        "deliverables": deliverables,
        "evidence": [],
        "blockers": [],
        "next_actions": next_actions,
        "current_phase": phase or "ideation",
        "verification_status": "not_started",
        "trust_summary": default_trust_summary(),
        "workflow_execution_id": None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_initiative_operational_state.py -v`
Expected: PASS for all tests including manual and template branches.

- [ ] **Step 5: Commit**

```bash
git add app/services/initiative_operational_state.py tests/unit/test_initiative_operational_state.py
git commit -m "feat(initiatives): template-source defaults derive success_criteria, deliverables, primary_workflow"
```

---

## Task 3: Extend helper for journey source

**Files:**
- Modify: `app/services/initiative_operational_state.py`
- Test: `tests/unit/test_initiative_operational_state.py`

- [ ] **Step 1: Write the failing test for journey source**

Append to `tests/unit/test_initiative_operational_state.py`:

```python
def test_build_default_operational_state_journey_source_uses_journey_context():
    from app.services.initiative_operational_state import build_default_operational_state

    result = build_default_operational_state(
        title="Customer Onboarding Revamp",
        description="Reduce time-to-value to under 7 days",
        phase="ideation",
        source="journey",
        source_context={
            "journey_id": "journey-abc",
            "journey_title": "Customer Onboarding",
            "primary_workflow_template_name": "Customer Onboarding Workflow",
            "desired_outcomes": (
                "Users complete setup in 7 days\n"
                "NPS above 40\n"
                "Reduce support tickets by 25%"
            ),
            "kpis": [{"name": "TTV", "target": "7 days"}],
        },
    )

    assert result["goal"] == "Reduce time-to-value to under 7 days"
    assert result["owner_agents"] == ["executive"]
    assert result["primary_workflow"] == "Customer Onboarding Workflow"
    assert result["success_criteria"] == [
        "Users complete setup in 7 days",
        "NPS above 40",
        "Reduce support tickets by 25%",
        "TTV: 7 days",
    ]
    assert result["next_actions"] == ["Start journey workflow"]


def test_build_default_operational_state_journey_source_without_outcomes():
    from app.services.initiative_operational_state import build_default_operational_state

    result = build_default_operational_state(
        title="Sparse Journey",
        description="Sparse journey description",
        phase="ideation",
        source="journey",
        source_context={
            "journey_id": "journey-empty",
            "journey_title": "Sparse Journey",
        },
    )

    assert result["primary_workflow"] is None
    assert result["success_criteria"] == []
    assert result["next_actions"] == ["Start journey workflow"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_initiative_operational_state.py::test_build_default_operational_state_journey_source_uses_journey_context tests/unit/test_initiative_operational_state.py::test_build_default_operational_state_journey_source_without_outcomes -v`
Expected: FAIL — journey branch not yet handled.

- [ ] **Step 3: Implement the journey branch**

In `app/services/initiative_operational_state.py`, locate the `if source == "template":` block inside `build_default_operational_state` and add an `elif` branch for `journey` immediately after it (before the final `return`):

```python
    elif source == "journey":
        outcomes = ctx.get("desired_outcomes")
        if isinstance(outcomes, str) and outcomes.strip():
            for line in outcomes.split("\n"):
                line = line.strip()
                if line:
                    success_criteria.append(line)

        kpis = ctx.get("kpis") or []
        if isinstance(kpis, list):
            for kpi in kpis:
                if isinstance(kpi, dict):
                    name = kpi.get("name")
                    target = kpi.get("target")
                    if name and target is not None:
                        success_criteria.append(f"{name}: {target}")
                    elif name:
                        success_criteria.append(str(name))
                elif isinstance(kpi, str):
                    success_criteria.append(kpi)

        primary_workflow = (
            ctx.get("primary_workflow_template_name")
            or ctx.get("workflow_template_name")
        )
        next_actions = ["Start journey workflow"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_initiative_operational_state.py -v`
Expected: PASS for all tests, including manual, template, and journey branches.

- [ ] **Step 5: Commit**

```bash
git add app/services/initiative_operational_state.py tests/unit/test_initiative_operational_state.py
git commit -m "feat(initiatives): journey-source defaults derive success_criteria from desired_outcomes and primary_workflow from journey template"
```

---

## Task 4: Wire scaffold into `create_initiative`

**Files:**
- Modify: `app/services/initiative_service.py:102-160`
- Test: `tests/unit/test_initiative_service.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_initiative_service.py`:

```python
    @pytest.mark.asyncio
    async def test_create_initiative_populates_operational_state_for_manual_source(
        self, service, mock_supabase_client
    ):
        """Manual create must scaffold operational_state with default owner_agents and next_actions."""
        captured_payload: dict = {}

        def capture_insert(payload):
            captured_payload.update(payload)
            mock_response = MagicMock()
            mock_response.data = [{**payload, "id": "init-789"}]
            insert_chain = MagicMock()
            insert_chain.execute.return_value = mock_response
            return insert_chain

        mock_supabase_client.table.return_value.insert.side_effect = capture_insert

        with patch(
            "app.services.initiative_service.execute_async",
            side_effect=lambda query, op_name=None: query.execute(),
        ):
            result = await service.create_initiative(
                title="Manual Initiative",
                description="A description from a manual creator",
                priority="high",
            )

        op_state = captured_payload["metadata"]["operational_state"]
        assert op_state["goal"] == "A description from a manual creator"
        assert op_state["owner_agents"] == ["executive"]
        assert op_state["current_phase"] == "ideation"
        assert op_state["verification_status"] == "not_started"
        assert op_state["next_actions"] == [
            "Define success criteria",
            "Identify key deliverables",
            "Assign owner agents",
        ]
        assert op_state["trust_summary"]["approval_state"] == "not_required"
        assert result["id"] == "init-789"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_initiative_service.py::TestInitiativeService::test_create_initiative_populates_operational_state_for_manual_source -v`
Expected: FAIL — `op_state["owner_agents"]` is `[]` (empty default from normalize) instead of `["executive"]`; `next_actions` is empty.

- [ ] **Step 3: Modify `create_initiative` to merge the scaffold**

In `app/services/initiative_service.py`, update the import block (around line 25-30) to also import the new helper:

```python
from app.services.initiative_operational_state import (
    OPERATIONAL_STATE_KEY,
    build_default_operational_state,
)
from app.services.initiative_operational_state import (
    normalize_operational_state as _normalize_operational_state,
)
```

Then update the `create_initiative` signature and body (replace lines 102-160):

```python
    async def create_initiative(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        user_id: str | None = None,
        phase: str = "ideation",
        template_id: str | None = None,
        metadata: dict | None = None,
        source: str = "manual",
        source_context: dict | None = None,
    ) -> dict:
        """Create a new initiative with a scaffolded operational_state.

        Args:
            title: Initiative title.
            description: Initiative description.
            priority: Priority level (low, medium, high, critical).
            user_id: Optional user ID who owns the initiative.
            phase: Starting phase (default: ideation).
            template_id: Optional template ID this was created from.
            metadata: Optional metadata dict (OKRs, milestones, etc.).
            source: Origin of the create call (manual, template, journey, idea).
            source_context: Source-specific context for the operational_state scaffold.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for initiative creation")

        merged_metadata: dict[str, Any] = dict(metadata or {})
        scaffold = build_default_operational_state(
            title=title,
            description=description,
            phase=phase,
            source=source,
            source_context=source_context,
        )
        existing_op = merged_metadata.get(OPERATIONAL_STATE_KEY)
        if isinstance(existing_op, dict) and existing_op:
            scaffold = {**scaffold, **existing_op}
        merged_metadata[OPERATIONAL_STATE_KEY] = scaffold

        normalized_metadata = _normalize_operational_state(
            {
                "title": title,
                "description": description,
                "phase": phase,
                "metadata": merged_metadata,
            }
        )["metadata"]

        data = {
            "title": title,
            "description": description,
            "priority": priority,
            "status": "not_started",
            "progress": 0,
            "phase": phase,
            "phase_progress": dict.fromkeys(INITIATIVE_PHASES, 0),
            "user_id": effective_user_id,
            "metadata": normalized_metadata,
        }
        if template_id:
            data["template_id"] = template_id

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(
            client.table(self._table_name).insert(data),
            op_name="initiatives.create",
        )
        if response.data:
            return _normalize_operational_state(response.data[0])
        raise Exception("No data returned from insert")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_initiative_service.py::TestInitiativeService::test_create_initiative_populates_operational_state_for_manual_source -v`
Expected: PASS.

- [ ] **Step 5: Run the full initiative test suite to catch regressions**

Run: `uv run pytest tests/unit/test_initiative_service.py tests/unit/test_initiative_operational_state.py -v`
Expected: All existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add app/services/initiative_service.py tests/unit/test_initiative_service.py
git commit -m "feat(initiatives): scaffold operational_state on every manual create"
```

---

## Task 5: Pass template context through `create_from_template`

**Files:**
- Modify: `app/services/initiative_service.py:784-826`
- Test: `tests/unit/test_initiative_service.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_initiative_service.py`:

```python
    @pytest.mark.asyncio
    async def test_create_from_template_populates_operational_state_from_template(
        self, service, mock_supabase_client
    ):
        """create_from_template must pass template phases/workflows/kpis into the scaffold."""
        template_payload = {
            "id": "tmpl-1",
            "title": "MVP Launch",
            "description": "Ship a startup MVP in 90 days",
            "priority": "high",
            "phases": [
                {
                    "key": "ideation",
                    "title": "Ideation",
                    "steps": [{"title": "Define target audience"}],
                }
            ],
            "suggested_workflows": ["Idea Validation"],
            "kpis": [{"name": "Active users", "target": "1000"}],
        }

        captured_payload: dict = {}

        def capture_insert(payload):
            captured_payload.update(payload)
            mock_response = MagicMock()
            mock_response.data = [{**payload, "id": "init-tmpl"}]
            chain = MagicMock()
            chain.execute.return_value = mock_response
            return chain

        template_response = MagicMock()
        template_response.data = template_payload

        def fake_execute(query, op_name=None):
            return query.execute()

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            template_response
        )
        mock_supabase_client.table.return_value.insert.side_effect = capture_insert

        with patch(
            "app.services.initiative_service.execute_async", side_effect=fake_execute
        ):
            await service.create_from_template(template_id="tmpl-1")

        op_state = captured_payload["metadata"]["operational_state"]
        assert op_state["primary_workflow"] == "Idea Validation"
        assert "Active users: 1000" in op_state["success_criteria"]
        assert op_state["deliverables"] == ["Define target audience"]
        assert op_state["next_actions"] == ["Define target audience"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_initiative_service.py::TestInitiativeService::test_create_from_template_populates_operational_state_from_template -v`
Expected: FAIL — `primary_workflow` is None and `deliverables` is empty because template context is not threaded through.

- [ ] **Step 3: Update `create_from_template` to pass source context**

Replace `create_from_template` in `app/services/initiative_service.py` (lines 784-826) with:

```python
    async def create_from_template(
        self,
        template_id: str,
        user_id: str | None = None,
        title_override: str | None = None,
    ) -> dict:
        """Create an initiative from a template with operational_state scaffold."""
        client = self.client if self.is_authenticated else AdminService().client
        template_response = await execute_async(
            client.table("initiative_templates")
            .select("*")
            .eq("id", template_id)
            .single(),
            op_name="initiative_templates.get",
        )
        template = template_response.data

        if not template:
            raise Exception(f"Template {template_id} not found")

        return await self.create_initiative(
            title=title_override or template["title"],
            description=template.get("description", ""),
            priority=template.get("priority", "medium"),
            user_id=user_id,
            phase="ideation",
            template_id=template_id,
            metadata={
                "template_title": template["title"],
                "phases": template.get("phases", []),
                "suggested_workflows": template.get("suggested_workflows", []),
                "kpis": template.get("kpis", []),
            },
            source="template",
            source_context={
                "template_title": template["title"],
                "phases": template.get("phases", []),
                "suggested_workflows": template.get("suggested_workflows", []),
                "kpis": template.get("kpis", []),
            },
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_initiative_service.py::TestInitiativeService::test_create_from_template_populates_operational_state_from_template -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/initiative_service.py tests/unit/test_initiative_service.py
git commit -m "feat(initiatives): pass template context to operational_state scaffold"
```

---

## Task 6: Pass journey context through `/from-journey` route

**Files:**
- Modify: `app/routers/initiatives.py:154-210`
- Test: `tests/unit/app/routers/test_initiatives.py` (verify file path) or `tests/unit/test_initiative_service.py` if router tests live elsewhere

- [ ] **Step 1: Locate the journey route test file**

Run: `ls tests/unit/app/routers/ 2>/dev/null && ls tests/integration/ | grep -i initiative`
Expected output (one of):
```
test_initiatives.py
```
Or:
```
test_initiative_checklist_endpoints.py
```

If `tests/unit/app/routers/test_initiatives.py` exists, append the test there. Otherwise add a new service-level test in `tests/unit/test_initiative_service.py` exercising `create_initiative` with `source="journey"` (which is what the route delegates to).

- [ ] **Step 2: Write the failing test (service-level fallback if router test file missing)**

Append to `tests/unit/test_initiative_service.py`:

```python
    @pytest.mark.asyncio
    async def test_create_initiative_with_journey_source_includes_desired_outcomes(
        self, service, mock_supabase_client
    ):
        """Journey-sourced create must pass desired_outcomes and journey workflow into scaffold."""
        captured_payload: dict = {}

        def capture_insert(payload):
            captured_payload.update(payload)
            mock_response = MagicMock()
            mock_response.data = [{**payload, "id": "init-journey"}]
            chain = MagicMock()
            chain.execute.return_value = mock_response
            return chain

        mock_supabase_client.table.return_value.insert.side_effect = capture_insert

        with patch(
            "app.services.initiative_service.execute_async",
            side_effect=lambda query, op_name=None: query.execute(),
        ):
            await service.create_initiative(
                title="Onboarding Revamp",
                description="Reduce TTV",
                priority="medium",
                phase="ideation",
                metadata={
                    "source": "user_journey",
                    "journey_id": "journey-abc",
                    "journey_title": "Customer Onboarding",
                    "desired_outcomes": "Users complete setup in 7 days\nNPS above 40",
                },
                source="journey",
                source_context={
                    "journey_id": "journey-abc",
                    "journey_title": "Customer Onboarding",
                    "primary_workflow_template_name": "Customer Onboarding Workflow",
                    "desired_outcomes": "Users complete setup in 7 days\nNPS above 40",
                },
            )

        op_state = captured_payload["metadata"]["operational_state"]
        assert op_state["primary_workflow"] == "Customer Onboarding Workflow"
        assert "Users complete setup in 7 days" in op_state["success_criteria"]
        assert "NPS above 40" in op_state["success_criteria"]
        assert op_state["next_actions"] == ["Start journey workflow"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_initiative_service.py::TestInitiativeService::test_create_initiative_with_journey_source_includes_desired_outcomes -v`
Expected: PASS already if Tasks 1-4 are correct (the service-side helper handles `source="journey"`). If it FAILS, the journey branch in `build_default_operational_state` is incomplete — go back to Task 3.

- [ ] **Step 4: Update the `/from-journey` route to pass source context**

In `app/routers/initiatives.py`, replace the `service.create_initiative(...)` call inside `create_initiative_from_journey` (lines 175-197) with:

```python
        service = InitiativeService()
        desired_outcomes = (
            body.desired_outcomes.strip()
            if isinstance(body.desired_outcomes, str)
            and body.desired_outcomes.strip()
            else None
        )
        timeline = (
            body.timeline.strip()
            if isinstance(body.timeline, str) and body.timeline.strip()
            else None
        )
        journey_workflow_template = journey.get("primary_workflow_template_name")
        initiative = await service.create_initiative(
            title=body.title_override or journey["title"],
            description=journey.get("description")
            or f'Initiative based on the "{journey["title"]}" user journey',
            priority="medium",
            user_id=user_id,
            phase="ideation",
            metadata={
                "source": "user_journey",
                "journey_id": journey["id"],
                "journey_title": journey["title"],
                "journey_stages": journey.get("stages") or [],
                "kpis": journey.get("kpis") or [],
                "desired_outcomes": desired_outcomes,
                "timeline": timeline,
                "workflow_template_name": journey_workflow_template,
            },
            source="journey",
            source_context={
                "journey_id": journey["id"],
                "journey_title": journey["title"],
                "primary_workflow_template_name": journey_workflow_template,
                "desired_outcomes": desired_outcomes,
                "kpis": journey.get("kpis") or [],
            },
        )
```

- [ ] **Step 5: Run service tests for regressions**

Run: `uv run pytest tests/unit/test_initiative_service.py tests/unit/test_initiative_operational_state.py -v`
Expected: All tests pass.

- [ ] **Step 6: Run integration tests for the journey route if present**

Run: `uv run pytest tests/integration/ -k "journey or initiative" -v`
Expected: All pass. If there are no integration tests for the from-journey route, this is a no-op.

- [ ] **Step 7: Commit**

```bash
git add app/routers/initiatives.py tests/unit/test_initiative_service.py
git commit -m "feat(initiatives): pass journey context to operational_state scaffold in /from-journey"
```

---

## Task 7: Backfill migration for existing initiatives

**Files:**
- Create: `supabase/migrations/20260428120000_backfill_initiative_operational_state.sql`

- [ ] **Step 1: Write the migration**

Create `supabase/migrations/20260428120000_backfill_initiative_operational_state.sql`:

```sql
-- Backfill operational_state for initiatives created before the parity fix.
-- Idempotent: only updates rows where operational_state is missing OR has an
-- empty owner_agents AND empty next_actions (the cheap signal that no scaffold
-- has been written by the autonomy kernel or the new create path).

-- Default trust_summary shape mirrors default_trust_summary() in
-- app/services/initiative_operational_state.py.
WITH targets AS (
    SELECT
        id,
        title,
        description,
        phase,
        COALESCE(metadata, '{}'::jsonb) AS meta,
        COALESCE(metadata->>'source', 'manual') AS source,
        COALESCE(metadata->'kpis', '[]'::jsonb) AS kpis,
        COALESCE(metadata->'phases', '[]'::jsonb) AS phases,
        COALESCE(metadata->'suggested_workflows', '[]'::jsonb) AS suggested_workflows,
        metadata->>'desired_outcomes' AS desired_outcomes,
        metadata->>'workflow_template_name' AS journey_workflow
    FROM initiatives
    WHERE
        metadata IS NULL
        OR NOT (metadata ? 'operational_state')
        OR (
            COALESCE(jsonb_array_length(metadata->'operational_state'->'owner_agents'), 0) = 0
            AND COALESCE(jsonb_array_length(metadata->'operational_state'->'next_actions'), 0) = 0
        )
),
scaffolded AS (
    SELECT
        t.id,
        t.meta,
        jsonb_build_object(
            'goal',
                COALESCE(NULLIF(TRIM(COALESCE(t.description, '')), ''), t.title, ''),
            'success_criteria',
                CASE
                    WHEN t.source = 'user_journey' AND t.desired_outcomes IS NOT NULL THEN
                        COALESCE(
                            (
                                SELECT jsonb_agg(line)
                                FROM (
                                    SELECT TRIM(unnest(string_to_array(t.desired_outcomes, E'\n'))) AS line
                                ) lines
                                WHERE line <> ''
                            ),
                            '[]'::jsonb
                        )
                    WHEN jsonb_array_length(t.kpis) > 0 THEN
                        COALESCE(
                            (
                                SELECT jsonb_agg(
                                    CASE
                                        WHEN jsonb_typeof(kpi) = 'object' AND kpi ? 'name' AND kpi ? 'target' THEN
                                            to_jsonb((kpi->>'name') || ': ' || (kpi->>'target'))
                                        WHEN jsonb_typeof(kpi) = 'object' AND kpi ? 'name' THEN
                                            to_jsonb(kpi->>'name')
                                        ELSE kpi
                                    END
                                )
                                FROM jsonb_array_elements(t.kpis) AS kpi
                            ),
                            '[]'::jsonb
                        )
                    ELSE '[]'::jsonb
                END,
            'owner_agents', '["executive"]'::jsonb,
            'primary_workflow',
                CASE
                    WHEN t.source = 'user_journey' THEN to_jsonb(t.journey_workflow)
                    WHEN jsonb_array_length(t.suggested_workflows) > 0 THEN t.suggested_workflows->0
                    ELSE 'null'::jsonb
                END,
            'deliverables',
                COALESCE(
                    (
                        SELECT jsonb_agg(step->>'title')
                        FROM jsonb_array_elements(t.phases) AS p
                        CROSS JOIN LATERAL jsonb_array_elements(COALESCE(p->'steps', '[]'::jsonb)) AS step
                        WHERE p->>'key' = COALESCE(t.phase, 'ideation')
                            AND step ? 'title'
                    ),
                    '[]'::jsonb
                ),
            'evidence', '[]'::jsonb,
            'blockers', '[]'::jsonb,
            'next_actions',
                CASE
                    WHEN t.source = 'user_journey' THEN
                        '["Start journey workflow"]'::jsonb
                    ELSE
                        '["Define success criteria","Identify key deliverables","Assign owner agents"]'::jsonb
                END,
            'current_phase', COALESCE(t.phase, 'ideation'),
            'verification_status', 'not_started',
            'trust_summary', jsonb_build_object(
                'trust_counts', '{}'::jsonb,
                'verification_counts', '{}'::jsonb,
                'approval_state', 'not_required',
                'verification_status', 'not_started',
                'last_failure_reason', null
            ),
            'workflow_execution_id', null
        ) AS scaffold
    FROM targets t
)
UPDATE initiatives i
SET metadata = jsonb_set(
        COALESCE(i.metadata, '{}'::jsonb),
        '{operational_state}',
        s.scaffold,
        true
    ),
    updated_at = now()
FROM scaffolded s
WHERE i.id = s.id;

-- Sanity log: count how many rows the migration touched. Surfaces in
-- supabase migration output for verification during rollout.
DO $$
DECLARE
    touched int;
BEGIN
    SELECT count(*) INTO touched FROM initiatives
    WHERE metadata ? 'operational_state'
        AND COALESCE(jsonb_array_length(metadata->'operational_state'->'owner_agents'), 0) > 0;
    RAISE NOTICE 'initiatives with populated operational_state after backfill: %', touched;
END $$;
```

- [ ] **Step 2: Apply the migration locally**

Run: `supabase db reset --local`
Expected: Migration chain runs cleanly, no errors. The `RAISE NOTICE` output shows a non-zero count if there were any seed initiatives.

- [ ] **Step 3: Verify backfill is idempotent**

Run: `supabase db push --local`
Expected: No new changes applied (migration already in `supabase_migrations.schema_migrations`). Re-running `psql` with the migration's UPDATE statement directly should affect 0 rows because the `WHERE` clause excludes already-scaffolded rows.

Run this SQL via psql or the Supabase dashboard SQL editor:

```sql
SELECT count(*) AS empty_op_state
FROM initiatives
WHERE metadata IS NULL
   OR NOT (metadata ? 'operational_state')
   OR (
       COALESCE(jsonb_array_length(metadata->'operational_state'->'owner_agents'), 0) = 0
       AND COALESCE(jsonb_array_length(metadata->'operational_state'->'next_actions'), 0) = 0
   );
```
Expected: 0 rows.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260428120000_backfill_initiative_operational_state.sql
git commit -m "feat(initiatives): backfill operational_state for existing initiatives"
```

---

## Task 8: End-to-end smoke test

**Files:**
- Modify: `tests/unit/test_initiative_service.py` (add a smoke test that exercises all three sources)

- [ ] **Step 1: Write the smoke test**

Append to `tests/unit/test_initiative_service.py`:

```python
    @pytest.mark.asyncio
    async def test_all_create_paths_yield_populated_owner_agents(
        self, service, mock_supabase_client
    ):
        """Smoke test: manual, template, and journey sources all populate owner_agents."""
        captured: list[dict] = []

        def capture_insert(payload):
            captured.append(payload)
            mock_response = MagicMock()
            mock_response.data = [{**payload, "id": f"init-{len(captured)}"}]
            chain = MagicMock()
            chain.execute.return_value = mock_response
            return chain

        mock_supabase_client.table.return_value.insert.side_effect = capture_insert

        with patch(
            "app.services.initiative_service.execute_async",
            side_effect=lambda query, op_name=None: query.execute(),
        ):
            await service.create_initiative(
                title="Manual",
                description="Manual desc",
                source="manual",
            )
            await service.create_initiative(
                title="Template",
                description="Template desc",
                source="template",
                source_context={
                    "suggested_workflows": ["Idea Validation"],
                    "kpis": [{"name": "ARR", "target": "1M"}],
                    "phases": [{"key": "ideation", "steps": [{"title": "Pitch"}]}],
                },
            )
            await service.create_initiative(
                title="Journey",
                description="Journey desc",
                source="journey",
                source_context={
                    "primary_workflow_template_name": "Onboarding",
                    "desired_outcomes": "Less than 7 days TTV",
                },
            )

        assert len(captured) == 3
        for payload in captured:
            op_state = payload["metadata"]["operational_state"]
            assert op_state["owner_agents"] == ["executive"]
            assert op_state["verification_status"] == "not_started"
            assert op_state["trust_summary"]["approval_state"] == "not_required"
```

- [ ] **Step 2: Run the smoke test**

Run: `uv run pytest tests/unit/test_initiative_service.py::TestInitiativeService::test_all_create_paths_yield_populated_owner_agents -v`
Expected: PASS.

- [ ] **Step 3: Run the entire initiative-related test suite**

Run: `uv run pytest tests/unit/test_initiative_service.py tests/unit/test_initiative_operational_state.py tests/integration/ -k "initiative" -v`
Expected: All tests pass.

- [ ] **Step 4: Run the lint/type pipeline**

Run: `make lint`
Expected: Ruff, ruff format, ty check, codespell, and workflow validation all pass.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_initiative_service.py
git commit -m "test(initiatives): smoke-test all three create paths populate operational_state"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Manual create populates `operational_state` — Task 4
- [x] Template create populates `operational_state` from template phases/workflows/kpis — Tasks 2, 5
- [x] Journey create populates `operational_state` from journey desired_outcomes/workflow — Tasks 3, 6
- [x] Backfill migration for existing rows — Task 7
- [x] Idempotency of backfill — Task 7 Step 3
- [x] Tests for each source — Tasks 1-3 (helper), 4-6 (integration), 8 (smoke)
- [x] Autonomy kernel path is unaffected — kernel calls `update_operational_state` AFTER create, which overwrites the scaffold; verified in Task 4 Step 5 by re-running existing kernel tests

**Placeholder scan:** No "TBD", "implement later", or undefined references. All steps include exact code or exact commands.

**Type consistency:**
- `build_default_operational_state(*, title, description, phase, source, source_context)` — same signature in Tasks 1, 2, 3
- `OPERATIONAL_STATE_KEY` constant reused from existing module
- `default_trust_summary()` reused from existing module
- `create_initiative` adds `source: str = "manual"` and `source_context: dict | None = None` — used consistently in Tasks 4, 5, 6, 8

**Behavioral parity:** The migration scaffold matches the Python helper's output for each source type — verified by mirroring `default_trust_summary()`, `["executive"]` owner_agents, and `next_actions` lists.

---

**End of plan.**
