# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Adaptive Workflow Generator.

Uses LLM to generate structured standard operating procedures (workflows)
customized to the user's business context.
"""

import json
import logging
import uuid
from typing import Dict, Any

from google.adk.models import Gemini
from google.genai import types

from app.agents.tools.registry import TOOL_REGISTRY
from app.workflows.engine import get_workflow_engine

logger = logging.getLogger(__name__)

class WorkflowGenerator:
    def __init__(self):
        # Use a smart model for architectural reasoning
        self.model = Gemini(
            model="gemini-2.5-pro", # High reasoning capability
            generate_content_config=types.GenerateContentConfig(
                temperature=0.4, # Balance creativity with structure
                max_output_tokens=4000
            ),
            retry_options=types.HttpRetryOptions(
                attempts=5,
                initial_delay_seconds=2.0,
                multiplier=2.0,
                max_delay_seconds=60.0,
            )
        )
        self.engine = get_workflow_engine()

    async def generate_workflow(self, user_id: str, goal: str, context: str) -> Dict[str, Any]:
        """Generate, validate, and save a new workflow template."""
        
        # 1. Prepare Prompt
        available_tools = list(TOOL_REGISTRY.keys())
        
        prompt = f"""
        You are an expert Process Architect and Workflow Strategist.
        Your goal is to design a standard operating procedure (Workflow) for a specific business goal.
        
        ### Context
        User Goal: {goal}
        Business Context: {context}
        
        ### Constraints
        1. Output must be valid JSON matching the schema below.
        2. Break the process into logical 'Phases' (e.g., Research, Plan, Execute).
        3. Break Phases into 'Steps'.
        4. For each step, assign the most appropriate 'tool' from the AVAILABLE TOOLS list below.
           - If no specific tool fits, use 'create_task' (general task) or 'mcp_web_search'.
           - PROHIBITED: Do not invent tool names. Use ONLY the provided list.
        
        ### Available Tools
        {json.dumps(available_tools, indent=2)}
        
        ### Output Schema (JSON)
        {{
            "name": "Title of Workflow",
            "description": "Short description",
            "category": "strategy|marketing|sales|operations|content|data",
            "phases": [
                {{
                    "name": "Phase Name",
                    "steps": [
                        {{
                            "name": "Step Name",
                            "tool": "exact_tool_string_from_list",
                            "description": "Actionable instruction",
                            "required_approval": boolean
                        }}
                    ]
                }}
            ]
        }}
        
        Generate the JSON now.
        """
        
        try:
            # 2. Call LLM
            logger.info(f"Generating workflow for: {goal}")
            # ADK sync wrapper call? We can use asyncio.to_thread if needed, 
            # but standard ADK usage in async context:
            response = self.model.prompt(prompt)
            text = response.text
            
            # 3. Clean & Parse
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            data = json.loads(text.strip())
            
            # 4. Validate Tools (Self-Healing)
            valid_tools = set(available_tools)
            for phase in data.get("phases", []):
                for step in phase.get("steps", []):
                    tool = step.get("tool")
                    if tool not in valid_tools:
                        logger.warning(f"Hallucinated tool '{tool}'. Replacing with 'create_task'.")
                        step["tool"] = "create_task"
            
            # 5. Save as DRAFT template via engine lifecycle API
            existing = self.engine.client.table("workflow_templates").select("id").eq("name", data["name"]).execute()
            if existing.data:
                data["name"] = f"{data['name']} (Custom {uuid.uuid4().hex[:4]})"

            created = await self.engine.create_template(
                user_id=user_id,
                name=data["name"],
                description=data["description"],
                category=data["category"],
                phases=data["phases"],
                template_key=None,
                personas_allowed=[],
                is_generated=True,
            )
            if "error" in created:
                return {"success": False, "error": created.get("error"), "details": created.get("details")}

            template_id = created["id"]
            
            return {
                "success": True,
                "template_id": template_id,
                "name": data["name"],
                "phases_count": len(data["phases"]),
                "message": f"Workflow '{data['name']}' created as draft successfully."
            }
            
        except Exception as e:
            logger.error(f"Workflow generation failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

# Singleton
_generator = None
def get_workflow_generator():
    global _generator
    if _generator is None:
        _generator = WorkflowGenerator()
    return _generator
