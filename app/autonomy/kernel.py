# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared autonomy kernel for initiative-driven agent execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.autonomy.agent_kernel import get_agent_kernel
from app.services.initiative_service import InitiativeService
from app.workflows.engine import get_workflow_engine


@dataclass(frozen=True)
class PlanBlueprint:
    key: str
    title: str
    success_criteria: list[str]
    owner_agents: list[str]
    deliverables: list[str]
    next_actions: list[str]
    workflow_templates: list[str]
    plan_graph: dict[str, Any]


class PlannerCapability:
    """Hidden planner capability shared by all visible agents."""

    def build(
        self, blueprint_key: str, *, title: str, context: str = ""
    ) -> PlanBlueprint:
        normalized_title = (
            title or "Autonomous initiative"
        ).strip() or "Autonomous initiative"
        if blueprint_key == "landing_page_to_launch":
            success = [
                "Landing page draft generated",
                "Persistent page created and live URL captured",
                "Tracking hooks or analytics event plan attached",
                "Launch readiness reviewed with approvals",
            ]
            deliverables = [
                "landing-page-brief",
                "page-html-or-react-artifact",
                "live-page-url",
                "launch-evidence-pack",
            ]
            next_actions = [
                "Review generated page and launch approvals",
                "Confirm analytics event naming",
                "Approve publication and launch window",
            ]
            workflow_templates = ["Landing Page to Launch", "Product Launch Workflow"]
            plan_graph = {
                "nodes": [
                    {
                        "id": "intake",
                        "title": "Intake and positioning",
                        "depends_on": [],
                        "allow_parallel": False,
                        "owner": "strategic",
                        "risk_level": "medium",
                    },
                    {
                        "id": "build_page",
                        "title": "Generate and save landing page",
                        "depends_on": ["intake"],
                        "allow_parallel": False,
                        "owner": "content",
                        "risk_level": "publish",
                    },
                    {
                        "id": "track",
                        "title": "Attach tracking and reporting",
                        "depends_on": ["build_page"],
                        "allow_parallel": True,
                        "owner": "data",
                        "risk_level": "medium",
                    },
                    {
                        "id": "launch",
                        "title": "Launch and evidence capture",
                        "depends_on": ["build_page", "track"],
                        "allow_parallel": False,
                        "owner": "marketing",
                        "risk_level": "publish",
                    },
                ],
                "edges": [
                    ["intake", "build_page"],
                    ["build_page", "track"],
                    ["track", "launch"],
                ],
            }
            return PlanBlueprint(
                key=blueprint_key,
                title=normalized_title,
                success_criteria=success,
                owner_agents=[
                    "executive",
                    "strategic",
                    "content",
                    "marketing",
                    "data",
                    "operations",
                ],
                deliverables=deliverables,
                next_actions=next_actions,
                workflow_templates=workflow_templates,
                plan_graph=plan_graph,
            )

        success = [
            "Initiative created with success criteria",
            "Evidence-backed research or validation captured",
            "Execution path selected and primary workflow attached",
            "Clear next actions and blockers surfaced",
        ]
        deliverables = [
            "initiative-charter",
            "research-evidence-pack",
            "mvp-offer-definition",
            "launch-plan",
        ]
        next_actions = [
            "Review initiative charter and target customer assumptions",
            "Validate the MVP or offer scope",
            "Approve the first execution milestone",
        ]
        workflow_templates = ["Idea-to-Venture", "Initiative Framework"]
        plan_graph = {
            "nodes": [
                {
                    "id": "capture",
                    "title": "Capture intent and context",
                    "depends_on": [],
                    "allow_parallel": False,
                    "owner": "executive",
                    "risk_level": "medium",
                },
                {
                    "id": "research",
                    "title": "Research and validation",
                    "depends_on": ["capture"],
                    "allow_parallel": True,
                    "owner": "strategic",
                    "risk_level": "medium",
                },
                {
                    "id": "design_offer",
                    "title": "Define MVP and offer",
                    "depends_on": ["research"],
                    "allow_parallel": False,
                    "owner": "strategic",
                    "risk_level": "medium",
                },
                {
                    "id": "launch_plan",
                    "title": "Launch planning and execution path",
                    "depends_on": ["design_offer"],
                    "allow_parallel": False,
                    "owner": "operations",
                    "risk_level": "medium",
                },
            ],
            "edges": [
                ["capture", "research"],
                ["research", "design_offer"],
                ["design_offer", "launch_plan"],
            ],
        }
        return PlanBlueprint(
            key=blueprint_key,
            title=normalized_title,
            success_criteria=success,
            owner_agents=["executive", "strategic", "operations", "data"],
            deliverables=deliverables,
            next_actions=next_actions,
            workflow_templates=workflow_templates,
            plan_graph=plan_graph,
        )


