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

"""Agent-Aware Skills Tools - Provides skill access with agent-specific permissions.

This module provides tools for agents to access the Skills Registry with proper
access control based on the agent's ID. Each agent gets a set of skill tools
that are configured with their agent ID for permission checking.

Key features:
1. Agent-aware skill access (enforces which skills each agent can use)
2. Full skill discovery (list, search)
3. Custom skill creation for user-specific needs
4. User skill management
"""

from typing import Optional, List, Dict, Any, Callable
import logging

from app.agents.tools.base import agent_tool
from app.skills.registry import skills_registry, AgentID
from app.services.request_context import get_current_user_id

logger = logging.getLogger(__name__)


# =============================================================================
# Agent-Aware Skill Tool Factories
# =============================================================================

def _create_list_skills(agent_id: AgentID) -> Callable:
    """Create a list_skills tool configured for a specific agent."""
    
    @agent_tool
    def list_skills(category: Optional[str] = None) -> Dict[str, Any]:
        """List all skills available to this agent, optionally filtered by category.
        
        Use this tool to discover what skills are available to help with tasks.
        Skills provide domain-specific knowledge, frameworks, and expert guidance.
        
        Args:
            category: Optional category filter. Options: finance, hr, marketing, 
                      sales, compliance, content, data, support, operations, planning.
                      
        Returns:
            Dictionary with count and list of available skills with their descriptions.
        """
        try:
            # Get skills available to this specific agent
            if category:
                all_category_skills = skills_registry.get_by_category(category)
                # Filter to only skills this agent can access
                skills = [
                    s for s in all_category_skills 
                    if agent_id in s.agent_ids or len(s.agent_ids) == 0
                ]
            else:
                skills = skills_registry.get_by_agent_id(agent_id)
            
            return {
                "success": True,
                "agent_id": agent_id.value,
                "count": len(skills),
                "skills": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "category": s.category,
                    }
                    for s in skills[:50]  # Limit to first 50
                ],
                "tip": "Use 'use_skill' with a skill name to access its knowledge and guidance."
            }
        except Exception as e:
            logger.error(f"Error listing skills for {agent_id.value}: {e}")
            return {"success": False, "error": str(e)}
    
    list_skills.__name__ = "list_skills"
    list_skills.__doc__ = f"""List all skills available to the {agent_id.value} agent.
    
Use this tool to discover what skills are available to help with tasks.
Skills provide domain-specific knowledge, frameworks, and expert guidance.

Args:
    category: Optional category filter. Options: finance, hr, marketing, 
              sales, compliance, content, data, support, operations, planning.
              
Returns:
    Dictionary with count and list of available skills with their descriptions.
"""
    return list_skills


def _create_use_skill(agent_id: AgentID) -> Callable:
    """Create a use_skill tool configured for a specific agent."""
    
    @agent_tool
    def use_skill(skill_name: str) -> Dict[str, Any]:
        """Use a skill to get domain-specific knowledge and guidance.
        
        Skills contain expert knowledge on specific topics. Use this tool to
        access frameworks, checklists, best practices, and domain expertise.
        
        Args:
            skill_name: Name of the skill to use (get from list_skills or search_skills).
            
        Returns:
            Dictionary with skill knowledge and guidance, or error if access denied.
        """
        try:
            # Pass agent_id for access control
            result = skills_registry.use_skill(skill_name, agent_id=agent_id)
            
            if not result.get("success"):
                return result
            
            response = {
                "success": True,
                "skill_name": skill_name,
                "description": result.get("description", ""),
            }
            
            if result.get("knowledge"):
                response["knowledge"] = result["knowledge"]
                
            if result.get("output"):
                # Gap 1: Validate structured output for critical skills
                from app.skills.skill_validation import validate_skill_output
                validation = validate_skill_output(skill_name, result["output"])
                response["output"] = validation.get("validated", result["output"])
                if not validation.get("valid"):
                    response["validation_warnings"] = validation.get("errors", [])
                
            return response
            
        except Exception as e:
            logger.error(f"Error using skill '{skill_name}' for {agent_id.value}: {e}")
            return {"success": False, "error": str(e)}
    
    use_skill.__name__ = "use_skill"
    use_skill.__doc__ = f"""Use a skill to get domain-specific knowledge (as {agent_id.value} agent).
    
Skills contain expert knowledge on specific topics. Use this tool to access 
frameworks, checklists, best practices, and domain expertise.

Args:
    skill_name: Name of the skill to use (get from list_skills or search_skills).
    
Returns:
    Dictionary with skill knowledge and guidance, or error if access denied.
"""
    return use_skill


