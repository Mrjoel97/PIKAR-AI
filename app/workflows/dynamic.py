# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Dynamic Workflow Generator - Custom BaseAgent for Runtime Workflow Creation.

This module implements the DynamicWorkflowGenerator, a custom BaseAgent that
analyzes user requests and dynamically composes workflows from available
specialized agents.

Enhanced with user-specific workflow storage and retrieval for pattern matching.

Note: Executive Agent handles final synthesis externally per Agent-Eco-System.md.
"""

import logging
from collections.abc import AsyncGenerator

from google.adk.agents import (
    BaseAgent,
    InvocationContext,
    LoopAgent,
    ParallelAgent,
    SequentialAgent,
)
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from app.agents.compliance import create_compliance_agent
from app.agents.content import create_content_agent
from app.agents.customer_support import create_customer_support_agent
from app.agents.data import create_data_agent, data_agent
from app.agents.financial import create_financial_agent
from app.agents.hr import create_hr_agent
from app.agents.marketing import create_marketing_agent
from app.agents.operations import create_operations_agent
from app.agents.sales import create_sales_agent
from app.agents.strategic import create_strategic_agent, strategic_agent
from app.services.user_agent_factory import USER_AGENT_PERSONALIZATION_STATE_KEY
from app.workflows.user_workflow_service import (
    UserWorkflowService,
    get_user_workflow_service,
)

logger = logging.getLogger(__name__)


# Agent factory registry for dynamic workflow creation
# Maps agent keys to factory functions that create fresh instances
# This avoids the ADK single-parent constraint by creating new agents per workflow
AGENT_FACTORY_REGISTRY = {
    "strategic": create_strategic_agent,
    "content": create_content_agent,
    "data": create_data_agent,
    "financial": create_financial_agent,
    "operations": create_operations_agent,
    "hr": create_hr_agent,
    "marketing": create_marketing_agent,
    "sales": create_sales_agent,
    "compliance": create_compliance_agent,
    "support": create_customer_support_agent,
}

# Legacy registry mapping (kept for backward compatibility with stored workflows)
# These are the singleton instances - DO NOT use for workflow sub_agents
AGENT_REGISTRY = {
    "strategic": strategic_agent,
    "content": strategic_agent,  # Fallback to strategic for analysis only
    "data": data_agent,
    "financial": strategic_agent,
    "operations": strategic_agent,
    "hr": strategic_agent,
    "marketing": strategic_agent,
    "sales": strategic_agent,
    "compliance": strategic_agent,
    "support": strategic_agent,
}


class DynamicWorkflowGenerator(BaseAgent):
    """Dynamically creates and executes workflows based on user requests.

    This agent analyzes the user's intent and dynamically composes a workflow
    from available specialized agents using the appropriate pattern:
    - Sequential: For step-by-step processes
    - Parallel: For concurrent data gathering
    - Loop: For iterative refinement processes

    Enhanced with user-specific workflow storage:
    - Checks for matching workflows from user's history before creating new ones
    - Saves successful workflows for future reuse
    - Tracks usage patterns for improved matching

    The workflow is created at runtime and executed immediately.
    Executive Agent handles final synthesis externally.
    """

    def __init__(self):
        super().__init__(
            name="DynamicWorkflowGenerator",
            description="Analyzes user requests and creates custom workflows dynamically",
        )
        self._workflow_service: UserWorkflowService | None = None

    @property
    def workflow_service(self) -> UserWorkflowService:
        """Lazy-load the workflow service."""
        if self._workflow_service is None:
            try:
                self._workflow_service = get_user_workflow_service()
            except ValueError as e:
                logger.warning(f"Workflow service unavailable: {e}")
                raise
        return self._workflow_service

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Analyze request and create a dynamic workflow.

        Enhanced workflow execution:
        1. Check for matching user workflow from history
        2. If match found, reuse and update usage count
        3. If no match, create new workflow
        4. Save successful new workflows for future reuse

        Args:
            ctx: The invocation context containing session state and history.

        Yields:
            Events produced during workflow execution.
        """
        # Get user_id from session state (for workflow storage)
        user_id = ctx.session.state.get("user_id")

        personalization = (
            ctx.session.state.get(USER_AGENT_PERSONALIZATION_STATE_KEY, {}) or {}
        )
        persona_scope = None
        if isinstance(personalization, dict):
            raw_persona = personalization.get("persona")
            if isinstance(raw_persona, str) and raw_persona.strip():
                persona_scope = raw_persona.strip().lower()

        # Get the user's request from session state
        user_request = ctx.session.state.get("user_request", "")

        if not user_request:
            # No request in state, check recent messages
            if ctx.session.events:
                for event in reversed(ctx.session.events):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                user_request = part.text
                                break
                    if user_request:
                        break

        # Try to find matching workflow from user's history
        matched_workflow = None
        workflow_from_storage = False

        if user_id:
            try:
                matched_workflow = await self.workflow_service.find_matching_workflow(
                    user_id=user_id,
                    request=user_request,
                    threshold=0.65,
                    persona_scope=persona_scope,
                )
                if matched_workflow:
                    workflow_from_storage = True
                    logger.info(
                        f"Found matching workflow: {matched_workflow['workflow_name']}"
                    )
            except Exception as e:
                logger.warning(f"Error finding matching workflow: {e}")

        # Build workflow from storage or create new one
        if matched_workflow:
            # Reconstruct workflow from stored configuration
            workflow = self._build_workflow_from_config(matched_workflow)
            agent_keys_needed = self._get_agents_from_config(matched_workflow)
            pattern = matched_workflow.get("workflow_pattern", "sequential")

            # Update usage count
            if user_id:
                try:
                    await self.workflow_service.update_workflow_usage(
                        user_id=user_id,
                        workflow_name=matched_workflow["workflow_name"],
                        persona_scope=persona_scope,
                    )
                except Exception as e:
                    logger.warning(f"Error updating workflow usage: {e}")
        else:
            # Analyze intent to determine agent keys needed
            agent_keys_needed = self._analyze_intent(user_request)
            pattern = self._determine_pattern(user_request, agent_keys_needed)

            # Build the dynamic workflow (creates fresh agents from factories)
            workflow = self._build_workflow(agent_keys_needed, pattern, user_request)

        # Store workflow info in state for transparency
        ctx.session.state["dynamic_workflow"] = {
            "agents": agent_keys_needed if agent_keys_needed else [],
            "pattern": pattern,
            "request": user_request,
            "from_storage": workflow_from_storage,
        }

        # Execute the workflow if we have one
        if workflow:
            async for event in workflow.run_async(ctx):
                yield event

            # Save new workflow for future reuse (only if not from storage and user_id available)
            if user_id and not workflow_from_storage and agent_keys_needed:
                await self._save_workflow(
                    user_id=user_id,
                    agent_keys=agent_keys_needed,
                    pattern=pattern,
                    request=user_request,
                    persona_scope=persona_scope,
                )
        else:
            # No suitable agents found, return informative message
            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[
                        genai_types.Part(
                            text=f"I analyzed your request but couldn't determine the right specialists. "
                            f"Available specialists: {', '.join(AGENT_FACTORY_REGISTRY.keys())}. "
                            f"Please rephrase your request or specify which area you need help with."
                        )
                    ]
                ),
                actions=EventActions(),
            )

    def _analyze_intent(self, request: str) -> list:
        """Analyze the request to determine which agent keys are needed.

        Args:
            request: The user's request text.

        Returns:
            List of agent keys (strings) needed for this request.
        """
        request_lower = request.lower()
        agent_keys = []

        # Keyword mapping to agent keys
        keyword_map = {
            "financial": [
                "financial",
                "revenue",
                "cost",
                "budget",
                "profit",
                "money",
                "pricing",
            ],
            "strategic": ["strategy", "plan", "goal", "objective", "okr", "initiative"],
            "data": ["data", "analysis", "metrics", "kpi", "dashboard", "analytics"],
            "content": ["content", "blog", "article", "write", "copy", "newsletter"],
            "marketing": [
                "marketing",
                "campaign",
                "email",
                "social",
                "brand",
                "advertising",
            ],
            "sales": ["sales", "lead", "deal", "crm", "outreach", "pipeline"],
            "hr": [
                "hr",
                "hiring",
                "recruit",
                "employee",
                "onboard",
                "training",
                "performance",
            ],
            "operations": [
                "operations",
                "process",
                "efficiency",
                "rollout",
                "workflow",
            ],
            "compliance": ["compliance", "legal", "risk", "policy", "audit", "gdpr"],
            "support": ["support", "customer", "ticket", "help desk", "service"],
        }

        for agent_key, keywords in keyword_map.items():
            for keyword in keywords:
                if keyword in request_lower:
                    if agent_key not in agent_keys:
                        agent_keys.append(agent_key)
                    break

        # Default to strategic + data if no specific agents identified
        if not agent_keys:
            agent_keys = ["strategic", "data"]

        return agent_keys

    def _determine_pattern(self, request: str, agents: list) -> str:
        """Determine the best workflow pattern for the request.

        Args:
            request: The user's request text.
            agents: List of agents identified.

        Returns:
            Pattern name: 'sequential' or 'parallel'.
        """
        request_lower = request.lower()

        # Parallel pattern indicators
        if any(
            word in request_lower
            for word in ["compare", "simultaneously", "all perspectives", "consensus"]
        ):
            return "parallel"

        # Default to sequential for most use cases
        return "sequential"

    def _build_workflow(self, agent_keys: list, pattern: str, request: str):
        """Build a workflow agent from agent keys and pattern.

        Creates fresh agent instances using factory functions to avoid
        the ADK single-parent constraint.

        Args:
            agent_keys: List of agent keys (strings) to include.
            pattern: The pattern to use ('sequential', 'parallel', 'loop').
            request: The original request for naming.

        Returns:
            A workflow agent instance, or None if no agent keys.
        """
        if not agent_keys:
            return None

        # Create fresh agent instances from factory functions
        agents = []
        for key in agent_keys:
            factory = AGENT_FACTORY_REGISTRY.get(key)
            if factory:
                # Create fresh instance with workflow-specific suffix
                agents.append(factory(name_suffix="_dynamic"))
            else:
                logger.warning(f"Unknown agent key: {key}")

        if not agents:
            return None

        workflow_name = f"DynamicWorkflow_{len(agents)}agents"

        if pattern == "parallel":
            return ParallelAgent(
                name=workflow_name,
                description=f"Dynamic parallel workflow for: {request[:50]}...",
                sub_agents=agents,
            )
        elif pattern == "loop":
            # Loop pattern for iterative refinement
            return LoopAgent(
                name=workflow_name,
                description=f"Dynamic loop workflow for: {request[:50]}...",
                sub_agents=agents,
                max_iterations=3,  # Default max iterations
            )
        else:  # sequential
            return SequentialAgent(
                name=workflow_name,
                description=f"Dynamic sequential workflow for: {request[:50]}...",
                sub_agents=agents,
            )

    def _build_workflow_from_config(self, workflow_record: dict):
        """Reconstruct a workflow from stored configuration.

        Uses factory functions to create fresh agent instances.

        Args:
            workflow_record: The workflow record from database.

        Returns:
            A workflow agent instance, or None if invalid.
        """
        config = workflow_record.get("workflow_config", {})
        pattern = workflow_record.get("workflow_pattern", "sequential")
        agent_keys = config.get("agents", [])

        # Validate that we have valid agent keys
        valid_keys = [k for k in agent_keys if k in AGENT_FACTORY_REGISTRY]

        if not valid_keys:
            return None

        request = config.get("request", "Stored workflow")
        # _build_workflow now handles factory creation
        return self._build_workflow(valid_keys, pattern, request)

    def _get_agents_from_config(self, workflow_record: dict) -> list:
        """Get agent keys from stored workflow configuration.

        Note: Returns agent keys (strings), not instances, since
        fresh instances are created by _build_workflow.

        Args:
            workflow_record: The workflow record from database.

        Returns:
            List of agent keys (strings).
        """
        config = workflow_record.get("workflow_config", {})
        agent_keys = config.get("agents", [])

        # Return only valid keys
        return [k for k in agent_keys if k in AGENT_FACTORY_REGISTRY]

    async def _save_workflow(
        self,
        user_id: str,
        agent_keys: list,
        pattern: str,
        request: str,
        persona_scope: str | None = None,
    ) -> None:
        """Save a successful workflow for future reuse.

        Args:
            user_id: The user's UUID.
            agent_keys: List of agent keys (strings) used.
            pattern: The workflow pattern.
            request: The original request.
        """
        try:
            # agent_keys are already strings, no conversion needed

            # Normalize request for pattern matching
            request_pattern = self.workflow_service.normalize_request(request)

            # Generate unique workflow name
            workflow_name = self.workflow_service.generate_workflow_name(
                agents=agent_keys, pattern=pattern
            )

            # Create workflow config
            workflow_config = {
                "agents": agent_keys,
                "pattern": pattern,
                "request": request,
                "agent_count": len(agent_keys),
            }

            # Save to database
            await self.workflow_service.save_workflow(
                user_id=user_id,
                workflow_name=workflow_name,
                workflow_pattern=pattern,
                agent_ids=agent_keys,
                request_pattern=request_pattern,
                workflow_config=workflow_config,
                persona_scope=persona_scope,
            )
            logger.info(f"Saved workflow: {workflow_name}")

        except Exception as e:
            logger.warning(f"Error saving workflow: {e}")
            # Don't fail the workflow execution if save fails


# Singleton instance
dynamic_workflow_generator = DynamicWorkflowGenerator()

__all__ = [
    "AGENT_FACTORY_REGISTRY",
    "AGENT_REGISTRY",  # Kept for backward compatibility
    "DynamicWorkflowGenerator",
    "dynamic_workflow_generator",
]
