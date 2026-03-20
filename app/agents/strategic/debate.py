"""Multi-agent boardroom debate orchestrator.

Conducts a structured 2-round debate between three executive personas
(CMO, CFO, CEO) using real Gemini LLM calls, then synthesises a
Board Packet with actionable recommendations.
"""

import asyncio
import json
import logging
import re
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class DebateTurn(BaseModel):
    """Single utterance in the boardroom transcript."""

    speaker: str  # "CEO", "CMO", "CFO"
    content: str
    sentiment: str = "neutral"  # "positive", "negative", "neutral", "nuanced"
    round: int = 1
    stance: str = ""  # "for", "against", "nuanced" — filled during vote tally


class BoardPacket(BaseModel):
    """Structured output synthesised after the debate concludes."""

    topic: str = ""
    recommendation: str = ""
    confidence: float = 0.0
    pros: list[str] = []
    cons: list[str] = []
    risks: list[str] = []
    estimated_impact: str = ""
    next_steps: list[str] = []
    dissenting_views: list[str] = []


class DebateResult(BaseModel):
    """Complete debate result returned to the caller."""

    topic: str
    transcript: list[DebateTurn]
    verdict: str
    board_packet: BoardPacket | None = None
    vote_summary: dict[str, str] = {}  # speaker -> stance


# ---------------------------------------------------------------------------
# Persona definitions
# ---------------------------------------------------------------------------

_PERSONAS: dict[str, str] = {
    "CMO": (
        "You are the Chief Marketing Officer of a growing startup. "
        "You are bold, optimistic, and growth-obsessed. You advocate for "
        "aggressive marketing spend, brand building, and viral growth loops. "
        "Back your arguments with marketing metrics like CAC, LTV, conversion rates, "
        "and market share. Keep your response under 200 words."
    ),
    "CFO": (
        "You are the Chief Financial Officer of a growing startup. "
        "You are analytical, risk-averse, and focused on unit economics. "
        "You scrutinise every proposal through the lens of ROI, burn rate, "
        "cash runway, and profitability. Challenge assumptions with numbers. "
        "Keep your response under 200 words."
    ),
    "CEO": (
        "You are the Chief Executive Officer of a growing startup. "
        "You must synthesise competing viewpoints and make a clear, decisive "
        "recommendation. Balance ambition with fiscal discipline. Consider "
        "timing, team capacity, and competitive dynamics. "
        "Keep your response under 200 words."
    ),
}

_SENTIMENT_KEYWORDS: dict[str, list[str]] = {
    "positive": ["recommend", "agree", "support", "opportunity", "growth", "advantage", "yes", "approve", "optimistic", "upside"],
    "negative": ["risk", "concern", "disagree", "costly", "dangerous", "oppose", "caution", "warn", "problem", "downside"],
}


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _get_genai_client():
    """Lazy-create a google.genai Client (auto-configures from env vars)."""
    import google.genai as genai

    return genai.Client()


async def _llm_generate(prompt: str) -> str:
    """Make a single Gemini Flash call in a background thread.

    Uses ``asyncio.to_thread`` so the synchronous ``genai.Client`` call
    does not block the event loop.
    """
    client = _get_genai_client()
    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text or ""


async def _get_agent_perspective(
    role: str,
    topic: str,
    context: str,
    prior_arguments: list[str] | None = None,
    debate_round: int = 1,
) -> str:
    """Get one agent's perspective on the topic."""
    role_prompt = _PERSONAS.get(role, "")
    parts: list[str] = [
        f"You are the {role} of the company. {role_prompt}",
        f"\nTopic for board debate: {topic}",
    ]
    if context:
        parts.append(f"\nBusiness context: {context}")

    if prior_arguments:
        parts.append("\nOther board members have said:")
        for arg in prior_arguments:
            parts.append(f"- {arg}")
        if debate_round == 2:
            parts.append(
                "\nThis is Round 2. Respond directly to the arguments above. "
                "Acknowledge strong points, rebut weak ones, and sharpen your position."
            )
        else:
            parts.append("\nGive your perspective, addressing their points where relevant.")

    prompt = "\n".join(parts)
    return await _llm_generate(prompt)


def _infer_sentiment(text: str) -> str:
    """Heuristically classify text sentiment."""
    lower = text.lower()
    pos = sum(1 for kw in _SENTIMENT_KEYWORDS["positive"] if kw in lower)
    neg = sum(1 for kw in _SENTIMENT_KEYWORDS["negative"] if kw in lower)
    if pos > neg + 1:
        return "positive"
    if neg > pos + 1:
        return "negative"
    return "neutral"


def _infer_stance(text: str) -> str:
    """Heuristically classify whether the speaker is for/against/nuanced."""
    lower = text.lower()
    for_signals = ["i support", "i recommend", "we should proceed", "let's do it", "approve", "go ahead", "i agree"]
    against_signals = ["i oppose", "we should not", "too risky", "i disagree", "reject", "cannot support", "do not proceed"]
    score_for = sum(1 for s in for_signals if s in lower)
    score_against = sum(1 for s in against_signals if s in lower)
    if score_for > score_against:
        return "for"
    if score_against > score_for:
        return "against"
    return "nuanced"