def _create_search_skills(agent_id: AgentID) -> Callable:
    """Create a search_skills tool configured for a specific agent."""
    
    @agent_tool
    def search_skills(query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for skills matching a query or topic.
        
        Use this to find relevant skills when you're not sure which skill to use.
        Results are ranked by relevance and filtered to skills this agent can access.
        Uses semantic search (embeddings) with keyword fallback.
        
        Args:
            query: Search terms or topic (e.g., "financial analysis", "SEO", "hiring").
            limit: Maximum number of results to return (default: 10).
            
        Returns:
            Dictionary with matching skills and their descriptions.
        """
        try:
            # ── Try semantic search first ──
            semantic_results = skills_registry.semantic_search(
                query, agent_id=agent_id, limit=limit
            )
            if semantic_results:
                return {
                    "success": True,
                    "agent_id": agent_id.value,
                    "query": query,
                    "search_type": "semantic",
                    "count": len(semantic_results),
                    "results": [
                        {
                            "name": r["skill"].name,
                            "description": r["skill"].description,
                            "category": r["skill"].category,
                            "relevance": round(r["score"], 2),
                        }
                        for r in semantic_results
                    ],
                    "tip": "Use 'use_skill' with a skill name to access its full knowledge.",
                }

            # ── Fall back to keyword matching ──
            available_skills = skills_registry.get_by_agent_id(agent_id)
            query_lower = query.lower()
            keywords = set(query_lower.split())
            
            scored_skills = []
            for skill in available_skills:
                score = 0.0
                
                # Check name match
                if query_lower in skill.name.lower():
                    score += 0.5
                    
                # Check description match
                desc_lower = skill.description.lower()
                for kw in keywords:
                    if kw in desc_lower:
                        score += 0.2
                    if kw in skill.name.lower():
                        score += 0.3
                        
                # Check category match
                if query_lower in skill.category.lower():
                    score += 0.3
                        
                # Check knowledge match (if available)
                if skill.knowledge:
                    knowledge_lower = skill.knowledge.lower()[:500]
                    for kw in keywords:
                        if kw in knowledge_lower:
                            score += 0.1
                            
                if score > 0:
                    scored_skills.append((score, skill))
            
            # Sort by score and take top results
            scored_skills.sort(key=lambda x: x[0], reverse=True)
            top_skills = scored_skills[:limit]
            
            return {
                "success": True,
                "agent_id": agent_id.value,
                "query": query,
                "search_type": "keyword",
                "count": len(top_skills),
                "results": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "category": s.category,
                        "relevance": round(score, 2)
                    }
                    for score, s in top_skills
                ],
                "tip": "Use 'use_skill' with a skill name to access its full knowledge."
            }
            
        except Exception as e:
            logger.error(f"Error searching skills for {agent_id.value}: {e}")
            return {"success": False, "error": str(e)}
    
    search_skills.__name__ = "search_skills"
    search_skills.__doc__ = f"""Search for skills matching a query (as {agent_id.value} agent).
    
Use this to find relevant skills when you're not sure which skill to use.
Results are ranked by relevance and filtered to skills this agent can access.

Args:
    query: Search terms or topic (e.g., "financial analysis", "SEO", "hiring").
    limit: Maximum number of results to return (default: 10).
    
Returns:
    Dictionary with matching skills and their descriptions.
"""
    return search_skills


def _create_create_custom_skill(agent_id: AgentID) -> Callable:
    """Create a create_custom_skill tool configured for a specific agent."""
    
    @agent_tool
    def create_custom_skill(
        skill_name: str,
        description: str,
        category: str,
        knowledge: str,
        target_agents: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new custom skill tailored to the user's business context.
        
        Use this when the user needs a specialized skill that doesn't exist.
        Custom skills persist and can be used in future conversations.
        
        Args:
            skill_name: Unique name for the skill (e.g., "quarterly_report_analysis").
            description: Clear description of what the skill does.
            category: Category for the skill. Options: finance, hr, marketing, 
                      sales, compliance, content, data, support, operations, planning.
            knowledge: The domain knowledge, frameworks, or instructions for the skill.
                       This is the expertise that will be provided when the skill is used.
            target_agents: Comma-separated list of agent IDs that can use this skill.
                           Options: EXEC, FIN, CONT, STRAT, SALES, MKT, OPS, HR, LEGAL, SUPP, DATA.
                           Leave empty to make available to the creating agent only.
                           
        Returns:
            Dictionary with created skill details or error message.
        """
        try:
            user_id = get_current_user_id()
            if not user_id:
                return {
                    "success": False, 
                    "error": "User context not available. Cannot create user-specific skill."
                }
            
            # Parse target agents, default to creating agent if not specified
            agent_ids = []
            if target_agents:
                agent_ids = [a.strip().upper() for a in target_agents.split(",")]
                
                # Validate agent IDs
                valid_ids = {aid.value for aid in AgentID}
                for aid in agent_ids:
                    if aid not in valid_ids:
                        return {
                            "success": False,
                            "error": f"Invalid agent ID: {aid}. Valid options: {', '.join(valid_ids)}"
                        }
            else:
                # Default to creating agent
                agent_ids = [agent_id.value]
            
            # Validate category
            valid_categories = [
                "finance", "hr", "marketing", "sales", "compliance",
                "content", "data", "support", "operations", "planning"
            ]
            if category.lower() not in valid_categories:
                return {
                    "success": False,
                    "error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"
                }
            
            # Create the skill using the custom skills service
            from app.skills.custom_skills_service import get_custom_skills_service
            import asyncio
            
            service = get_custom_skills_service()
            
            # Run async function
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            service.create_custom_skill(
                                user_id=user_id,
                                name=skill_name,
                                description=description,
                                category=category.lower(),
                                agent_ids=agent_ids,
                                knowledge=knowledge,
                                metadata={"created_by": f"agent:{agent_id.value}"}
                            )
                        )
                        record = future.result()
                else:
                    record = asyncio.run(
                        service.create_custom_skill(
                            user_id=user_id,
                            name=skill_name,
                            description=description,
                            category=category.lower(),
                            agent_ids=agent_ids,
                            knowledge=knowledge,
                            metadata={"created_by": f"agent:{agent_id.value}"}
                        )
                    )
            except RuntimeError:
                record = asyncio.run(
                    service.create_custom_skill(
                        user_id=user_id,
                        name=skill_name,
                        description=description,
                        category=category.lower(),
                        agent_ids=agent_ids,
                        knowledge=knowledge,
                        metadata={"created_by": f"agent:{agent_id.value}"}
                    )
                )
            
            return {
                "success": True,
                "message": f"Custom skill '{skill_name}' created successfully!",
                "skill_id": record.get("id"),
                "skill_name": record.get("name"),
                "category": record.get("category"),
                "available_to": agent_ids,
                "note": "This skill is now available for use in future conversations."
            }
            
        except Exception as e:
            logger.error(f"Error creating custom skill: {e}")
            return {"success": False, "error": str(e)}
    
    create_custom_skill.__name__ = "create_custom_skill"
    create_custom_skill.__doc__ = f"""Create a new custom skill (as {agent_id.value} agent).
    
Use this when the user needs a specialized skill that doesn't exist.
Custom skills persist and can be used in future conversations.

Args:
    skill_name: Unique name for the skill (e.g., "quarterly_report_analysis").
    description: Clear description of what the skill does.
    category: Category for the skill. Options: finance, hr, marketing, 
              sales, compliance, content, data, support, operations, planning.
    knowledge: The domain knowledge, frameworks, or instructions for the skill.
    target_agents: Comma-separated list of agent IDs that can use this skill.
                   Leave empty to make available to the creating agent only.
                   
Returns:
    Dictionary with created skill details or error message.
"""
    return create_custom_skill


