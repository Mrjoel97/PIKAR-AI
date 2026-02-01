from typing import Any, Dict
from app.agents.strategic.debate import debate_orchestrator

async def convene_board_meeting(topic: str) -> Dict[str, Any]:
    """
    Convening a board meeting triggers a multi-agent debate on a topic.
    Returns the full transcript and verdict to the user.
    """
    result = await debate_orchestrator.conduct_debate(topic)
    
    # We return the data structure required by the frontend widget
    return {
        "widget_type": "boardroom_debate",
        "title": "Boardroom Session",
        "data": result.dict()
    }
