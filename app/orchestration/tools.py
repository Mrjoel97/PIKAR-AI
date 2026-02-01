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

"""Orchestration tools for multi-agent delegation and coordination.

Provides tools for the Executive Agent to delegate tasks to specialized agents
and coordinate multi-agent workflows.
"""

import os
from typing import Any
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Get Supabase client for database operations."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        # Return None if not configured (for testing)
        return None
    
    return create_client(url, key)


def get_available_agents() -> dict:
    """Get list of all available specialized agents.
    
    Returns:
        Dictionary containing list of agents with their names, roles, and capabilities.
    """
    client = get_supabase_client()
    
    if not client:
        # Return mock data for testing
        return {
            "agents": [
                {"name": "Financial Analysis Agent", "role": "CFO / Financial Analyst"},
                {"name": "Content Creation Agent", "role": "CMO / Creative Director"},
                {"name": "Strategic Planning Agent", "role": "Chief Strategy Officer"},
                {"name": "Sales Intelligence Agent", "role": "Head of Sales"},
                {"name": "Marketing Automation Agent", "role": "Marketing Director"},
                {"name": "Operations Optimization Agent", "role": "COO / Operations Manager"},
                {"name": "HR & Recruitment Agent", "role": "Human Resources Manager"},
                {"name": "Compliance & Risk Agent", "role": "Legal Counsel"},
                {"name": "Customer Support Agent", "role": "CTO / IT Support"},
                {"name": "Data Analysis Agent", "role": "Data Analyst"},
            ]
        }
    
    try:
        response = client.table("agents").select(
            "name, role, description, enabled_tools"
        ).eq("is_system", True).neq("name", "Executive Agent").execute()
        
        return {"agents": response.data if response.data else []}
    except Exception as e:
        return {"agents": [], "error": str(e)}


def delegate_to_agent(agent_name: str, task_description: str) -> dict:
    """Delegate a task to a specialized agent.
    
    This tool allows the Executive Agent to delegate specific tasks to
    specialized agents based on the task requirements.
    
    Args:
        agent_name: The name of the agent to delegate to (e.g., "Financial Analysis Agent").
        task_description: A clear description of what the agent should accomplish.
        
    Returns:
        Dictionary with delegation status and agent response.
    """
    client = get_supabase_client()
    
    # Validate agent exists
    available_agents = get_available_agents()
    agent_names = [a["name"] for a in available_agents.get("agents", [])]
    
    if agent_name not in agent_names:
        return {
            "success": False,
            "error": f"Agent '{agent_name}' not found. Available agents: {', '.join(agent_names)}",
        }
    
    # Log the delegation (in a real implementation, this would queue the task)
    print(f"Delegating to {agent_name}: {task_description}")
    
    # For now, return acknowledgment (actual agent invocation handled by ADK sub_agents)
    return {
        "success": True,
        "agent": agent_name,
        "task": task_description,
        "status": "delegated",
        "message": f"Task successfully delegated to {agent_name}. The agent will process your request.",
    }


def get_agent_capabilities(agent_name: str) -> dict:
    """Get the capabilities and tools available to a specific agent.
    
    Args:
        agent_name: The name of the agent to query.
        
    Returns:
        Dictionary with agent capabilities, tools, and system prompt.
    """
    client = get_supabase_client()
    
    if not client:
        return {"error": "Database not configured"}
    
    try:
        response = client.table("agents").select(
            "name, role, description, system_prompt, enabled_tools"
        ).eq("name", agent_name).single().execute()
        
        if response.data:
            return {
                "agent": response.data["name"],
                "role": response.data["role"],
                "description": response.data.get("description"),
                "tools": response.data.get("enabled_tools", []),
            }
        return {"error": f"Agent '{agent_name}' not found"}
    except Exception as e:
        return {"error": str(e)}


def request_agent_consensus(question: str, agent_names: list[str]) -> dict:
    """Request consensus from multiple agents on a decision.
    
    This implements the Consensus orchestration pattern where multiple
    agents provide their perspective and a decision is synthesized.
    
    Args:
        question: The question or decision to get consensus on.
        agent_names: List of agent names to consult.
        
    Returns:
        Dictionary with each agent's perspective (placeholder for actual implementation).
    """
    if not agent_names:
        return {"error": "No agents specified for consensus"}
    
    # Validate agents exist
    available = get_available_agents()
    valid_agents = [a["name"] for a in available.get("agents", [])]
    invalid = [n for n in agent_names if n not in valid_agents]
    
    if invalid:
        return {"error": f"Invalid agents: {', '.join(invalid)}"}
    
    # Placeholder - actual implementation would invoke each agent
    return {
        "question": question,
        "agents_consulted": agent_names,
        "status": "pending",
        "message": "Consensus request submitted. Each agent will provide their perspective.",
    }