def _create_list_user_skills(agent_id: AgentID) -> Callable:
    """Create a list_user_skills tool."""
    
    @agent_tool
    def list_user_skills() -> Dict[str, Any]:
        """List custom skills created for the current user.
        
        Returns:
            Dictionary with user's custom skills.
        """
        try:
            user_id = get_current_user_id()
            if not user_id:
                return {
                    "success": False, 
                    "error": "User context not available."
                }
            
            from app.skills.custom_skills_service import get_custom_skills_service
            import asyncio
            
            service = get_custom_skills_service()
            
            # Run async function
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            service.list_custom_skills(user_id=user_id, is_active=True)
                        )
                        skills = future.result()
                else:
                    skills = asyncio.run(
                        service.list_custom_skills(user_id=user_id, is_active=True)
                    )
            except RuntimeError:
                skills = asyncio.run(
                    service.list_custom_skills(user_id=user_id, is_active=True)
                )
            
            # Filter to skills this agent can access
            accessible_skills = []
            for s in skills:
                skill_agents = s.get("agent_ids", [])
                if not skill_agents or agent_id.value in skill_agents:
                    accessible_skills.append(s)
            
            return {
                "success": True,
                "agent_id": agent_id.value,
                "count": len(accessible_skills),
                "custom_skills": [
                    {
                        "id": s.get("id"),
                        "name": s.get("name"),
                        "description": s.get("description"),
                        "category": s.get("category"),
                        "created_at": s.get("created_at")
                    }
                    for s in accessible_skills
                ]
            }
            
        except Exception as e:
            logger.error(f"Error listing user skills: {e}")
            return {"success": False, "error": str(e)}
    
    list_user_skills.__name__ = "list_user_skills"
    list_user_skills.__doc__ = f"""List custom skills created for the current user (accessible by {agent_id.value}).

Returns:
    Dictionary with user's custom skills that this agent can access.
"""
    return list_user_skills


