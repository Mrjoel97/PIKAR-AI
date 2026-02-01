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

"""Skills Registry - Central registry for agent capabilities.

This module defines the Skill model and SkillsRegistry class that provides
a centralized way for agents to access domain-specific knowledge and tools.
"""

from enum import Enum
from typing import Callable, Any
from pydantic import BaseModel, Field


class AgentID(str, Enum):
    """Unique identifiers for all agents in the Pikar AI ecosystem.

    Each agent has a short ID that can be used to map skills to agents.
    Skills can be assigned to multiple agents via their agent_ids field.
    """
    # Executive Agent - Central Orchestrator
    EXEC = "EXEC"      # ExecutiveAgent - Chief of Staff

    # Specialized Domain Agents
    FIN = "FIN"        # FinancialAnalysisAgent - CFO / Financial Analyst
    CONT = "CONT"      # ContentCreationAgent - CMO / Creative Director
    STRAT = "STRAT"    # StrategicPlanningAgent - Chief Strategy Officer
    SALES = "SALES"    # SalesIntelligenceAgent - Head of Sales
    MKT = "MKT"        # MarketingAutomationAgent - Marketing Director
    OPS = "OPS"        # OperationsOptimizationAgent - COO / Operations Manager
    HR = "HR"          # HRRecruitmentAgent - Human Resources Manager
    LEGAL = "LEGAL"    # ComplianceRiskAgent - Legal Counsel
    SUPP = "SUPP"      # CustomerSupportAgent - CTO / IT Support
    DATA = "DATA"      # DataAnalysisAgent - Data Analyst

    # Reserved for future agents (extensibility)
    # PRODUCT = "PRODUCT"    # ProductManagementAgent
    # RESEARCH = "RESEARCH"  # MarketResearchAgent
    # CUSTOMER = "CUSTOMER"  # CustomerSuccessAgent


# Mapping from AgentID to agent class names for reference
AGENT_ID_TO_NAME = {
    AgentID.EXEC: "ExecutiveAgent",
    AgentID.FIN: "FinancialAnalysisAgent",
    AgentID.CONT: "ContentCreationAgent",
    AgentID.STRAT: "StrategicPlanningAgent",
    AgentID.SALES: "SalesIntelligenceAgent",
    AgentID.MKT: "MarketingAutomationAgent",
    AgentID.OPS: "OperationsOptimizationAgent",
    AgentID.HR: "HRRecruitmentAgent",
    AgentID.LEGAL: "ComplianceRiskAgent",
    AgentID.SUPP: "CustomerSupportAgent",
    AgentID.DATA: "DataAnalysisAgent",
}


class Skill(BaseModel):
    """A modular capability or knowledge unit that agents can use.

    Skills can be:
    - Knowledge-based: Provide context/instructions (e.g., SEO checklist)
    - Function-based: Provide executable logic (e.g., calculation)

    Each skill is mapped to one or more agents via the agent_ids field.
    This allows agents to query which skills they have access to.
    """
    name: str = Field(..., description="Unique identifier for the skill")
    description: str = Field(..., description="What this skill does")
    category: str = Field(..., description="Category: finance, hr, marketing, sales, compliance, content, data, support, operations")

    # Agent mapping - which agents can use this skill
    agent_ids: list[AgentID] = Field(
        default_factory=list,
        description="List of agent IDs that can use this skill. Empty list means available to all agents."
    )

    # Knowledge content (for prompt injection)
    knowledge: str | None = Field(default=None, description="Domain knowledge to inject into agent context")

    # Optional callable for function-based skills
    implementation: Callable[..., Any] | None = Field(default=None, exclude=True, description="Optional function implementation")

    class Config:
        arbitrary_types_allowed = True


