"""Boardroom debate tool — triggers a multi-agent strategic debate.

This is an async tool (used by ADK agents) that delegates to
``app.agents.strategic.debate.DebateOrchestrator`` for the actual
LLM-backed debate.  Returns a widget-ready data structure the
frontend ``BoardroomWidget`` can render.
"""

import logging
from typing import Any

from app.agents.tools.base import agent_tool

logger = logging.getLogger(__name__)


@agent_tool
async def convene_board_meeting(topic: str, context: str = "") -> dict[str, Any]:
    """Convene a boardroom meeting: triggers a multi-agent debate on a strategic topic.

    Three executive personas (CMO, CFO, CEO) debate the topic over two rounds,
    then a Board Packet is synthesised with recommendations, risks, and next steps.

    Args:
        topic: The strategic question or proposal to debate.
        context: Optional business context (current metrics, constraints, etc.).

    Returns:
        Widget-ready data structure containing the full debate transcript,
        verdict, vote summary, and Board Packet.
    """
    from app.agents.strategic.debate import debate_orchestrator

    try:
        result = await debate_orchestrator.conduct_debate(topic, context=context)
    except Exception as exc:
        logger.exception("Board meeting failed for topic: %s", topic)
        return {
            "type": "boardroom",
            "title": "Boardroom Session",
            "data": {
                "topic": topic,
                "transcript": [],
                "verdict": f"The board meeting could not be completed: {exc}",
                "board_packet": None,
                "vote_summary": {},
            },
        }

    # Serialise transcript turns to plain dicts for the widget
    transcript_dicts = [
        {
            "speaker": turn.speaker,
            "content": turn.content,
            "sentiment": turn.sentiment,
            "round": turn.round,
            "stance": turn.stance,
        }
        for turn in result.transcript
    ]

    board_packet_dict = (
        result.board_packet.model_dump() if result.board_packet else None
    )

    return {
        "type": "boardroom",
        "title": "Boardroom Session",
        "data": {
            "topic": result.topic,
            "transcript": transcript_dicts,
            "verdict": result.verdict,
            "board_packet": board_packet_dict,
            "vote_summary": result.vote_summary,
        },
        "dismissible": True,
        "expandable": True,
    }
