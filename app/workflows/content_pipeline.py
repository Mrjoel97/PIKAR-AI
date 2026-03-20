"""Content Pipeline Orchestrator.

Defines a 10-stage creative pipeline that chains together existing tools
into a structured workflow:

    Brief → Research → Concepts → Script → Art Direction →
    Storyboard → Asset Generation → Assembly → Publish Strategy → Repurpose

Each stage has defined inputs/outputs, can be paused for approval,
and tracks progress via Supabase. Pipelines support re-entry at any stage.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """The 10 stages of the creative content pipeline."""

    BRIEF = "brief"
    RESEARCH = "research"
    CONCEPTS = "concepts"
    SCRIPT = "script"
    ART_DIRECTION = "art_direction"
    STORYBOARD = "storyboard"
    ASSET_GENERATION = "asset_generation"
    ASSEMBLY = "assembly"
    PUBLISH_STRATEGY = "publish_strategy"
    REPURPOSE = "repurpose"


class PipelineStatus(str, Enum):
    """Pipeline execution statuses."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(str, Enum):
    """Individual stage statuses."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"


# Stage order for sequential execution
STAGE_ORDER = list(PipelineStage)

# Stage metadata: which tools/agents each stage maps to
STAGE_DEFINITIONS = {
    PipelineStage.BRIEF: {
        "name": "Creative Brief",
        "description": "Transform the idea into a structured creative brief",
        "tool": "generate_creative_brief",
        "agent": "ContentCreationAgent",
        "requires_approval": False,
        "output_type": "creative_brief",
    },
    PipelineStage.RESEARCH: {
        "name": "Research & Trends",
        "description": "Research market trends, competitors, and audience insights",
        "tool": "deep_research",
        "agent": "ContentCreationAgent",
        "requires_approval": False,
        "output_type": "research_report",
    },
    PipelineStage.CONCEPTS: {
        "name": "Concept Exploration",
        "description": "Generate 3 competing creative directions",
        "tool": "explore_concepts",
        "agent": "ContentCreationAgent",
        "requires_approval": True,
        "output_type": "creative_concepts",
    },
    PipelineStage.SCRIPT: {
        "name": "Script & Copy",
        "description": "Write the content script, captions, or copy",
        "tool": "save_content",
        "agent": "CopywriterAgent",
        "requires_approval": True,
        "output_type": "script",
    },
    PipelineStage.ART_DIRECTION: {
        "name": "Art Direction",
        "description": "Define the visual contract — palette, mood, lighting, composition",
        "tool": "create_art_direction",
        "agent": "GraphicDesignerAgent",
        "requires_approval": False,
        "output_type": "art_direction",
    },
    PipelineStage.STORYBOARD: {
        "name": "Storyboard",
        "description": "Map every shot/scene with timing and descriptions",
        "tool": "save_content",
        "agent": "VideoDirectorAgent",
        "requires_approval": True,
        "output_type": "storyboard",
    },
    PipelineStage.ASSET_GENERATION: {
        "name": "Asset Generation",
        "description": "Generate images, video clips, and graphics",
        "tool": "generate_image,create_video_with_veo",
        "agent": "VideoDirectorAgent,GraphicDesignerAgent",
        "requires_approval": False,
        "output_type": "media_assets",
    },
    PipelineStage.ASSEMBLY: {
        "name": "Assembly & Editing",
        "description": "Assemble scenes into final video or content bundle",
        "tool": "execute_content_pipeline",
        "agent": "VideoDirectorAgent",
        "requires_approval": False,
        "output_type": "assembled_content",
    },
    PipelineStage.PUBLISH_STRATEGY: {
        "name": "Publishing Strategy",
        "description": "Create platform-specific captions, hashtags, and posting schedule",
        "tool": "create_publishing_strategy",
        "agent": "SocialMediaAgent",
        "requires_approval": True,
        "output_type": "publishing_strategy",
    },
    PipelineStage.REPURPOSE: {
        "name": "Cross-Platform Repurpose",
        "description": "Adapt content for multiple platforms and formats",
        "tool": "repurpose_content",
        "agent": "CopywriterAgent",
        "requires_approval": False,
        "output_type": "repurposed_content",
    },
}


def _get_supabase_client():
    """Get Supabase client from centralized service."""
    try:
        from app.services.supabase import get_service_client

        return get_service_client()
    except (ImportError, ConnectionError):
        return None


def _get_request_user_id() -> str | None:
    """Get the current user ID from the request context."""
    try:
        from app.services.request_context import get_current_user_id

        return get_current_user_id()
    except (ImportError, AttributeError):
        return None


async def start_content_pipeline(
    idea: str,
    content_type: str = "",
    target_platform: str = "",
    goal: str = "",
    skip_stages: list[str] | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Start a new content pipeline run.

    Creates a pipeline execution record and initializes all 10 stages.
    The agent should then proceed through each stage sequentially, calling
    the appropriate tools at each step.

    Args:
        idea: The creative idea or content request.
        content_type: Desired output (video ad, blog post, campaign, etc.).
        target_platform: Primary platform (Instagram, TikTok, YouTube, etc.).
        goal: Content objective (awareness, leads, engagement, etc.).
        skip_stages: Optional list of stage names to skip (e.g., ["research", "repurpose"]).
        user_id: Optional user ID override.

    Returns:
        Pipeline execution record with all stages initialized.
    """
    user_id = user_id or _get_request_user_id()
    if not user_id:
        return {"success": False, "error": "No user context available."}

    pipeline_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    skip_set = set(skip_stages or [])

    # Initialize all stages
    stages = []
    for i, stage in enumerate(STAGE_ORDER):
        stage_def = STAGE_DEFINITIONS[stage]
        status = StageStatus.SKIPPED if stage.value in skip_set else StageStatus.PENDING
        stages.append({
            "stage": stage.value,
            "name": stage_def["name"],
            "description": stage_def["description"],
            "order": i,
            "status": status.value,
            "requires_approval": stage_def["requires_approval"],
            "tool": stage_def["tool"],
            "agent": stage_def["agent"],
            "output_type": stage_def["output_type"],
            "output_id": None,
            "output_summary": "",
            "started_at": None,
            "completed_at": None,
        })

    pipeline = {
        "id": pipeline_id,
        "user_id": user_id,
        "idea": idea,
        "content_type": content_type,
        "target_platform": target_platform,
        "goal": goal,
        "status": PipelineStatus.RUNNING.value,
        "current_stage": STAGE_ORDER[0].value,
        "stages": stages,
        "artifacts": {},
        "created_at": now,
        "updated_at": now,
    }

    # Save to Knowledge Vault
    supabase = _get_supabase_client()
    if supabase:
        try:
            supabase.table("knowledge_vault").insert({
                "id": pipeline_id,
                "user_id": user_id,
                "title": f"Content Pipeline: {idea[:80]}",
                "content": json.dumps(pipeline, default=str),
                "document_type": "content_pipeline",
                "metadata": {
                    "pipeline_stage": "started",
                    "content_type": content_type,
                    "platform": target_platform,
                    "total_stages": len([s for s in stages if s["status"] != "skipped"]),
                },
                "created_at": now,
            }).execute()
        except Exception as exc:
            logger.warning("Failed to save pipeline to Knowledge Vault: %s", exc)

    # Build progress display
    progress_lines = []
    for s in stages:
        icon = "⏭️" if s["status"] == "skipped" else "⬜"
        approval = " (approval required)" if s["requires_approval"] else ""
        progress_lines.append(f"{icon} {s['order'] + 1}. {s['name']}{approval}")

    return {
        "success": True,
        "pipeline_id": pipeline_id,
        "pipeline": pipeline,
        "progress": "\n".join(progress_lines),
        "message": (
            f"Content pipeline started with {len([s for s in stages if s['status'] != 'skipped'])} active stages.\n\n"
            "Pipeline stages:\n" + "\n".join(progress_lines) + "\n\n"
            "Begin with Stage 1: generate_creative_brief() to create the brief."
        ),
        "next_stage": STAGE_ORDER[0].value,
        "next_tool": STAGE_DEFINITIONS[STAGE_ORDER[0]]["tool"],
    }


