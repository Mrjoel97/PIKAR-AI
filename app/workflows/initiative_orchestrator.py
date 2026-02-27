# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Orchestrator for initiative phases."""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class InitiativeWorkflowOrchestrator:
    """Maps initiative phases to workflows, skills, and tools.
    
    When a user's idea enters a phase, this orchestrator:
    1. Looks up matching workflow templates for the phase
    2. Identifies relevant skills to auto-invoke
    3. Passes context (initiative_id, user facts, phase data) via session.state
    4. Returns the orchestration plan as a structured dict
    """
    
    PHASE_WORKFLOW_MAP = {
        "ideation_empathy": {
            "workflows": ["Brain Dump Processing", "Idea Validation"],
            "skills": ["comprehensive_business_strategy", "market_research"],
            "pipeline": "InitiativeIdeationPipeline",
        },
        "validation_research": {
            "workflows": ["Market Research", "Competitor Analysis"],
            "skills": ["analyze_financial_statement", "competitor_analysis"],
            "pipeline": "InitiativeValidationPipeline",
        },
        "prototype_test": {
            "workflows": ["MVP Development", "User Testing"],
            "skills": ["product_roadmap", "ux_research"],
            "pipeline": "InitiativeBuildPipeline",
        },
        "build_product": {
            "workflows": ["Product Launch Prep", "Resource Planning"],
            "skills": ["project_management", "operations_optimization"],
            "pipeline": "InitiativeTestPipeline",
        },
        "scale_business": {
            "workflows": ["Go-to-Market", "Growth Strategy"],
            "skills": ["growth_hacking", "sales_strategy"],
            "pipeline": "InitiativeLaunchPipeline",
        },
    }
    
    async def orchestrate_phase(self, initiative_id: str, phase: str, context: dict) -> Dict[str, Any]:
        """Run the appropriate workflows and skills for an initiative phase."""
        logger.info(f"Orchestrating phase {phase} for initiative {initiative_id}")
        
        plan = self.PHASE_WORKFLOW_MAP.get(phase, {})
        
        return {
            "initiative_id": initiative_id,
            "phase": phase,
            "recommended_workflows": plan.get("workflows", []),
            "recommended_skills": plan.get("skills", []),
            "pipeline_agent": plan.get("pipeline", ""),
            "context": context
        }

def orchestrate_initiative_phase(initiative_id: str, phase: str, context: dict = None) -> dict:
    """Execute phase orchestration for a specific initiative.
    
    Args:
        initiative_id: The ID of the initiative.
        phase: The phase to orchestrate (ideation_empathy, validation_research, etc.)
        context: Optional additional context.
    """
    import asyncio
    orchestrator = InitiativeWorkflowOrchestrator()
    coro = orchestrator.orchestrate_phase(initiative_id, phase, context or {})
    # For sync tool execution if necessary, though if it's async ADK handles it.
    # We will assume async execution is fine, but just return a dict instead.
    # Let's make it direct.
    plan = orchestrator.PHASE_WORKFLOW_MAP.get(phase, {})
    return {
        "initiative_id": initiative_id,
        "phase": phase,
        "recommended_workflows": plan.get("workflows", []),
        "recommended_skills": plan.get("skills", []),
        "pipeline_agent": plan.get("pipeline", ""),
        "context": context or {}
    }
