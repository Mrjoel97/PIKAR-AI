# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tools for the Strategic Planning Agent."""


async def create_initiative(
    title: str, description: str, priority: str = "medium"
) -> dict:
    """Create a new strategic initiative.

    Args:
        title: Title of the initiative.
        description: Description of the initiative goals.
        priority: Priority level (low, medium, high, critical).

    Returns:
        Dictionary containing the created initiative.
    """
    from app.services.initiative_service import InitiativeService

    try:
        from app.services.request_context import get_current_user_id

        service = InitiativeService()
        initiative = await service.create_initiative(
            title, description, priority, user_id=get_current_user_id()
        )
        return {"success": True, "initiative": initiative}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_initiative(initiative_id: str) -> dict:
    """Retrieve an initiative by ID.

    Args:
        initiative_id: The unique identifier of the initiative.

    Returns:
        Dictionary containing the initiative details.
    """
    from app.services.initiative_service import InitiativeService

    try:
        from app.services.request_context import get_current_user_id

        service = InitiativeService()
        initiative = await service.get_initiative(
            initiative_id, user_id=get_current_user_id()
        )
        return {"success": True, "initiative": initiative}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_initiative(
    initiative_id: str,
    status: str = None,
    progress: int = None,
    phase: str = None,
    title: str = None,
    description: str = None,
    desired_outcomes: str = None,
    timeline: str = None,
    metadata: dict = None,
) -> dict:
    """Update initiative status, progress, phase, details, or metadata (e.g. desired outcomes).

    Use desired_outcomes and timeline when the user has provided what success looks like
    for a journey-sourced initiative; these are stored in initiative metadata for
    start_journey_workflow and automode.

    Args:
        initiative_id: The unique identifier of the initiative.
        status: The new status (not_started, in_progress, completed, blocked, on_hold).
        progress: Optional progress percentage (0-100).
        phase: Optional phase (ideation, validation, prototype, build, scale).
        title: Optional new title.
        description: Optional new description.
        desired_outcomes: Optional; what success looks like (stored in metadata, used by journey workflow).
        timeline: Optional; target timeline or milestones (stored in metadata).
        metadata: Optional; extra key-value pairs to merge into initiative metadata.

    Returns:
        Dictionary confirming the update.
    """
    from app.services.initiative_service import InitiativeService

    try:
        from app.services.request_context import get_current_user_id

        service = InitiativeService()
        meta_update = dict(metadata or {})
        if desired_outcomes is not None:
            meta_update["desired_outcomes"] = desired_outcomes
        if timeline is not None:
            meta_update["timeline"] = timeline
        initiative = await service.update_initiative(
            initiative_id,
            status=status,
            progress=progress,
            phase=phase,
            title=title,
            description=description,
            metadata=meta_update if meta_update else None,
            user_id=get_current_user_id(),
        )
        return {"success": True, "initiative": initiative}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_initiatives(status: str = None, phase: str = None) -> dict:
    """List all initiatives, optionally filtered by status or phase.

    Args:
        status: Optional status filter (not_started, in_progress, completed, blocked, on_hold).
        phase: Optional phase filter (ideation, validation, prototype, build, scale).

    Returns:
        Dictionary containing list of initiatives.
    """
    from app.agents.tools.tool_cache import get_cached, set_cached
    from app.services.initiative_service import InitiativeService

    try:
        from app.services.request_context import get_current_user_id

        user_id = get_current_user_id()

        # Check cache first
        cache_key = f"list_initiatives:{user_id}:{status}:{phase}"
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

        service = InitiativeService()
        initiatives = await service.list_initiatives(
            status=status, phase=phase, user_id=user_id
        )
        result = {
            "success": True,
            "initiatives": initiatives,
            "count": len(initiatives),
        }
        set_cached(cache_key, result)
        return result
    except Exception as e:
        return {"success": False, "error": str(e), "initiatives": []}