async def update_pipeline_stage(
    pipeline_id: str,
    stage: str,
    status: str,
    output_id: str = "",
    output_summary: str = "",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Update the status and output of a pipeline stage.

    Call this after completing each stage to track progress. When a stage
    is marked as 'completed', the pipeline automatically advances to the next stage.

    Args:
        pipeline_id: The pipeline execution ID.
        stage: Stage name (e.g., "brief", "concepts", "art_direction").
        status: New status (pending, in_progress, completed, skipped, failed, waiting_approval).
        output_id: ID of the output artifact (e.g., brief_id, art_direction_id).
        output_summary: Brief summary of what was produced.
        user_id: Optional user ID override.

    Returns:
        Updated pipeline state with next stage info.
    """
    user_id = user_id or _get_request_user_id()
    if not user_id:
        return {"success": False, "error": "No user context available."}

    supabase = _get_supabase_client()
    if not supabase:
        return {"success": False, "error": "Database not configured."}

    try:
        # Load current pipeline
        result = (
            supabase.table("knowledge_vault")
            .select("content")
            .eq("id", pipeline_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if not result.data:
            return {"success": False, "error": f"Pipeline {pipeline_id} not found."}

        content = result.data.get("content", "{}")
        pipeline = json.loads(content) if isinstance(content, str) else content

        # Update the target stage
        now = datetime.now(timezone.utc).isoformat()
        stage_updated = False
        for s in pipeline.get("stages", []):
            if s["stage"] == stage:
                s["status"] = status
                if output_id:
                    s["output_id"] = output_id
                if output_summary:
                    s["output_summary"] = output_summary
                if status == "in_progress" and not s.get("started_at"):
                    s["started_at"] = now
                if status in ("completed", "skipped"):
                    s["completed_at"] = now
                stage_updated = True
                break

        if not stage_updated:
            return {"success": False, "error": f"Stage '{stage}' not found in pipeline."}

        # Store output artifact reference
        if output_id:
            pipeline.setdefault("artifacts", {})[stage] = {
                "id": output_id,
                "summary": output_summary,
            }

        # Determine next stage
        next_stage = None
        next_tool = None
        all_done = True
        for s in pipeline.get("stages", []):
            if s["status"] in ("pending", "in_progress", "waiting_approval"):
                all_done = False
                if s["status"] == "pending":
                    next_stage = s["stage"]
                    stage_def = STAGE_DEFINITIONS.get(PipelineStage(s["stage"]))
                    next_tool = stage_def["tool"] if stage_def else None
                    break

        # Update pipeline status
        if all_done:
            pipeline["status"] = PipelineStatus.COMPLETED.value
        elif status == "waiting_approval":
            pipeline["status"] = PipelineStatus.WAITING_APPROVAL.value
        elif status == "failed":
            pipeline["status"] = PipelineStatus.PAUSED.value
        else:
            pipeline["status"] = PipelineStatus.RUNNING.value

        pipeline["current_stage"] = next_stage or stage
        pipeline["updated_at"] = now

        # Save updated pipeline
        supabase.table("knowledge_vault").update({
            "content": json.dumps(pipeline, default=str),
            "metadata": {
                "pipeline_stage": next_stage or "completed",
                "content_type": pipeline.get("content_type", ""),
                "platform": pipeline.get("target_platform", ""),
                "completed_stages": len([
                    s for s in pipeline["stages"]
                    if s["status"] in ("completed", "skipped")
                ]),
                "total_stages": len(pipeline["stages"]),
            },
        }).eq("id", pipeline_id).execute()

        # Build progress display
        progress_lines = []
        for s in pipeline.get("stages", []):
            if s["status"] == "completed":
                icon = "✅"
            elif s["status"] == "in_progress":
                icon = "🔄"
            elif s["status"] == "waiting_approval":
                icon = "⏸️"
            elif s["status"] == "skipped":
                icon = "⏭️"
            elif s["status"] == "failed":
                icon = "❌"
            else:
                icon = "⬜"
            summary = f" — {s['output_summary']}" if s.get("output_summary") else ""
            progress_lines.append(f"{icon} {s['order'] + 1}. {s['name']}{summary}")

        result_msg = f"Stage '{stage}' → {status}."
        if next_stage:
            next_def = STAGE_DEFINITIONS.get(PipelineStage(next_stage), {})
            result_msg += f" Next: {next_def.get('name', next_stage)} using {next_tool}."
        elif all_done:
            result_msg += " Pipeline complete!"

        return {
            "success": True,
            "pipeline_id": pipeline_id,
            "stage": stage,
            "status": status,
            "next_stage": next_stage,
            "next_tool": next_tool,
            "pipeline_status": pipeline["status"],
            "progress": "\n".join(progress_lines),
            "message": result_msg,
        }

    except Exception as e:
        logger.error("Failed to update pipeline stage: %s", e)
        return {"success": False, "error": str(e)}


async def get_pipeline_status(
    pipeline_id: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Get the current status and progress of a content pipeline.

    Args:
        pipeline_id: The pipeline execution ID.
        user_id: Optional user ID override.

    Returns:
        Full pipeline state with stage progress.
    """
    user_id = user_id or _get_request_user_id()
    if not user_id:
        return {"success": False, "error": "No user context available."}

    supabase = _get_supabase_client()
    if not supabase:
        return {"success": False, "error": "Database not configured."}

    try:
        result = (
            supabase.table("knowledge_vault")
            .select("content")
            .eq("id", pipeline_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if not result.data:
            return {"success": False, "error": f"Pipeline {pipeline_id} not found."}

        content = result.data.get("content", "{}")
        pipeline = json.loads(content) if isinstance(content, str) else content

        # Build progress display
        progress_lines = []
        completed = 0
        total = 0
        for s in pipeline.get("stages", []):
            if s["status"] == "skipped":
                icon = "⏭️"
            elif s["status"] == "completed":
                icon = "✅"
                completed += 1
                total += 1
            elif s["status"] == "in_progress":
                icon = "🔄"
                total += 1
            elif s["status"] == "waiting_approval":
                icon = "⏸️"
                total += 1
            elif s["status"] == "failed":
                icon = "❌"
                total += 1
            else:
                icon = "⬜"
                total += 1
            summary = f" — {s['output_summary']}" if s.get("output_summary") else ""
            progress_lines.append(f"{icon} {s['order'] + 1}. {s['name']}{summary}")

        return {
            "success": True,
            "pipeline_id": pipeline_id,
            "pipeline": pipeline,
            "status": pipeline.get("status", "unknown"),
            "current_stage": pipeline.get("current_stage"),
            "completed_stages": completed,
            "total_stages": total,
            "progress": "\n".join(progress_lines),
            "artifacts": pipeline.get("artifacts", {}),
        }

    except Exception as e:
        logger.error("Failed to get pipeline status: %s", e)
        return {"success": False, "error": str(e)}


async def list_content_pipelines(
    user_id: str | None = None,
    status_filter: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """List all content pipelines for the current user.

    Args:
        user_id: Optional user ID override.
        status_filter: Optional status filter (running, completed, etc.).
        limit: Max number of pipelines to return.

    Returns:
        List of pipeline summaries.
    """
    user_id = user_id or _get_request_user_id()
    if not user_id:
        return {"success": False, "error": "No user context available."}

    supabase = _get_supabase_client()
    if not supabase:
        return {"success": False, "error": "Database not configured."}

    try:
        query = (
            supabase.table("knowledge_vault")
            .select("id, title, content, metadata, created_at")
            .eq("user_id", user_id)
            .eq("document_type", "content_pipeline")
            .order("created_at", desc=True)
            .limit(limit)
        )
        result = query.execute()

        pipelines = []
        for row in result.data or []:
            content = row.get("content", "{}")
            p = json.loads(content) if isinstance(content, str) else content
            p_status = p.get("status", "unknown")

            if status_filter and p_status != status_filter:
                continue

            pipelines.append({
                "id": row["id"],
                "idea": p.get("idea", ""),
                "content_type": p.get("content_type", ""),
                "platform": p.get("target_platform", ""),
                "status": p_status,
                "current_stage": p.get("current_stage", ""),
                "created_at": row.get("created_at"),
            })

        return {
            "success": True,
            "pipelines": pipelines,
            "count": len(pipelines),
        }

    except Exception as e:
        logger.error("Failed to list pipelines: %s", e)
        return {"success": False, "error": str(e)}


# Exported tools list
CONTENT_PIPELINE_TOOLS = [
    start_content_pipeline,
    update_pipeline_stage,
    get_pipeline_status,
    list_content_pipelines,
]
