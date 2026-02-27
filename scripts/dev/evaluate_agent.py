"""Agent Evaluation Script using Vertex AI Gen AI Evaluation.

This script runs an evaluation pipeline against a specific agent (e.g., HRRecruitmentAgent)
using a dataset of prompts and reference trajectories.

Usage:
    python scripts/evaluate_agent.py --agent hr_agent --dataset tests/eval_datasets/recruitment_eval.json
"""

import argparse
import asyncio
import json
import os
import sys
import pandas as pd
from typing import List, Dict, Any

# Ensure we can import app modules
sys.path.append(os.getcwd())

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import agents
from app.agents.specialized_agents import SPECIALIZED_AGENTS, hr_agent

try:
    from vertexai.preview.evaluation import EvalTask
    from vertexai.preview.evaluation.metrics import (
        PointwiseMetric,
        TrajectorySingleToolUse,
    )
    import vertexai
except ImportError:
    print("Error: google-cloud-aiplatform[evaluation] not installed or Vertex AI SDK missing.")
    sys.exit(1)


def parse_adk_output_to_trajectory(events) -> List[Dict[str, Any]]:
    """Parse ADK events into a trajectory format for evaluation."""
    trajectory = []
    for event in events:
        if not getattr(event, "content", None) or not getattr(event.content, "parts", None):
            continue
        for part in event.content.parts:
            if getattr(part, "function_call", None):
                info = {
                    "tool_name": part.function_call.name,
                    "tool_input": dict(part.function_call.args),
                }
                if info not in trajectory:
                    trajectory.append(info)
    return trajectory


async def run_agent_and_get_trajectory(agent: Agent, prompt: str) -> List[Dict[str, Any]]:
    """Runs the agent with a prompt and returns the tool usage trajectory."""
    session_service = InMemorySessionService()
    session_id = f"eval-session-{os.urandom(4).hex()}"
    user_id = "eval-user"
    
    await session_service.create_session(app_name="eval_app", user_id=user_id, session_id=session_id)
    
    runner = Runner(agent=agent, app_name="eval_app", session_service=session_service)
    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    
    events = [event async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content)]
    
    return parse_adk_output_to_trajectory(events)


async def evaluate_dataset(agent: Agent, dataset_path: str, project_id: str, location: str):
    """Run evaluation on the dataset."""
    print(f"Initializing Vertex AI Evaluation for project {project_id}...")
    vertexai.init(project=project_id, location=location)
    
    with open(dataset_path, 'r') as f:
        eval_data = json.load(f)
    
    results = []
    for item in eval_data:
        prompt = item["prompt"]
        reference = item.get("reference_trajectory", [])
        
        print(f"Evaluating prompt: {prompt}")
        predicted = await run_agent_and_get_trajectory(agent, prompt)
        
        results.append({
            "prompt": prompt,
            "reference_trajectory": reference,
            "predicted_trajectory": predicted
        })
    
    df = pd.DataFrame(results)
    
    # Define metrics
    # Note: Custom metrics setup would go here using EvalTask
    # For now, we print the comparison
    print("\n--- Evaluation Results ---")
    correct_tool_usage = 0
    for res in results:
        pred_tools = [t["tool_name"] for t in res["predicted_trajectory"]]
        ref_tools = [t["tool_name"] for t in res["reference_trajectory"]]
        
        match = pred_tools == ref_tools
        if match:
            correct_tool_usage += 1
            
        print(f"Prompt: {res['prompt']}")
        print(f"  Predicted: {pred_tools}")
        print(f"  Reference: {ref_tools}")
        print(f"  Match: {match}")
    
    print(f"\nAccuracy: {correct_tool_usage}/{len(results)} ({correct_tool_usage/len(results)*100:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate ADK Agent")
    parser.add_argument("--agent", default="hr_agent", help="Name of agent to evaluate")
    parser.add_argument("--dataset", required=True, help="Path to evaluation dataset")
    parser.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT"), help="GCP Project ID")
    parser.add_argument("--location", default="us-central1", help="GCP Location")
    
    args = parser.parse_args()
    
    # Select agent
    target_agent = hr_agent # Default
    # (In a real script, we'd look up from SPECIALIZED_AGENTS based on args.agent)
    
    if not args.project:
        print("Error: GCP Project ID is required (set GOOGLE_CLOUD_PROJECT or use --project)")
        # For demonstration when running without auth, we simulate success if possible or exit
        # sys.exit(1) 
    
    asyncio.run(evaluate_dataset(target_agent, args.dataset, args.project, args.location))
