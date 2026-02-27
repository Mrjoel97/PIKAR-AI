"""Journey Discovery Service - The Continuous Learning Engine."""

import logging
import json
import asyncio
from typing import List, Dict
from datetime import datetime
from pydantic import BaseModel

from app.agents.tools.adaptive_workflows import generate_workflow_template
from app.agents.shared import get_model

logger = logging.getLogger(__name__)


class ActivityLog(BaseModel):
    action: str
    details: str
    timestamp: datetime


class DiscoveredPattern(BaseModel):
    description: str
    frequency: int
    confidence: float
    suggested_goal: str
    suggested_context: str


class JourneyDiscoveryService:
    """Service to discover new workflows from user behavior."""

    def __init__(self):
        self.model = None
        try:
            self.model = get_model()
        except Exception as e:
            logger.warning("Journey discovery model unavailable; continuing in safe fallback mode: %s", e)

    async def analyze_user_activity(self, user_id: str, logs: List[Dict]) -> List[DiscoveredPattern]:
        if not logs or len(logs) < 5:
            return []

        log_text = "\\n".join([
            f"[{log.get('timestamp')}] {log.get('action')}: {log.get('details')}"
            for log in logs
        ])

        prompt = f"""
        Analyze the following user activity logs from 'Pikar AI'.
        Identify if there are any **repeated sequences** of manual tasks that the user performs frequently.
        
        Focus on sequences of 3 or more steps that match a logical workflow (e.g., "Search X" -> "Summarize X" -> "Email X").
        
        Logs:
        {log_text}
        
        Output a JSON list of patterns found. If none, output empty list [].
        Format:
        [
            {{
                "description": "Short description of the pattern",
                "frequency": "Estimated times repeated in these logs",
                "confidence": "0.0 to 1.0",
                "suggested_goal": "Goal string for a new workflow",
                "suggested_context": "Why this is useful based on the logs"
            }}
        ]
        """

        try:
            if self.model is None:
                return []
            response = await self.model.generate_content_async(prompt)
            text = response.text
            
            start = text.find('[')
            end = text.rfind(']') + 1
            if start == -1 or end == 0:
                return []
                
            data = json.loads(text[start:end])
            patterns = [DiscoveredPattern(**p) for p in data]
            patterns = [p for p in patterns if p.confidence > 0.7]
            
            return patterns

        except Exception as e:
            logger.error(f"Error in journey discovery: {e}")
            return []

    async def propose_workflow_from_pattern(self, user_id: str, pattern: DiscoveredPattern):
        from app.services.user_onboarding_service import get_user_onboarding_service
        
        logger.info(f"Proposing workflow for pattern: {pattern.description}")
        
        # 1. Fetch User Persona
        try:
            onboarding_svc = get_user_onboarding_service()
            await onboarding_svc.get_onboarding_status(user_id)
        except Exception as e:
            logger.warning(f"Could not fetch user persona for {user_id}: {e}")

        # 2. Generate template
        try:
            template = generate_workflow_template(
                user_id=user_id,
                goal=pattern.suggested_goal,
                context=f"Based on user behavior: {pattern.suggested_context}"
            )
        except Exception as e:
            logger.warning(f"Could not generate workflow template: {e}")
            template = {}

        # 3. Save suggestion
        suggestion = {
            "user_id": user_id,
            "origin": "continuous_learning",
            "pattern_description": pattern.description,
            "workflow_template": template,
            "status": "pending_approval",
            "detected_at": datetime.now().isoformat()
        }
        
        logger.info(f"Proposed workflow saved: {suggestion}")
        return suggestion

    async def log_activity(self, user_id: str, action: str, details: str):
        """Log a user activity for pattern analysis.

        Persists to Supabase (fire-and-forget) so the journey discovery engine
        can analyze user behavior patterns and suggest workflows.
        Falls back to logger if Supabase insert fails.
        """
        async def _persist():
            try:
                from app.services.supabase import get_service_client
                client = get_service_client()
                client.table("user_activity_log").insert({
                    "user_id": user_id,
                    "action": action,
                    "details": details[:500],
                    "timestamp": datetime.now().isoformat(),
                }).execute()
            except Exception as e:
                logger.warning("Activity persist failed (logging only): %s", e)
                logger.info("ACTIVITY LOG [%s]: %s - %s", user_id, action, details)

        # Fire-and-forget — don't block the request
        try:
            asyncio.create_task(_persist())
        except RuntimeError:
            logger.info("ACTIVITY LOG [%s]: %s - %s", user_id, action, details)


_discovery_service = JourneyDiscoveryService()

def get_journey_discovery_service():
    return _discovery_service