class VerifierCapability:
    """Hidden verifier capability shared by all visible agents."""

    def initial_status(
        self, *, workflow_execution_id: str | None, blockers: list[Any]
    ) -> str:
        if blockers:
            return "blocked"
        if workflow_execution_id:
            return "pending"
        return "not_started"


class RecoveryCapability:
    """Hidden recovery capability for failed orchestration starts."""

    def blockers_from_errors(self, errors: list[str]) -> list[dict[str, Any]]:
        return [{"status": "open", "message": error} for error in errors if error]


class ExecutorCapability:
    """Hidden execution capability that launches real workflows when available."""

    def __init__(self, workflow_engine=None):
        self._workflow_engine = workflow_engine

    @property
    def workflow_engine(self):
        if self._workflow_engine is None:
            self._workflow_engine = get_workflow_engine()
        return self._workflow_engine

    async def launch(
        self,
        *,
        user_id: str,
        template_names: list[str],
        context: dict[str, Any],
        run_source: str = "agent_ui",
    ) -> dict[str, Any]:
        errors: list[str] = []
        kernel = get_agent_kernel(workflow_engine=self.workflow_engine)
        for template_name in template_names:
            result = await kernel.start_workflow_mission(
                user_id=user_id,
                template_name=template_name,
                context=context,
                run_source=run_source,
            )
            if "error" not in result:
                return {
                    "success": True,
                    "template_name": template_name,
                    "result": result,
                    "errors": errors,
                }
            errors.append(f"{template_name}: {result.get('error')}")
        return {"success": False, "errors": errors}