async def start_initiative_from_idea(
    idea: str = None, context: str = "", braindump_id: str = None
) -> dict:
    """Create or attach an initiative from an idea and invoke the autonomy kernel."""
    from app.agents.tools.brain_dump import get_braindump_document
    from app.autonomy.kernel import AutonomyKernel
    from app.services.request_context import get_current_user_id

    try:
        user_id = get_current_user_id()
        if braindump_id:
            braindump = await get_braindump_document(braindump_id)
            if braindump.get("error"):
                return {"success": False, "error": braindump.get("error")}
            idea = idea or f"Initiative from braindump {braindump_id}"
            context = context or braindump.get("content", "")

        if not isinstance(idea, str) or not idea.strip():
            return {
                "success": False,
                "error": "An idea is required to start an initiative.",
            }

        kernel = AutonomyKernel()
        orchestration = await kernel.orchestrate_idea_to_venture(
            user_id=user_id,
            idea=idea.strip(),
            context=context or "",
            braindump_id=braindump_id,
        )

        blockers = orchestration.get("blockers") or []
        workflow_execution_id = orchestration.get("workflow_execution_id")
        template_name = orchestration.get("template_name")
        message = (
            f"Initiative '{idea[:100]}' created and routed into the autonomy kernel."
        )
        if workflow_execution_id and template_name:
            message += f" Primary workflow '{template_name}' has been queued."
        elif blockers:
            message += (
                " Workflow launch is blocked until the listed issues are resolved."
            )

        return {
            "success": True,
            "initiative": orchestration.get("initiative"),
            "initiative_id": orchestration.get("initiative_id"),
            "workflow_execution_id": workflow_execution_id,
            "template_name": template_name,
            "message": message,
            "goal": orchestration.get("goal"),
            "success_criteria": orchestration.get("success_criteria") or [],
            "plan_graph": orchestration.get("plan_graph") or {},
            "owner_agents": orchestration.get("owner_agents") or [],
            "deliverables": orchestration.get("deliverables") or [],
            "evidence": orchestration.get("evidence") or [],
            "blockers": blockers,
            "next_steps": orchestration.get("next_actions") or [],
            "trust_summary": orchestration.get("trust_summary") or {},
            "verification_status": orchestration.get("verification_status"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def advance_initiative_phase(initiative_id: str) -> dict:
    """Advance an initiative to the next phase in the framework.

    Moves the initiative from current phase to the next:
    ideation → validation → prototype → build → scale → completed

    Returns the updated initiative plus phase-specific guidance including
    recommended skills, tools, and deliverables for the new phase.

    Args:
        initiative_id: The unique identifier of the initiative.

    Returns:
        Dictionary containing the updated initiative with new phase and guidance.
    """
    from app.services.initiative_service import InitiativeService

    try:
        from app.services.request_context import get_current_user_id

        user_id = get_current_user_id()
        service = InitiativeService()

        # Capture previous phase before advancing
        old_initiative = await service.get_initiative(initiative_id, user_id=user_id)
        old_phase = (
            old_initiative.get("phase", "ideation") if old_initiative else "ideation"
        )

        initiative = await service.advance_phase(initiative_id, user_id=user_id)

        new_phase = initiative.get("phase", "completed")
        result = {
            "success": True,
            "initiative": initiative,
            "message": f"Initiative advanced to phase: {new_phase}",
        }

        # Inject phase-aware guidance from the framework skill
        phase_guidance = _get_phase_guidance(new_phase)
        if phase_guidance:
            result["phase_guidance"] = phase_guidance

        # Get orchestration plan
        from app.workflows.initiative_orchestrator import orchestrate_initiative_phase

        try:
            plan = orchestrate_initiative_phase(
                initiative_id, new_phase, {"user_id": user_id}
            )
            result["orchestration_plan"] = plan
        except Exception:
            pass

        # D3: Record phase transition history (fire-and-forget)
        import asyncio

        async def _record_phase_transition():
            try:
                from datetime import datetime

                from app.services.supabase import get_service_client

                client = get_service_client()
                client.table("initiative_phase_history").insert(
                    {
                        "initiative_id": initiative_id,
                        "user_id": user_id,
                        "from_phase": old_phase,
                        "to_phase": new_phase,
                        "transitioned_at": datetime.now().isoformat(),
                    }
                ).execute()
            except Exception:
                pass  # Non-fatal

        try:
            asyncio.create_task(_record_phase_transition())
        except RuntimeError:
            pass

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


# Phase guidance map extracted from initiative_framework_guide for fast lookup
_PHASE_GUIDANCE_MAP = {
    "ideation": {
        "goal": "Understand the problem space and validate the idea is worth pursuing.",
        "skills": ["comprehensive_business_strategy", "competitive_analysis"],
        "tools": ["mcp_web_search", "create_initiative_dashboard_widget"],
        "deliverables": [
            "Problem statement defined",
            "Target audience persona",
            "Initial competitive landscape",
            "Empathy map completed",
        ],
    },
    "validation": {
        "goal": "Market validation, feasibility analysis, and evidence gathering.",
        "skills": ["competitive_analysis", "seo_checklist", "trend_analysis"],
        "tools": ["mcp_web_search", "create_table_widget"],
        "deliverables": [
            "Market size estimate (TAM/SAM/SOM)",
            "Competitor comparison matrix",
            "Customer interview insights (3-5 interviews)",
            "Go/No-Go decision",
        ],
    },
    "prototype": {
        "goal": "Build MVP, test with real users, iterate.",
        "skills": ["blog_writing", "social_content"],
        "tools": ["mcp_generate_landing_page", "create_kanban_board_widget"],
        "deliverables": [
            "MVP feature list",
            "Landing page / test page",
            "User testing results (5-10 users)",
            "Iteration notes",
        ],
    },
    "build": {
        "goal": "Full implementation, resource allocation, execution.",
        "skills": ["process_bottleneck_analysis", "sop_generation"],
        "tools": ["create_workflow_builder_widget", "create_kanban_board_widget"],
        "deliverables": [
            "Product/service built",
            "SOPs documented",
            "Team trained",
            "Launch checklist",
        ],
    },
    "scale": {
        "goal": "Growth strategy, marketing, optimization.",
        "skills": [
            "campaign_ideation",
            "seo_checklist",
            "social_content",
            "lead_qualification_framework",
        ],
        "tools": ["create_campaign", "create_revenue_chart_widget"],
        "deliverables": [
            "Marketing strategy",
            "Sales pipeline configured",
            "Growth metrics dashboard",
            "First month targets set",
        ],
    },
}


def _get_phase_guidance(phase: str) -> dict | None:
    """Get phase-specific guidance from the built-in map."""
    return _PHASE_GUIDANCE_MAP.get(phase)


async def list_initiative_templates(persona: str = None) -> dict:
    """List available initiative templates, optionally filtered by persona.

    Args:
        persona: Optional persona filter (solopreneur, startup, sme, enterprise).

    Returns:
        Dictionary containing list of initiative templates.
    """
    from app.services.initiative_service import InitiativeService

    try:
        service = InitiativeService()
        templates = await service.list_templates(persona=persona)
        return {"success": True, "templates": templates, "count": len(templates)}
    except Exception as e:
        return {"success": False, "error": str(e), "templates": []}


async def create_initiative_from_template(template_id: str, title: str = None) -> dict:
    """Create an initiative from a predefined template.

    Args:
        template_id: The ID of the template to use.
        title: Optional custom title (overrides template title).

    Returns:
        Dictionary containing the created initiative.
    """
    from app.services.initiative_service import InitiativeService

    try:
        from app.services.request_context import get_current_user_id

        service = InitiativeService()
        initiative = await service.create_from_template(
            template_id=template_id,
            user_id=get_current_user_id(),
            title_override=title,
        )
        return {"success": True, "initiative": initiative}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def start_journey_workflow(initiative_id: str) -> dict:
    """Start the workflow linked to a user-journey initiative.

    Use this when the user has created an initiative from a User Journey and has provided
    desired outcomes (or they are already in initiative metadata). Loads the journey's
    primary workflow template and starts it with initiative_id and desired_outcomes in context.

    Args:
        initiative_id: The ID of the initiative (created from a user journey).

    Returns:
        Dictionary with success, workflow_execution_id, message, and optional error.
    """
    from app.services.initiative_service import InitiativeService
    from app.services.request_context import get_current_user_id
    from app.services.supabase import get_service_client
    from app.workflows.engine import get_workflow_engine

    user_id = get_current_user_id()
    if not user_id:
        return {
            "success": False,
            "error": "User context missing. Cannot start journey workflow.",
        }

    try:
        service = InitiativeService()
        initiative = await service.get_initiative(initiative_id, user_id=user_id)
        if not initiative:
            return {
                "success": False,
                "error": f"Initiative '{initiative_id}' not found.",
            }

        metadata = initiative.get("metadata") or {}
        journey_id = metadata.get("journey_id")
        if not journey_id:
            return {
                "success": False,
                "error": "This initiative was not created from a User Journey. Use start_workflow with a template name instead.",
            }

        desired_outcomes = metadata.get("desired_outcomes")
        timeline = metadata.get("timeline")
        defaulted_inputs = []
        if not isinstance(desired_outcomes, str) or not desired_outcomes.strip():
            desired_outcomes = "Not specified"
            defaulted_inputs.append("desired_outcomes")
        if not isinstance(timeline, str) or not timeline.strip():
            timeline = "Not specified"
            defaulted_inputs.append("timeline")

        client = get_service_client()
        journey_res = (
            client.table("user_journeys")
            .select("primary_workflow_template_name, title, suggested_workflows")
            .eq("id", journey_id)
            .execute()
        )
        if not journey_res.data:
            return {"success": False, "error": f"Journey '{journey_id}' not found."}
        journey = journey_res.data[0]
        template_name = (
            journey.get("primary_workflow_template_name") or "Initiative Framework"
        )

        context = {
            "initiative_id": initiative_id,
            "desired_outcomes": desired_outcomes,
            "timeline": timeline,
            "topic": initiative.get("title") or journey.get("title") or "",
        }

        from app.autonomy.kernel import AutonomyKernel

        kernel = AutonomyKernel(
            initiative_service=service, workflow_engine=get_workflow_engine()
        )
        launch = await kernel.launch_workflow_for_initiative(
            initiative_id=initiative_id,
            user_id=user_id,
            blueprint_key="landing_page_to_launch"
            if "landing" in template_name.lower()
            else "idea_to_venture",
            title=initiative.get("title") or journey.get("title") or template_name,
            context={**context, "user_id": user_id},
            template_names=[template_name, "Initiative Framework"],
            owner_agents=["executive", "strategic", "operations"],
            deliverables=["journey-linked-workflow", "execution-evidence"],
            next_actions=[
                "Review current workflow progress",
                "Resolve any launch blockers",
                "Approve the next gated step if required",
            ],
        )

        blockers = launch.get("blockers") or []
        execution_id = launch.get("workflow_execution_id")
        if blockers and not execution_id:
            first_blocker = (
                blockers[0].get("message")
                if isinstance(blockers[0], dict)
                else str(blockers[0])
            )
            return {
                "success": False,
                "error": first_blocker or "Journey workflow launch failed.",
                "error_code": "workflow_contract_invalid",
                "blockers": blockers,
                "trust_summary": launch.get("trust_summary") or {},
            }

        if execution_id:
            await service.update_initiative(
                initiative_id,
                workflow_execution_id=execution_id,
                status="in_progress",
                metadata={
                    "journey_id": journey_id,
                    "journey_title": journey.get("title"),
                    "workflow_template_name": launch.get("template_name")
                    or template_name,
                },
                user_id=user_id,
            )

        return {
            "success": True,
            "workflow_execution_id": execution_id,
            "template_name": launch.get("template_name") or template_name,
            "message": "Journey workflow started through the autonomy kernel."
            if execution_id
            else "Journey workflow plan attached to initiative.",
            "requirements_satisfied": True,
            "missing_inputs": [],
            "defaulted_inputs": defaulted_inputs,
            "blockers": blockers,
            "trust_summary": launch.get("trust_summary") or {},
            "verification_status": launch.get("verification_status"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def suggest_workflows() -> dict:
    """Suggest relevant workflows based on the user's recent activity patterns.

    Analyzes the user's recent actions and finds workflows that match
    their behavior patterns using semantic similarity.

    Returns:
        Dictionary with suggested workflow templates ranked by relevance.
    """
    try:
        from app.services.request_context import get_current_user_id
        from app.services.semantic_workflow_matcher import match_workflows_for_user

        user_id = get_current_user_id()
        suggestions = await match_workflows_for_user(user_id)

        return {
            "success": True,
            "count": len(suggestions),
            "suggestions": suggestions,
            "tip": "Use 'start_journey_workflow' to launch a suggested workflow.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def journey_metrics() -> dict:
    """Get journey quality metrics for the current user.

    Returns statistics on initiative phase transitions including
    average time-in-phase, completion rates, and phases reached.

    Returns:
        Dictionary with journey analytics and quality metrics.
    """
    try:
        from app.services.request_context import get_current_user_id
        from app.services.semantic_workflow_matcher import get_journey_quality_metrics

        user_id = get_current_user_id()
        metrics = await get_journey_quality_metrics(user_id)

        return {"success": True, **metrics}
    except Exception as e:
        return {"success": False, "error": str(e)}