class SkillsRegistry:
    """Central registry for managing and accessing skills.
    
    Usage:
        registry = SkillsRegistry()
        registry.register(my_skill)
        skill = registry.get("my_skill_name")
    """
    
    _instance: "SkillsRegistry | None" = None
    
    def __new__(cls) -> "SkillsRegistry":
        """Singleton pattern to ensure one global registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if not self._initialized:
            self._skills: dict[str, Skill] = {}
            self._initialized = True
            
            # Load custom skills during initialization
            try:
                from app.skills.loader import load_custom_skills
                load_custom_skills()
            except ImportError:
                # Handle case where loader module isn't ready yet or circular import
                pass
    
    def register(self, skill: Skill) -> None:
        """Register a skill in the registry."""
        self._skills[skill.name] = skill
    
    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name)
    
    def get_by_category(self, category: str) -> list[Skill]:
        """Get all skills in a category."""
        return [s for s in self._skills.values() if s.category == category]

    def get_by_agent_id(self, agent_id: AgentID) -> list[Skill]:
        """Get all skills assigned to a specific agent.

        Args:
            agent_id: The agent ID to filter skills by.

        Returns:
            List of skills that the agent has access to.
            Skills with empty agent_ids list are considered available to all.
        """
        return [
            s for s in self._skills.values()
            if agent_id in s.agent_ids or len(s.agent_ids) == 0
        ]

    def get_agent_skills_summary(self, agent_id: AgentID) -> dict[str, list[str]]:
        """Get a summary of skills for an agent, organized by category.

        Args:
            agent_id: The agent ID to get skills for.

        Returns:
            Dictionary mapping category -> list of skill names.
        """
        skills = self.get_by_agent_id(agent_id)
        summary: dict[str, list[str]] = {}
        for skill in skills:
            if skill.category not in summary:
                summary[skill.category] = []
            summary[skill.category].append(skill.name)
        return summary

    def list_all(self) -> list[Skill]:
        """List all registered skills."""
        return list(self._skills.values())
    
    def list_names(self) -> list[str]:
        """List all skill names."""
        return list(self._skills.keys())
    
    def use_skill(self, name: str, agent_id: AgentID | None = None, **kwargs: Any) -> dict[str, Any]:
        """Use a skill - returns knowledge or executes function.
        
        Args:
            name: The skill name to use.
            agent_id: The ID of the agent attempting to use the skill.
                     If provided, validates the agent has permission.
            **kwargs: Arguments to pass if skill has an implementation.
            
        Returns:
            Dictionary with skill output or knowledge.
            Returns error if agent lacks permission.
        """
        skill = self.get(name)
        if not skill:
            return {"success": False, "error": f"Skill '{name}' not found"}
        
        # Validate agent has permission to use this skill
        if agent_id is not None and len(skill.agent_ids) > 0:
            if agent_id not in skill.agent_ids:
                allowed_agents = [aid.value for aid in skill.agent_ids]
                return {
                    "success": False, 
                    "error": f"Agent '{agent_id.value}' does not have access to skill '{name}'. "
                             f"Allowed agents: {allowed_agents}"
                }
        
        result = {
            "success": True,
            "skill_name": name,
            "description": skill.description,
        }
        
        # If skill has implementation, execute it
        if skill.implementation:
            try:
                output = skill.implementation(**kwargs)
                result["output"] = output
            except Exception as e:
                result["success"] = False
                result["error"] = str(e)
        
        # If skill has knowledge, include it
        if skill.knowledge:
            result["knowledge"] = skill.knowledge
        
        return result


# Global registry instance
skills_registry = SkillsRegistry()


def get_skill_tool(skill_name: str) -> Callable:
    """Create a tool function for a specific skill.
    
    This allows skills to be exposed as ADK tools.
    """
    def skill_tool(**kwargs: Any) -> dict:
        """Execute the skill with provided arguments."""
        return skills_registry.use_skill(skill_name, **kwargs)
    
    skill_tool.__name__ = f"use_{skill_name}"
    skill_tool.__doc__ = f"Use the {skill_name} skill."
    
    return skill_tool
