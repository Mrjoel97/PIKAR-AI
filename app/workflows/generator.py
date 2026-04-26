# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Adaptive Workflow Generator.

Uses LLM to generate structured standard operating procedures (workflows)
customized to the user's business context.
"""

import json
import logging
import uuid
from typing import Any

from google.adk.models import Gemini
from google.genai import types

from app.agents.tools.registry import TOOL_REGISTRY
from app.workflows.contract_defaults import (
    enrich_template_phases_for_execution,
    list_contract_safe_tool_names,
)
from app.workflows.engine import get_workflow_engine

logger = logging.getLogger(__name__)


class WorkflowGenerator:
    def __init__(self):
        # Use a smart model for architectural reasoning
        self.model = Gemini(
            model="gemini-2.5-pro",
            generate_content_config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=4000,
            ),
            retry_options=types.HttpRetryOptions(
                attempts=5,
                initial_delay=2.0,
                exp_base=2.0,
                max_delay=60.0,
            ),
        )
        self.engine = get_workflow_engine()

    def _build_tool_catalog(self) -> list[dict[str, Any]]:
        tool_names = list_contract_safe_tool_names(tool_registry=TOOL_REGISTRY)
        catalog: list[dict[str, Any]] = []
        for tool_name in tool_names:
            tool_fn = TOOL_REGISTRY[tool_name]
            input_schema = getattr(tool_fn, "input_schema", None)
            model_fields = (
                getattr(input_schema, "model_fields", {}) if input_schema else {}
            )
            required_inputs: list[str] = []
            for field_name, field_info in model_fields.items():
                is_required = getattr(field_info, "is_required", None)
                if callable(is_required) and is_required():
                    required_inputs.append(field_name)
            catalog.append(
                {
                    "name": tool_name,
                    "required_inputs": required_inputs,
                    "all_inputs": list(model_fields.keys()),
                }
            )
        return catalog

    async def generate_workflow(
        self,
        user_id: str,
        goal: str,
        context: str,
        category: str = "custom",
        persona: str | None = None,
    ) -> dict[str, Any]:
        """Generate, validate, save, and publish a new workflow template when possible."""
        tool_catalog = self._build_tool_catalog()
        available_tools = [tool["name"] for tool in tool_catalog]

        prompt = f"""
        You are an expert Process Architect and Workflow Strategist.
        Your goal is to design a standard operating procedure (Workflow) for a specific business goal.

        ### Context
        User Goal: {goal}
        Business Context: {context}
        Requested Category: {category}
        Persona: {persona or "unspecified"}

        ### Constraints
        1. Output must be valid JSON matching the schema below.
        2. Break the process into logical 'Phases' (e.g., Research, Plan, Execute).
        3. Break phases into actionable 'Steps'.
        4. Use ONLY tools from the AVAILABLE TOOLS list.
        5. Prefer the simplest executable workflow that can run immediately for a non-technical user.
        6. Every step must include:
           - tool
           - description
           - required_approval
           - input_bindings
           - risk_level
           - required_integrations
           - verification_checks
           - expected_outputs
           - allow_parallel
        7. Prefer these safe patterns:
           - research -> mcp_web_search
           - create a follow-up/action item -> create_task
           - save an evidence summary -> create_report
           - record an analytics event -> track_event
           - create a campaign object -> create_campaign
           - create an initiative record -> create_initiative
        8. Do not invent tool names, fields, or output keys.
        9. For most non-destructive business workflows, use risk_level="medium" and required_approval=false.
        10. Use required_approval=true only for clearly risky or irreversible actions.

        ### Available Tools
        {json.dumps(tool_catalog, indent=2)}

        ### Output Schema (JSON)
        {{
          "name": "Title of Workflow",
          "description": "Short description",
          "category": "{category}",
          "phases": [
            {{
              "name": "Phase Name",
              "steps": [
                {{
                  "name": "Step Name",
                  "tool": "exact_tool_string_from_list",
                  "description": "Actionable instruction",
                  "required_approval": false,
                  "input_bindings": {{
                    "field_name": {{"value": "literal value"}}
                  }},
                  "risk_level": "medium",
                  "required_integrations": [],
                  "verification_checks": ["success"],
                  "expected_outputs": ["success"],
                  "allow_parallel": false
                }}
              ]
            }}
          ]
        }}

        Generate the JSON now.
        """

        try:
            logger.info("Generating workflow for goal=%s category=%s", goal, category)
            response = self.model.prompt(prompt)
            text = response.text

            if "```json" in text:
                text = text.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in text:
                text = text.split("```", 1)[1].split("```", 1)[0]

            data = json.loads(text.strip())
            data["category"] = category or str(data.get("category") or "custom")

            valid_tools = set(available_tools)
            for phase in data.get("phases", []):
                for step in phase.get("steps", []):
                    tool = step.get("tool")
                    if tool not in valid_tools:
                        logger.warning(
                            "Hallucinated or unsafe tool '%s'. Replacing with 'create_task'.",
                            tool,
                        )
                        step["tool"] = "create_task"

            normalized_phases = enrich_template_phases_for_execution(
                data.get("phases") or [],
                template_name=str(data.get("name") or goal or "Generated Workflow"),
                category=str(data.get("category") or category or "custom"),
                persona=persona,
                goal=goal,
                tool_registry=TOOL_REGISTRY,
            )

            existing = (
                self.engine.client.table("workflow_templates")
                .select("id")
                .eq("name", data["name"])
                .execute()
            )
            if existing.data:
                data["name"] = f"{data['name']} (Custom {uuid.uuid4().hex[:4]})"

            created = await self.engine.create_template(
                user_id=user_id,
                name=data["name"],
                description=data.get("description")
                or f"AI-generated workflow for: {goal}",
                category=data["category"],
                phases=normalized_phases,
                template_key=None,
                personas_allowed=None,
                is_generated=True,
                default_persona=persona,
            )
            if "error" in created:
                return {
                    "success": False,
                    "error": created.get("error"),
                    "details": created.get("details"),
                }

            template_id = created["id"]
            publish_result = await self.engine.publish_template(
                template_id=template_id, user_id=user_id
            )
            if "error" in publish_result:
                logger.warning(
                    "Generated workflow %s created as draft because publish failed: %s",
                    template_id,
                    publish_result.get("error"),
                )
                return {
                    "success": True,
                    "template_id": template_id,
                    "name": data["name"],
                    "phases_count": len(normalized_phases),
                    "lifecycle_status": created.get("lifecycle_status", "draft"),
                    "published": False,
                    "publish_error": publish_result.get("error"),
                    "publish_details": publish_result.get("details"),
                    "message": f"Workflow '{data['name']}' was created as a draft and needs review before it can run.",
                }

            return {
                "success": True,
                "template_id": template_id,
                "name": data["name"],
                "phases_count": len(normalized_phases),
                "lifecycle_status": publish_result.get("lifecycle_status", "published"),
                "published": True,
                "message": f"Workflow '{data['name']}' was created and published successfully.",
            }

        except Exception as e:
            logger.error("Workflow generation failed: %s", e, exc_info=True)
            return {"success": False, "error": str(e)}


_generator = None


def get_workflow_generator():
    global _generator
    if _generator is None:
        _generator = WorkflowGenerator()
    return _generator
