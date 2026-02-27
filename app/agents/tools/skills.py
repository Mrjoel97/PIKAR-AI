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

"""Skills Tools - Agent tools for accessing and creating skills.

This module provides tools for agents to:
1. List available skills from the registry
2. Use skills to get domain knowledge
3. Create new custom skills for the user
4. Search for relevant skills
"""

from typing import Optional, Dict, Any
import logging

from app.agents.tools.base import agent_tool
from app.skills.registry import skills_registry, AgentID
from app.services.request_context import get_current_user_id

logger = logging.getLogger(__name__)


@agent_tool
def list_skills(category: Optional[str] = None) -> Dict[str, Any]:
    """List all available skills, optionally filtered by category.
    
    Use this tool to discover what skills are available to help with tasks.
    Skills provide domain-specific knowledge and expertise.
    
    Args:
        category: Optional category filter. Options: finance, hr, marketing, 
                  sales, compliance, content, data, support, operations, planning.
                  
    Returns:
        Dictionary with count and list of available skills with their descriptions.
    """
    try:
        if category:
            skills = skills_registry.get_by_category(category)
        else:
            skills = skills_registry.list_all()
        
        return {
            "success": True,
            "count": len(skills),
            "skills": [
                {
                    "name": s.name,
                    "description": s.description,
                    "category": s.category,
                }
                for s in skills[:50]  # Limit to first 50 to avoid overwhelming context
            ],
            "tip": "Use 'use_skill' with a skill name to access its knowledge."
        }
    except Exception as e:
        logger.error(f"Error listing skills: {e}")
        return {"success": False, "error": str(e)}


@agent_tool
def use_skill(skill_name: str) -> Dict[str, Any]:
    """Use a skill to get domain-specific knowledge and guidance.
    
    Skills contain expert knowledge on specific topics. Use this tool to
    access frameworks, checklists, best practices, and domain expertise.
    
    Args:
        skill_name: Name of the skill to use (get from list_skills).
        
    Returns:
        Dictionary with skill knowledge and guidance.
    """
    try:
        result = skills_registry.use_skill(skill_name, agent_id=None)
        
        if not result.get("success"):
            return result
        
        # Format the response for the agent
        response = {
            "success": True,
            "skill_name": skill_name,
            "description": result.get("description", ""),
        }
        
        if result.get("knowledge"):
            response["knowledge"] = result["knowledge"]
            
        if result.get("output"):
            response["output"] = result["output"]
            
        return response
        
    except Exception as e:
        logger.error(f"Error using skill '{skill_name}': {e}")
        return {"success": False, "error": str(e)}


@agent_tool
def search_skills(query: str, limit: int = 10) -> Dict[str, Any]:
    """Search for skills matching a query or topic.
    
    Use this to find relevant skills when you're not sure which skill to use.
    
    Args:
        query: Search terms or topic (e.g., "financial analysis", "SEO", "hiring").
        limit: Maximum number of results to return (default: 10).
        
    Returns:
        Dictionary with matching skills and their descriptions.
    """
    try:
        all_skills = skills_registry.list_all()
        query_lower = query.lower()
        keywords = set(query_lower.split())
        
        scored_skills = []
        for skill in all_skills:
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
                    
            # Check knowledge match (if available)
            if skill.knowledge:
                knowledge_lower = skill.knowledge.lower()[:500]  # First 500 chars
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
            "query": query,
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
        logger.error(f"Error searching skills: {e}")
        return {"success": False, "error": str(e)}


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
                       Leave empty for all agents.
                       
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
        
        # Parse target agents
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
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, use create_task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    service.create_custom_skill(
                        user_id=user_id,
                        name=skill_name,
                        description=description,
                        category=category.lower(),
                        agent_ids=agent_ids or [AgentID.EXEC.value],
                        knowledge=knowledge,
                        metadata={"created_by": "agent"}
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
                    agent_ids=agent_ids or [AgentID.EXEC.value],
                    knowledge=knowledge,
                    metadata={"created_by": "agent"}
                )
            )
        
        return {
            "success": True,
            "message": f"Custom skill '{skill_name}' created successfully!",
            "skill_id": record.get("id"),
            "skill_name": record.get("name"),
            "category": record.get("category"),
            "note": "This skill is now available for use in future conversations."
        }
        
    except Exception as e:
        logger.error(f"Error creating custom skill: {e}")
        return {"success": False, "error": str(e)}


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
            # No event loop, create one
            skills = asyncio.run(
                service.list_custom_skills(user_id=user_id, is_active=True)
            )
        
        return {
            "success": True,
            "count": len(skills),
            "custom_skills": [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "description": s.get("description"),
                    "category": s.get("category"),
                    "created_at": s.get("created_at")
                }
                for s in skills
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing user skills: {e}")
        return {"success": False, "error": str(e)}


# Export all skill tools
SKILL_TOOLS = [
    list_skills,
    use_skill,
    search_skills,
    create_custom_skill,
    list_user_skills,
]