# ---------------------------------------------------------------------------
# Board Packet synthesis
# ---------------------------------------------------------------------------

async def _synthesise_board_packet(topic: str, transcript: list[DebateTurn]) -> BoardPacket:
    """Make a final LLM call to produce a structured Board Packet."""
    transcript_text = "\n\n".join(
        f"[{t.speaker} — Round {t.round}]: {t.content}" for t in transcript
    )
    prompt = f"""You are a board secretary summarising a strategic debate.

Topic: {topic}

Transcript:
{transcript_text}

Produce a JSON object with EXACTLY these keys (no markdown fences, just raw JSON):
{{
  "recommendation": "<1-2 sentence recommendation>",
  "confidence": <float 0-1>,
  "pros": ["<pro 1>", "<pro 2>", ...],
  "cons": ["<con 1>", "<con 2>", ...],
  "risks": ["<risk 1>", "<risk 2>", ...],
  "estimated_impact": "<1 sentence estimated business impact>",
  "next_steps": ["<step 1>", "<step 2>", ...],
  "dissenting_views": ["<view 1>", ...]
}}
"""
    try:
        raw = await _llm_generate(prompt)
        # Strip markdown code fences if present
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        data = json.loads(cleaned)
        return BoardPacket(topic=topic, **data)
    except Exception:
        logger.exception("Failed to parse Board Packet from LLM output")
        return BoardPacket(
            topic=topic,
            recommendation="Could not synthesise — see transcript for details.",
        )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class DebateOrchestrator:
    """Orchestrates a multi-round strategic debate between virtual executives."""

    async def conduct_debate(
        self,
        topic: str,
        context: str = "",
    ) -> DebateResult:
        """Run a 2-round structured debate with Board Packet synthesis.

        Round 1: Each agent presents their initial perspective (parallel).
        Round 2: Each agent responds to the others (sequential, needs prior context).
        Synthesis: CEO verdict + structured Board Packet.

        Args:
            topic: The strategic question to debate.
            context: Optional business context (e.g. current revenue, runway).

        Returns:
            DebateResult with full transcript, verdict, vote summary, and Board Packet.
        """
        logger.info("Convening board meeting on: %s", topic)
        transcript: list[DebateTurn] = []

        # ---- Round 1: parallel initial perspectives ----
        round1_roles = ["CMO", "CFO", "CEO"]
        round1_coros = [
            _get_agent_perspective(role, topic, context, debate_round=1)
            for role in round1_roles
        ]
        round1_results = await asyncio.gather(*round1_coros, return_exceptions=True)

        for role, result in zip(round1_roles, round1_results):
            if isinstance(result, Exception):
                logger.warning("Round 1 %s failed: %s", role, result)
                content = f"[{role} was unable to provide input at this time.]"
            else:
                content = result
            turn = DebateTurn(
                speaker=role,
                content=content,
                sentiment=_infer_sentiment(content),
                round=1,
                stance=_infer_stance(content),
            )
            transcript.append(turn)

        # ---- Round 2: sequential rebuttals ----
        for role in round1_roles:
            prior_args = [
                f"{t.speaker} (Round {t.round}): {t.content}"
                for t in transcript
                if t.speaker != role
            ]
            try:
                content = await _get_agent_perspective(
                    role, topic, context, prior_arguments=prior_args, debate_round=2,
                )
            except Exception as exc:
                logger.warning("Round 2 %s failed: %s", role, exc)
                content = f"[{role} deferred to their Round 1 position.]"

            turn = DebateTurn(
                speaker=role,
                content=content,
                sentiment=_infer_sentiment(content),
                round=2,
                stance=_infer_stance(content),
            )
            transcript.append(turn)

        # ---- CEO verdict (use the CEO's Round 2 response) ----
        ceo_round2 = next(
            (t for t in transcript if t.speaker == "CEO" and t.round == 2),
            None,
        )
        verdict = ceo_round2.content if ceo_round2 else "No verdict available."

        # ---- Vote tally ----
        vote_summary: dict[str, str] = {}
        for role in round1_roles:
            # Use the latest round stance for each speaker
            latest = next(
                (t for t in reversed(transcript) if t.speaker == role),
                None,
            )
            vote_summary[role] = latest.stance if latest else "nuanced"

        # ---- Board Packet synthesis ----
        try:
            board_packet = await _synthesise_board_packet(topic, transcript)
        except Exception as exc:
            logger.warning("Board Packet synthesis failed: %s", exc)
            board_packet = BoardPacket(
                topic=topic,
                recommendation="Synthesis failed — refer to transcript.",
            )

        return DebateResult(
            topic=topic,
            transcript=transcript,
            verdict=verdict,
            board_packet=board_packet,
            vote_summary=vote_summary,
        )


debate_orchestrator = DebateOrchestrator()