def _create_get_skills_summary(agent_id: AgentID) -> Callable:
    """Create a get_skills_summary tool for quick overview."""
    
    @agent_tool
    def get_skills_summary() -> Dict[str, Any]:
        """Get a summary of all skills available to this agent, organized by category.
        
        Use this for a quick overview of what expertise is available.
        
        Returns:
            Dictionary with skills organized by category.
        """
        try:
            summary = skills_registry.get_agent_skills_summary(agent_id)
            
            total = sum(len(skills) for skills in summary.values())
            
            return {
                "success": True,
                "agent_id": agent_id.value,
                "total_skills": total,
                "categories": {
                    cat: {
                        "count": len(skills),
                        "skills": skills
                    }
                    for cat, skills in summary.items()
                },
                "tip": "Use 'search_skills' or 'list_skills' to find specific skills."
            }
            
        except Exception as e:
            logger.error(f"Error getting skills summary for {agent_id.value}: {e}")
            return {"success": False, "error": str(e)}
    
    get_skills_summary.__name__ = "get_skills_summary"
    get_skills_summary.__doc__ = f"""Get a summary of all skills available to the {agent_id.value} agent.
    
Use this for a quick overview of what expertise is available.

Returns:
    Dictionary with skills organized by category.
"""
    return get_skills_summary


# =============================================================================
# Tool Factory Function
# =============================================================================

def get_agent_skill_tools(agent_id: AgentID) -> List[Callable]:
    """Get all skill-related tools configured for a specific agent.
    
    This function creates a set of skill tools that are bound to the
    specified agent ID for proper access control.
    
    Args:
        agent_id: The AgentID enum value identifying the agent.
        
    Returns:
        List of skill tools configured for the agent.
    """
    return [
        _create_list_skills(agent_id),
        _create_use_skill(agent_id),
        _create_search_skills(agent_id),
        _create_get_skills_summary(agent_id),
        _create_create_custom_skill(agent_id),
        _create_list_user_skills(agent_id),
    ]


# =============================================================================
# Convenience exports for direct usage
# =============================================================================

# Pre-built tool sets for each agent (for manual import if needed)
EXEC_SKILL_TOOLS = get_agent_skill_tools(AgentID.EXEC)
FIN_SKILL_TOOLS = get_agent_skill_tools(AgentID.FIN)
CONT_SKILL_TOOLS = get_agent_skill_tools(AgentID.CONT)
STRAT_SKILL_TOOLS = get_agent_skill_tools(AgentID.STRAT)
SALES_SKILL_TOOLS = get_agent_skill_tools(AgentID.SALES)
MKT_SKILL_TOOLS = get_agent_skill_tools(AgentID.MKT)
OPS_SKILL_TOOLS = get_agent_skill_tools(AgentID.OPS)
HR_SKILL_TOOLS = get_agent_skill_tools(AgentID.HR)
LEGAL_SKILL_TOOLS = get_agent_skill_tools(AgentID.LEGAL)
SUPP_SKILL_TOOLS = get_agent_skill_tools(AgentID.SUPP)
DATA_SKILL_TOOLS = get_agent_skill_tools(AgentID.DATA)

# Mapping for easy lookup
AGENT_SKILL_TOOLS_MAP = {
    AgentID.EXEC: EXEC_SKILL_TOOLS,
    AgentID.FIN: FIN_SKILL_TOOLS,
    AgentID.CONT: CONT_SKILL_TOOLS,
    AgentID.STRAT: STRAT_SKILL_TOOLS,
    AgentID.SALES: SALES_SKILL_TOOLS,
    AgentID.MKT: MKT_SKILL_TOOLS,
    AgentID.OPS: OPS_SKILL_TOOLS,
    AgentID.HR: HR_SKILL_TOOLS,
    AgentID.LEGAL: LEGAL_SKILL_TOOLS,
    AgentID.SUPP: SUPP_SKILL_TOOLS,
    AgentID.DATA: DATA_SKILL_TOOLS,
}