class AutonomyKernel:
    """Shared orchestration layer for serious multi-step requests."""

    def __init__(
        self, initiative_service: InitiativeService | None = None, workflow_engine=None
    ):
        self._initiatives = initiative_service
        self.planner = PlannerCapability()
        self.executor = ExecutorCapability(workflow_engine=workflow_engine)
        self.verifier = VerifierCapability()
        self.recovery = RecoveryCapability()

    @property
    def initiatives(self) -> InitiativeService:
        if self._initiatives is None:
            self._initiatives = InitiativeService()
        return self._initiatives

    async def orchestrate_idea_to_venture(
        self,
        *,
        user_id: str,
        idea: str,
        context: str = "",
        braindump_id: str | None = None,
        initiative_id: str | None = None,
    ) -> dict[str, Any]:
        blueprint = self.planner.build("idea_to_venture", title=idea, context=context)
        initiative = (
            await self.initiatives.get_initiative(initiative_id, user_id=user_id)
            if initiative_id
            else await self.initiatives.create_initiative(
                title=blueprint.title[:200],
                description=context or f"Initiative auto-created from idea: {idea}",
                priority="medium",
                user_id=user_id,
                phase="ideation",
                metadata={
                    "source": "braindump" if braindump_id else "idea",
                    "original_idea": idea,
                    "braindump_id": braindump_id,
                    "framework": "autonomy-kernel-v1",
                    "autonomy_blueprint": blueprint.key,
                },
            )
        )

        launch = await self.executor.launch(
            user_id=user_id,
            template_names=blueprint.workflow_templates,
            context={
                "initiative_id": initiative["id"],
                "idea": idea,
                "topic": idea,
                "user_id": user_id,
            },
            run_source="agent_ui",
        )
        blockers = self.recovery.blockers_from_errors(launch.get("errors") or [])
        workflow_execution_id = (
            (launch.get("result") or {}).get("execution_id")
            if launch.get("success")
            else None
        )
        trust_summary = {
            "mode": "strict_workflow_launch",
            "plan_nodes": len(blueprint.plan_graph.get("nodes") or []),
            "approval_state": "required"
            if any(
                node.get("risk_level")
                in {
                    "publish",
                    "spend",
                    "legal",
                    "contract",
                    "payroll",
                    "hr_sensitive",
                    "customer_outbound",
                }
                for node in blueprint.plan_graph.get("nodes") or []
            )
            else "not_required",
            "verification_counts": {},
            "trust_counts": {},
            "last_failure_reason": blockers[0]["message"] if blockers else None,
        }
        initiative = await self.initiatives.update_operational_state(
            initiative["id"],
            user_id=user_id,
            goal=context or idea,
            success_criteria=blueprint.success_criteria,
            owner_agents=blueprint.owner_agents,
            primary_workflow=launch.get("template_name")
            or blueprint.workflow_templates[0],
            deliverables=blueprint.deliverables,
            blockers=blockers,
            next_actions=blueprint.next_actions,
            current_phase="ideation",
            verification_status=self.verifier.initial_status(
                workflow_execution_id=workflow_execution_id,
                blockers=blockers,
            ),
            trust_summary=trust_summary,
            workflow_execution_id=workflow_execution_id,
        )
        return {
            "initiative_id": initiative["id"],
            "initiative": initiative,
            "goal": initiative.get("goal"),
            "success_criteria": initiative.get("success_criteria")
            or blueprint.success_criteria,
            "plan_graph": blueprint.plan_graph,
            "owner_agents": initiative.get("owner_agents") or blueprint.owner_agents,
            "deliverables": initiative.get("deliverables") or blueprint.deliverables,
            "evidence": initiative.get("evidence") or [],
            "blockers": initiative.get("blockers") or blockers,
            "next_actions": initiative.get("next_actions") or blueprint.next_actions,
            "trust_summary": initiative.get("trust_summary") or trust_summary,
            "verification_status": initiative.get("verification_status"),
            "workflow_execution_id": workflow_execution_id,
            "template_name": launch.get("template_name"),
        }

    async def launch_workflow_for_initiative(
        self,
        *,
        initiative_id: str,
        user_id: str,
        blueprint_key: str,
        title: str,
        context: dict[str, Any],
        template_names: list[str],
        owner_agents: list[str] | None = None,
        deliverables: list[str] | None = None,
        next_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        blueprint = self.planner.build(blueprint_key, title=title)
        launch = await self.executor.launch(
            user_id=user_id,
            template_names=template_names,
            context=context,
            run_source="agent_ui",
        )
        blockers = self.recovery.blockers_from_errors(launch.get("errors") or [])
        workflow_execution_id = (
            (launch.get("result") or {}).get("execution_id")
            if launch.get("success")
            else None
        )
        initiative = await self.initiatives.update_operational_state(
            initiative_id,
            user_id=user_id,
            owner_agents=owner_agents or blueprint.owner_agents,
            primary_workflow=launch.get("template_name")
            or (
                template_names[0] if template_names else blueprint.workflow_templates[0]
            ),
            deliverables=deliverables or blueprint.deliverables,
            blockers=blockers,
            next_actions=next_actions or blueprint.next_actions,
            verification_status=self.verifier.initial_status(
                workflow_execution_id=workflow_execution_id,
                blockers=blockers,
            ),
            workflow_execution_id=workflow_execution_id,
            trust_summary={
                "mode": "strict_workflow_launch",
                "plan_nodes": len(blueprint.plan_graph.get("nodes") or []),
                "approval_state": "required"
                if any(
                    node.get("risk_level")
                    in {
                        "publish",
                        "spend",
                        "legal",
                        "contract",
                        "payroll",
                        "hr_sensitive",
                        "customer_outbound",
                    }
                    for node in blueprint.plan_graph.get("nodes") or []
                )
                else "not_required",
                "verification_counts": {},
                "trust_counts": {},
                "last_failure_reason": blockers[0]["message"] if blockers else None,
            },
        )
        return {
            "initiative": initiative,
            "workflow_execution_id": workflow_execution_id,
            "template_name": launch.get("template_name"),
            "blockers": blockers,
            "plan_graph": blueprint.plan_graph,
            "verification_status": initiative.get("verification_status"),
            "trust_summary": initiative.get("trust_summary"),
        }
