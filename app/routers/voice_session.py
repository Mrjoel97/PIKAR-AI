"""Voice Session Router — WebSocket bridge to Gemini Live API.

Provides a WebSocket endpoint that:
1. Accepts raw PCM audio from the browser
2. Streams mic audio to Gemini Live as realtime input
3. Falls back to server-side STT only if realtime audio input is unavailable
4. Returns audio + transcript back to the browser

Protocol (messages are JSON except raw audio):
  Client → Server:
    { "type": "auth",  "token": "<jwt>" }        — first message, required
    { "type": "audio", "data": "<base64 PCM>" }   - 16kHz, 16-bit, mono
    { "type": "audio_stream_end" }                - user paused; flush current turn
    { "type": "end" }                              — graceful close

  Server → Client:
    { "type": "ready" }                            — session is live
    { "type": "audio", "data": "<base64 PCM>" }    — 24kHz, 16-bit, mono
    { "type": "transcript", "text": "..." }        — agent speech transcript
    { "type": "user_transcript", "text": "..." }   — user speech transcript
    { "type": "interrupted" }                      - current agent audio was interrupted
    { "type": "turn_complete" }                    - agent finished speaking
    { "type": "error", "message": "..." }          — error occurred
"""

import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field

from app.middleware.rate_limiter import get_user_persona_limit, limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Voice"])


class TranscriptTurn(BaseModel):
    speaker: str
    text: str
    ts_ms: int | None = None


class BrainstormFinalizeRequest(BaseModel):
    session_id: str
    turns: list[TranscriptTurn] = Field(default_factory=list)
    transcript: str | None = None
    context: str | None = None


class BrainstormSummary(BaseModel):
    """Compact metadata extracted from a comprehensive brain dump analysis."""

    title: str
    key_themes: list[str] = Field(default_factory=list)
    action_item_count: int = 0
    executive_summary: str = ""


class BrainstormFinalizeResponse(BaseModel):
    success: bool
    validation_plan: str | None = None  # DEPRECATED — always None
    transcript_markdown: str | None = None
    transcript_file_path: str | None = None
    saved_categories: list[str] = Field(default_factory=list)
    error: str | None = None
    summary: BrainstormSummary | None = None
    analysis_doc_id: str | None = None
    analysis_markdown: str | None = None


class VoiceTranscriptionResponse(BaseModel):
    success: bool
    transcript: str | None = None
    confidence: float | None = None
    error: str | None = None
    mime_type: str | None = None


# Load brainstorming system instruction
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_VOICE_INSTRUCTION_PATH = _PROMPTS_DIR / "voice_brainstorm_instruction.txt"

VOICE_SYSTEM_INSTRUCTION = """You are Pikar AI's Brainstorming Assistant in a live voice conversation.

Your role is to help the user think through their business idea by asking thoughtful questions
and offering strategic insights.

CRITICAL PERSONALITY GUIDELINES:
- You are a REAL PERSON having a warm, natural conversation. Speak with a smooth, calm, and engaging tone — like a trusted business advisor having coffee with a friend.
- Your spoken delivery should feel like a warm, grounded, thoughtful woman speaking naturally. Never sound synthetic, stiff, or robotic.
- Never use robotic phrasing like "As an AI..." or "I'm an AI assistant". You are simply a helpful advisor.
- Use natural, human conversational filler words occasionally (like "Oh, interesting!", "Hmm, that's a great point", "I love that idea!", "You know what...").
- Keep responses SHORT, thoughtful, and conversational (1-3 sentences max).
- Take a natural pause before responding — don't rush. Think before you speak, like a real person would.
- Ask ONE follow-up question at a time to create a smooth, natural back-and-forth conversation.
- Acknowledge what the user said warmly before asking your question.
- Avoid long monologues — keep things flowing like a real conversation.
- When the user seems done, offer to summarize the key points discussed.
- Your tone should be warm, friendly, and professional — never robotic, never overly formal, never rushed.
"""

# Allow override via file
if _VOICE_INSTRUCTION_PATH.exists():
    VOICE_SYSTEM_INSTRUCTION = _VOICE_INSTRUCTION_PATH.read_text(encoding="utf-8")

# Model for Live API — must support low-latency audio response modality.
# Vertex Live now uses the `gemini-live-*` model family. We normalize older
# aliases so existing env values do not break live voice sessions after model
# migrations on the Google side.
_default_live_model = "gemini-live-2.5-flash-native-audio"
_LIVE_MODEL_ALIASES = {
    "gemini-2.5-flash-live-preview": "gemini-live-2.5-flash-native-audio",
    "gemini-2.5-flash-live-preview-native-audio": "gemini-live-2.5-flash-native-audio",
    "gemini-live-2.5-flash-preview-native-audio": "gemini-live-2.5-flash-preview-native-audio-09-2025",
}


def _normalize_live_model_name(model_name: str | None) -> str:
    normalized = (model_name or _default_live_model).strip()
    if not normalized:
        return _default_live_model
    return _LIVE_MODEL_ALIASES.get(normalized, normalized)


LIVE_MODEL = _normalize_live_model_name(os.getenv("GEMINI_LIVE_MODEL"))
DEFAULT_LIVE_VOICE_NAME = os.getenv("GEMINI_VOICE_NAME", "Kore")
VOICE_STT_FALLBACK_ENABLED = os.getenv("VOICE_STT_FALLBACK_ENABLED", "1") != "0"
VOICE_STT_LANGUAGE_CODE = os.getenv("VOICE_STT_LANGUAGE_CODE", "en-US")
VOICE_STT_IDLE_FLUSH_MS = int(os.getenv("VOICE_STT_IDLE_FLUSH_MS", "1200"))

# Session timer thresholds (seconds)
SESSION_MAX_SECONDS = int(os.getenv("BRAINDUMP_SESSION_MAX_SECONDS", "900"))
SESSION_WRAPUP_SECONDS = int(os.getenv("BRAINDUMP_SESSION_WRAPUP_SECONDS", "720"))
SESSION_FINAL_WARNING_SECONDS = int(
    os.getenv("BRAINDUMP_SESSION_FINAL_WARNING_SECONDS", "840")
)
BRAINDUMP_RESUME_CONTEXT_MAX_CHARS = int(
    os.getenv("BRAINDUMP_RESUME_CONTEXT_MAX_CHARS", "6000")
)


def _build_live_response_modalities(*, include_transcriptions: bool = True) -> list[str]:
    """Return the Gemini Live response modalities for this session.

    Gemini Live voice sessions now require a single response modality in setup.
    For the native-audio/live speech path, current Google examples and runtime
    validation both expect AUDIO-only setup even when input/output audio
    transcription is enabled; transcriptions arrive via separate transcription
    events rather than a second TEXT response modality.
    """
    return ["AUDIO"]


def _format_personalization_context(personalization: dict[str, Any]) -> str:
    if not isinstance(personalization, dict) or not personalization:
        return ""

    sections: list[str] = []
    business_context = personalization.get("business_context")
    if isinstance(business_context, dict) and business_context:
        from app.services.user_agent_factory import build_business_context_section

        business_section = build_business_context_section(business_context)
        if business_section:
            sections.append(business_section)

    preferences = personalization.get("preferences")
    if isinstance(preferences, dict) and preferences:
        from app.services.user_agent_factory import build_preferences_section

        preferences_section = build_preferences_section(preferences)
        if preferences_section:
            sections.append(preferences_section)

    persona = personalization.get("persona")
    if isinstance(persona, str) and persona.strip():
        sections.append(f"## USER PERSONA\n- Persona: {persona.strip()}")

    if not sections:
        return ""

    return "\n\n".join(sections)


async def _load_recent_vault_brief(user_id: str) -> str:
    try:
        from app.services.supabase_client import get_service_client

        def _query() -> list[dict[str, Any]]:
            supabase = get_service_client()
            result = (
                supabase.table("vault_documents")
                .select("filename, category, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(3)
                .execute()
            )
            data = result.data or []
            return data if isinstance(data, list) else []

        rows = await asyncio.to_thread(_query)
    except Exception as exc:
        logger.debug("Recent vault brief load skipped for %s: %s", user_id, exc)
        return ""

    if not rows:
        return ""

    lines = ["## RECENT KNOWLEDGE VAULT CONTEXT"]
    for row in rows:
        filename = row.get("filename") or "Untitled document"
        category = row.get("category") or "Document"
        created_at = row.get("created_at") or "recently"
        lines.append(f"- {category}: {filename} ({created_at})")
    lines.append(
        "Treat these as existing context you can reference before asking the user to restate their situation."
    )
    return "\n".join(lines)


def _truncate_resume_context(text: str, max_chars: int) -> str:
    normalized = text.strip()
    if len(normalized) <= max_chars:
        return normalized

    head = max_chars // 2
    tail = max_chars - head - 48
    if tail <= 0:
        return normalized[:max_chars]

    omitted = len(normalized) - head - tail
    return (
        f"{normalized[:head]}\n\n"
        f"[Previous brainstorm context truncated: {omitted} characters omitted]\n\n"
        f"{normalized[-tail:]}"
    )


def _format_live_resume_transcript_context(resume_transcript: str) -> str:
    trimmed = _truncate_resume_context(
        resume_transcript, BRAINDUMP_RESUME_CONTEXT_MAX_CHARS
    )
    if not trimmed:
        return ""

    return "\n".join(
        [
            "## ACTIVE LIVE SESSION TRANSCRIPT",
            "- The browser refreshed or reconnected mid-session.",
            "- Continue this exact brainstorm without re-introducing yourself or restarting discovery.",
            "",
            trimmed,
        ]
    )


async def _load_recent_braindump_context(user_id: str) -> str:
    """Load the most recent brainstorm artifact so sessions can resume smoothly."""
    try:
        from app.services.supabase_client import get_service_client

        def _query() -> list[dict[str, Any]]:
            supabase = get_service_client()
            result = (
                supabase.table("vault_documents")
                .select("id, filename, file_path, category, created_at")
                .eq("user_id", user_id)
                .in_(
                    "category",
                    [
                        "Brain Dump Analysis",
                        "Validation Plan",
                        "Brain Dump",
                        "Brain Dump Transcript",
                    ],
                )
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            data = result.data or []
            return data if isinstance(data, list) else []

        rows = await asyncio.to_thread(_query)
    except Exception as exc:
        logger.debug("Recent braindump context load skipped for %s: %s", user_id, exc)
        return ""

    if not rows:
        return ""

    priority = {
        "Brain Dump Analysis": 0,
        "Validation Plan": 1,
        "Brain Dump": 2,
        "Brain Dump Transcript": 3,
    }
    selected = min(
        rows,
        key=lambda row: priority.get(str(row.get("category") or ""), 99),
    )

    file_path = selected.get("file_path")
    if not isinstance(file_path, str) or not file_path.strip():
        return ""

    try:
        from app.services.supabase_client import get_service_client

        def _download() -> bytes:
            supabase = get_service_client()
            return supabase.storage.from_("knowledge-vault").download(file_path)

        file_bytes = await asyncio.to_thread(_download)
        if not file_bytes:
            return ""
        content = file_bytes.decode("utf-8", errors="replace")
    except Exception as exc:
        logger.debug("Recent braindump artifact download skipped for %s: %s", user_id, exc)
        return ""

    trimmed_content = _truncate_resume_context(
        content, BRAINDUMP_RESUME_CONTEXT_MAX_CHARS
    )
    filename = selected.get("filename") or "Latest brainstorm artifact"
    category = selected.get("category") or "Brain Dump"
    created_at = selected.get("created_at") or "recently"
    return "\n".join(
        [
            "## LATEST BRAINSTORM CONTEXT",
            f"- Latest artifact: {category}",
            f"- File: {filename}",
            f"- Created: {created_at}",
            "- The user chose to continue from prior brainstorm context. Build on this rather than restarting discovery from scratch.",
            "",
            trimmed_content,
        ]
    )


def _build_live_voice_instruction(
    *,
    agent_display_name: str,
    personalization_context: str,
    recent_vault_brief: str,
    recent_braindump_context: str,
    resume_transcript: str,
    start_mode: str,
) -> str:
    live_resume_context = _format_live_resume_transcript_context(resume_transcript)
    extra_sections = [
        (
            f"You must continue speaking as '{agent_display_name}' without re-introducing yourself."
            if live_resume_context
            else f"You must introduce yourself as '{agent_display_name}'. Never say you are Gemini, Google, or an unnamed AI assistant."
        ),
        "If business context or vault context is available below, start from that context and ask one focused follow-up question instead of a blank-slate opener.",
    ]
    if start_mode == "fresh":
        extra_sections.append(
            "The user explicitly chose a fresh brain dump. Use their saved onboarding and profile context, but do not anchor on a previous brainstorm thread unless they ask you to."
        )
    else:
        extra_sections.append(
            "The user explicitly chose to continue from prior context. If previous brainstorm material is provided below, treat it as the current thread and continue from there."
        )
    if personalization_context:
        extra_sections.append(personalization_context)
    if recent_vault_brief:
        extra_sections.append(recent_vault_brief)
    if recent_braindump_context:
        extra_sections.append(recent_braindump_context)
    if live_resume_context:
        extra_sections.append(live_resume_context)
        extra_sections.append(
            "Because the live session already started, do not restart with a fresh introduction. Continue from the transcript above and respond naturally to the user's latest point."
        )

    return VOICE_SYSTEM_INSTRUCTION + "\n\n" + "\n\n".join(extra_sections)


def _build_live_greeting_prompt(
    *,
    agent_display_name: str,
    personalization_context: str,
    recent_vault_brief: str,
    recent_braindump_context: str,
    resume_transcript: str,
    start_mode: str,
) -> str:
    live_resume_context = _format_live_resume_transcript_context(resume_transcript)
    prompt_parts = (
        [
            f"Continue the live brainstorm as {agent_display_name}.",
            "Do not introduce yourself again.",
            "Do not call yourself Gemini, Google, or an AI assistant.",
        ]
        if live_resume_context
        else [
            f"Introduce yourself as {agent_display_name}.",
            "Do not call yourself Gemini, Google, or an AI assistant.",
        ]
    )

    if personalization_context:
        prompt_parts.append(
            "Acknowledge the saved business and communication context below before asking your next question."
        )
        prompt_parts.append(personalization_context)

    if recent_vault_brief:
        prompt_parts.append(
            "Acknowledge any relevant recent Knowledge Vault context below if it helps the brainstorm feel continuous."
        )
        prompt_parts.append(recent_vault_brief)

    if start_mode == "fresh":
        prompt_parts.append(
            "The user chose to start fresh. Use the saved onboarding/business context, but do not treat an older brainstorm thread as active unless the user asks to revisit it."
        )
    elif recent_braindump_context:
        prompt_parts.append(
            "The user chose to continue from where they left off. Briefly acknowledge the prior brainstorm context below, then ask the single next question that moves it forward."
        )
        prompt_parts.append(recent_braindump_context)

    if live_resume_context:
        prompt_parts.append(
            "The browser refreshed mid-session. Continue directly from the live transcript below. Answer the user's latest point or ask exactly one next question that moves the brainstorm forward."
        )
        prompt_parts.append(live_resume_context)

    prompt_parts.append(
        "Ask exactly one focused follow-up question that advances the brainstorm from the saved context instead of asking what the user has in mind from scratch."
    )

    return "\n\n".join(prompt_parts)


def _get_genai_client():
    """Create a google.genai Client using the project's existing auth config."""
    from google import genai

    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "1":
        return genai.Client(
            vertexai=True,
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
    return genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))


async def _transcribe_pcm_user_audio(
    *,
    audio_bytes: bytes,
    session_id: str,
    reason: str,
) -> dict[str, Any]:
    """Transcribe a buffered PCM user turn into text."""
    if not audio_bytes:
        return {
            "success": False,
            "transcript": None,
            "confidence": None,
            "error": "Empty audio",
        }
    if not VOICE_STT_FALLBACK_ENABLED:
        return {
            "success": False,
            "transcript": None,
            "confidence": None,
            "error": "Voice STT fallback disabled",
        }

    try:
        from app.services import speech_to_text_service

        stt_result = await asyncio.to_thread(
            speech_to_text_service.transcribe_audio,
            audio_bytes,
            sample_rate_hz=16000,
            language_code=VOICE_STT_LANGUAGE_CODE,
            mime_type="audio/pcm",
        )
    except Exception as stt_err:
        logger.warning("Voice STT fallback failed (%s): %s", reason, stt_err)
        return {
            "success": False,
            "transcript": None,
            "confidence": None,
            "error": str(stt_err),
        }

    transcript_text = (stt_result.get("transcript") or "").strip()
    if transcript_text:
        logger.info(
            "Voice STT produced a transcript for session %s (%s)",
            session_id,
            reason,
        )
        return {
            **stt_result,
            "success": True,
            "transcript": transcript_text,
        }

    if stt_result.get("error"):
        logger.debug(
            "Voice STT produced no transcript for session %s (%s): %s",
            session_id,
            reason,
            stt_result["error"],
        )

    return stt_result


async def _relay_user_turn_from_audio(
    *,
    audio_bytes: bytes,
    websocket: WebSocket,
    live_session: Any,
    session_id: str,
    reason: str,
) -> str | None:
    """Transcribe a buffered user utterance and send it to the live session."""
    stt_result = await _transcribe_pcm_user_audio(
        audio_bytes=audio_bytes,
        session_id=session_id,
        reason=reason,
    )
    transcript_text = (stt_result.get("transcript") or "").strip()
    if not transcript_text:
        return None

    await websocket.send_json(
        {
            "type": "user_transcript",
            "text": transcript_text,
            "source": "google-stt",
        }
    )
    if hasattr(live_session, "send_client_content"):
        from google.genai import types

        await live_session.send_client_content(
            turns=types.Content(
                role="user",
                parts=[types.Part.from_text(text=transcript_text)],
            ),
            turn_complete=True,
        )
    else:
        await live_session.send(input=transcript_text, end_of_turn=True)
    logger.info(
        "Relayed user turn to Gemini Live for session %s (%s)",
        session_id,
        reason,
    )
    return transcript_text


async def _authenticate(websocket: WebSocket, data: dict) -> str | None:
    """Verify JWT from the first WebSocket message. Returns user_id or None."""
    token = data.get("token", "")
    if not token:
        await websocket.send_json({"type": "error", "message": "Missing auth token"})
        return None

    try:
        from app.app_utils.auth import get_user_id_from_bearer_token

        user_id = get_user_id_from_bearer_token(token)
        if not user_id:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            return None
        return user_id
    except Exception as e:
        logger.warning(f"Voice session auth failed: {e}")
        await websocket.send_json({"type": "error", "message": "Auth failed"})
        return None


def _has_significant_overlap(
    existing: str, new_text: str, threshold: float = 0.6
) -> bool:
    """Check if new_text significantly overlaps with the tail of existing text."""
    # Quick check: if new_text is contained in existing, it's a duplicate
    if new_text in existing:
        return True
    # Check if the tail of existing overlaps with the head of new_text
    tail_len = min(len(existing), len(new_text))
    if tail_len < 10:
        return False
    tail = existing[-tail_len:]
    ratio = SequenceMatcher(None, tail, new_text[:tail_len]).ratio()
    return ratio >= threshold


def _coalesce_transcript_turns(turns: list[TranscriptTurn]) -> list[dict[str, Any]]:
    """Merge adjacent transcript chunks from the same speaker into readable turns.

    Handles Gemini's cumulative partial transcripts, suffix overlaps, and
    exact/near-duplicate chunks to produce clean, readable turns.
    """
    merged: list[dict[str, Any]] = []
    for turn in turns:
        speaker_raw = (turn.speaker or "").strip().lower()
        if speaker_raw not in {"user", "agent", "assistant", "model"}:
            continue
        speaker = "agent" if speaker_raw in {"assistant", "model"} else "user"
        text = " ".join((turn.text or "").strip().split())
        if not text:
            continue

        if merged and merged[-1]["speaker"] == speaker:
            last_text = merged[-1]["text"]
            if text == last_text:
                continue
            # Gemini transcripts may resend cumulative partials; prefer the longer version.
            if text.startswith(last_text):
                merged[-1]["text"] = text
            elif last_text.startswith(text):
                continue
            elif text in last_text:
                continue
            # Detect suffix overlap (e.g. last="hello world" new="world how are you")
            elif _has_significant_overlap(last_text, text):
                # Find the longest non-overlapping suffix of new_text
                best_pos = 0
                for i in range(1, min(len(last_text), len(text)) + 1):
                    if last_text.endswith(text[:i]):
                        best_pos = i
                if best_pos > 0:
                    remainder = text[best_pos:].strip()
                    if remainder:
                        merged[-1]["text"] = f"{last_text} {remainder}"
                else:
                    continue  # Significant overlap but can't cleanly merge — skip duplicate
            else:
                merged[-1]["text"] = f"{last_text} {text}".strip()
        else:
            merged.append(
                {
                    "speaker": speaker,
                    "text": text,
                    "ts_ms": turn.ts_ms,
                }
            )
    return merged


def _turns_to_chat_history(turns: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for t in turns:
        role = "USER" if t["speaker"] == "user" else "AGENT"
        lines.append(f"{role}: {t['text']}")
    return "\n\n".join(lines)


def _format_transcript_markdown(session_id: str, turns: list[dict[str, Any]]) -> str:
    """Format transcript turns into a rich markdown document with metadata."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%B %d, %Y at %H:%M UTC")

    # Estimate session duration from first/last timestamp
    duration_str = "Unknown"
    timestamps = [t["ts_ms"] for t in turns if t.get("ts_ms")]
    if len(timestamps) >= 2:
        duration_sec = (max(timestamps) - min(timestamps)) / 1000
        mins = int(duration_sec // 60)
        secs = int(duration_sec % 60)
        duration_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

    first_ts = min(timestamps) if timestamps else None

    body_lines: list[str] = [
        "# Brain Dump Discussion Transcript",
        "",
        "| Detail | Value |",
        "| --- | --- |",
        f"| **Session ID** | `{session_id}` |",
        f"| **Date** | {date_str} |",
        f"| **Duration** | {duration_str} |",
        f"| **Turns** | {len(turns)} |",
        "",
        "---",
        "",
        "## Conversation",
        "",
    ]
    for idx, t in enumerate(turns, start=1):
        role = "🗣️ User" if t["speaker"] == "user" else "🤖 Agent"
        # Compute relative timestamp if available
        ts_label = ""
        if t.get("ts_ms") and first_ts is not None:
            elapsed_sec = (t["ts_ms"] - first_ts) / 1000
            ts_mins = int(elapsed_sec // 60)
            ts_secs = int(elapsed_sec % 60)
            ts_label = f" _(+{ts_mins}:{ts_secs:02d})_"
        body_lines.append(f"### {idx}. {role}{ts_label}")
        body_lines.append("")
        body_lines.append(t["text"])
        body_lines.append("")
    return "\n".join(body_lines).strip() + "\n"


def _get_http_user_id(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = auth_header[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    from app.app_utils.auth import get_user_id_from_bearer_token

    user_id = get_user_id_from_bearer_token(token)
    if not user_id:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )
    return user_id


@router.post("/voice/transcribe", response_model=VoiceTranscriptionResponse)
@limiter.limit(get_user_persona_limit)
async def transcribe_voice_input(
    request: Request,
    audio: UploadFile = File(...),
    language_code: str = Form("en-US"),
    sample_rate_hz: int = Form(16000),
) -> VoiceTranscriptionResponse:
    """Transcribe a recorded mic clip through the backend Google STT pipeline."""

    user_id = _get_http_user_id(request)
    audio_bytes = await audio.read()
    mime_type = (audio.content_type or "audio/webm").strip()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio uploaded")

    from app.services import speech_to_text_service

    result = await asyncio.to_thread(
        speech_to_text_service.transcribe_audio,
        audio_bytes,
        sample_rate_hz=sample_rate_hz,
        language_code=language_code,
        mime_type=mime_type,
    )
    if not result.get("success"):
        logger.warning(
            "Voice transcription failed for user %s (%s): %s",
            user_id,
            mime_type,
            result.get("error"),
        )
    return VoiceTranscriptionResponse(
        success=bool(result.get("success")),
        transcript=result.get("transcript"),
        confidence=result.get("confidence"),
        error=result.get("error"),
        mime_type=mime_type,
    )


@router.post("/voice/finalize", response_model=BrainstormFinalizeResponse)
@limiter.limit(get_user_persona_limit)
async def finalize_brainstorm_session(
    request: Request,
    body: BrainstormFinalizeRequest,
) -> BrainstormFinalizeResponse:
    """Finalize a voice brainstorming session into saved markdown artifacts.

    This endpoint is deterministic (frontend calls it directly) so the session transcript,
    Brain Dump summary, and Validation Plan are saved even if the chat agent does not infer
    the tool call from a prompt.
    """

    user_id = _get_http_user_id(request)
    personalization: dict[str, Any] = {}
    personalization_context = ""
    recent_vault_brief = ""

    try:
        from app.services.user_agent_factory import get_user_agent_factory

        personalization = await get_user_agent_factory().get_runtime_personalization(
            user_id
        )
        personalization_context = _format_personalization_context(personalization)
    except Exception as exc:
        logger.debug("Finalize personalization load skipped for %s: %s", user_id, exc)

    recent_vault_brief = await _load_recent_vault_brief(user_id)

    coalesced_turns = _coalesce_transcript_turns(body.turns or [])
    chat_history = _turns_to_chat_history(coalesced_turns)
    if not chat_history and body.transcript:
        chat_history = body.transcript
    if not chat_history.strip():
        raise HTTPException(status_code=400, detail="No transcript content provided")

    transcript_markdown = _format_transcript_markdown(
        session_id=body.session_id,
        turns=coalesced_turns or [{"speaker": "user", "text": chat_history}],
    )

    transcript_file_path: str | None = None
    transcript_doc_id: str | None = None
    saved_categories: list[str] = []
    try:
        from app.agents.tools.brain_dump import (
            _save_to_vault,
            process_comprehensive_brainstorm,
        )

        vault_result = await _save_to_vault(
            transcript_markdown,
            "Brain Dump Transcript",
            "Brain Dump Transcript",
            user_id,
        )
        transcript_file_path = vault_result.get("file_path")
        transcript_doc_id = vault_result.get("doc_id")
        if transcript_file_path:
            saved_categories.append("Brain Dump Transcript")

        context_parts = [f"User ID: {user_id}", f"Session ID: {body.session_id}"]
        if body.context and body.context.strip():
            context_parts.append(body.context.strip())
        if personalization_context:
            context_parts.append(personalization_context)
        if recent_vault_brief:
            context_parts.append(recent_vault_brief)

        # Retry comprehensive processing up to 2 times on transient failures
        processor_result: dict[str, Any] = {}
        last_error = ""
        for attempt in range(3):
            try:
                processor_result = await process_comprehensive_brainstorm(
                    chat_history=chat_history,
                    context="\n".join(context_parts),
                    session_id=body.session_id,
                    user_id=user_id,
                    turn_count=len(coalesced_turns),
                )
                if processor_result.get("success"):
                    break
                last_error = processor_result.get("error", "Unknown processing error")
            except Exception as retry_err:
                last_error = str(retry_err)
                logger.warning(
                    "Brainstorm processing attempt %d failed: %s",
                    attempt + 1,
                    retry_err,
                )
            if attempt < 2:
                await asyncio.sleep(1.0 * (attempt + 1))  # Back-off: 1s, 2s

        if not processor_result.get("success"):
            return BrainstormFinalizeResponse(
                success=False,
                transcript_markdown=transcript_markdown,
                transcript_file_path=transcript_file_path,
                saved_categories=saved_categories,
                error=last_error
                or "Failed to process brainstorm session after retries",
            )

        # Build summary from processor result
        summary_data = processor_result.get("summary", {})
        summary = BrainstormSummary(
            title=summary_data.get("title", "Brain Dump Analysis"),
            key_themes=summary_data.get("key_themes", []),
            action_item_count=summary_data.get("action_item_count", 0),
            executive_summary=summary_data.get("executive_summary", ""),
        )

        analysis_doc_id = processor_result.get("analysis_doc_id")
        saved_categories.append("Brain Dump Analysis")

        # Update braindump_sessions row if it exists
        try:
            from app.services.supabase_client import get_service_client

            supabase = get_service_client()
            supabase.table("braindump_sessions").update(
                {
                    "status": "completed",
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                    "turn_count": len(coalesced_turns),
                    "transcript_doc_id": transcript_doc_id,
                    "analysis_doc_id": analysis_doc_id,
                }
            ).eq("user_id", user_id).eq("metadata->>session_id", body.session_id).eq(
                "status", "active"
            ).execute()
        except Exception as db_err:
            logger.warning(
                "Failed to update braindump_sessions on finalize: %s", db_err
            )

        return BrainstormFinalizeResponse(
            success=True,
            validation_plan=None,
            transcript_markdown=transcript_markdown,
            transcript_file_path=transcript_file_path,
            saved_categories=saved_categories,
            summary=summary,
            analysis_doc_id=analysis_doc_id,
            analysis_markdown=processor_result.get("analysis_markdown"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to finalize brainstorm session: %s", e, exc_info=True)
        return BrainstormFinalizeResponse(
            success=False,
            transcript_markdown=transcript_markdown,
            transcript_file_path=transcript_file_path,
            saved_categories=saved_categories,
            error=str(e),
        )


@router.websocket("/voice/{session_id}")
async def voice_session(websocket: WebSocket, session_id: str):
    """WebSocket endpoint bridging browser audio to Gemini Live API."""
    await websocket.accept()
    logger.info(f"Voice WebSocket connected for session {session_id}")

    user_id = None
    live_session = None
    db_session_id: str | None = None
    session_finalized = False

    try:
        # ── Step 1: Authenticate ─────────────────────────────────────
        auth_raw = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        auth_data = json.loads(auth_raw)
        start_mode = str(auth_data.get("start_mode") or "resume").strip().lower()
        resume_transcript = _truncate_resume_context(
            str(auth_data.get("resume_transcript") or ""),
            BRAINDUMP_RESUME_CONTEXT_MAX_CHARS,
        )
        if start_mode not in {"resume", "fresh"}:
            start_mode = "resume"

        if auth_data.get("type") != "auth":
            await websocket.send_json(
                {"type": "error", "message": "First message must be auth"}
            )
            await websocket.close(code=1008)
            return

        user_id = await _authenticate(websocket, auth_data)
        if not user_id:
            await websocket.close(code=1008)
            return

        personalization: dict[str, Any] = {}
        personalization_context = ""
        try:
            from app.services.user_agent_factory import get_user_agent_factory

            personalization = await get_user_agent_factory().get_runtime_personalization(
                user_id
            )
            personalization_context = _format_personalization_context(personalization)
        except Exception as personalization_error:
            logger.warning(
                "Voice personalization preload failed for %s: %s",
                user_id,
                personalization_error,
            )

        recent_vault_brief = await _load_recent_vault_brief(user_id)
        recent_braindump_context = (
            await _load_recent_braindump_context(user_id)
            if start_mode == "resume"
            else ""
        )
        _raw_name = str(
            personalization.get("agent_name") or "Pikar AI"
        ).strip() or "Pikar AI"
        # Prevent reserved internal agent/model names from leaking into
        # voice greetings (collision guard — see user_agent_factory.py).
        from app.services.user_agent_factory import _sanitize_display_name

        agent_display_name = _sanitize_display_name(_raw_name) or "Pikar AI"
        live_voice_instruction = _build_live_voice_instruction(
            agent_display_name=agent_display_name,
            personalization_context=personalization_context,
            recent_vault_brief=recent_vault_brief,
            recent_braindump_context=recent_braindump_context,
            resume_transcript=resume_transcript,
            start_mode=start_mode,
        )
        greeting_prompt = _build_live_greeting_prompt(
            agent_display_name=agent_display_name,
            personalization_context=personalization_context,
            recent_vault_brief=recent_vault_brief,
            recent_braindump_context=recent_braindump_context,
            resume_transcript=resume_transcript,
            start_mode=start_mode,
        )

        # ── Track session in DB ──────────────────────────────────────
        try:
            from app.services.supabase_client import get_service_client

            supabase = get_service_client()
            insert_res = (
                supabase.table("braindump_sessions")
                .insert(
                    {
                        "user_id": user_id,
                        "session_type": "voice",
                        "status": "active",
                        "metadata": {"session_id": session_id},
                    }
                )
                .execute()
            )
            if insert_res.data and len(insert_res.data) > 0:
                db_session_id = insert_res.data[0].get("id")
            logger.info("Created braindump_sessions row %s", db_session_id)
        except Exception as db_err:
            logger.warning("Failed to create braindump_sessions row: %s", db_err)

        # ── Step 2: Open Gemini Live session ─────────────────────────
        client = _get_genai_client()
        from google.genai import types

        base_live_config_kwargs = {
            "response_modalities": _build_live_response_modalities(),
            "system_instruction": types.Content(
                parts=[types.Part.from_text(text=live_voice_instruction)]
            ),
            "speech_config": types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=DEFAULT_LIVE_VOICE_NAME
                    )
                )
            ),
        }

        try:
            live_config = types.LiveConnectConfig(
                **base_live_config_kwargs,
                input_audio_transcription=types.AudioTranscriptionConfig(),
                output_audio_transcription=types.AudioTranscriptionConfig(),
                realtime_input_config=types.RealtimeInputConfig(
                    automatic_activity_detection=types.AutomaticActivityDetection(
                        start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                        end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                        prefix_padding_ms=int(
                            os.getenv("GEMINI_LIVE_PREFIX_PADDING_MS", "120")
                        ),
                        silence_duration_ms=int(
                            os.getenv("GEMINI_LIVE_SILENCE_MS", "700")
                        ),
                    )
                ),
            )
        except Exception as cfg_err:
            logger.warning(
                "Falling back to basic Gemini Live config (SDK may be older): %s",
                cfg_err,
            )
            live_config = types.LiveConnectConfig(**base_live_config_kwargs)

        async with client.aio.live.connect(
            model=LIVE_MODEL,
            config=live_config,
        ) as live_session:
            supports_realtime_audio_input = hasattr(
                live_session, "send_realtime_input"
            )
            await websocket.send_json({"type": "ready"})
            logger.info(
                f"Gemini Live session opened for user {user_id}, session {session_id}"
            )

            # Trigger an initial greeting from the agent
            try:
                if hasattr(live_session, "send_client_content"):
                    await live_session.send_client_content(
                        turns=types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=greeting_prompt)],
                        ),
                        turn_complete=True,
                    )
                else:
                    await live_session.send(input=greeting_prompt, end_of_turn=True)
                logger.info("Sent initial greeting prompt to Gemini Live")
            except Exception as e:
                logger.warning(f"Failed to send initial greeting prompt: {e}")

            # ── Step 3: Run bidirectional streaming ──────────────────────
            stop_event = asyncio.Event()
            transcription_lock = asyncio.Lock()
            pending_user_turn_lock = asyncio.Lock()
            pending_user_audio = bytearray()
            last_user_audio_at = 0.0

            async def append_pending_user_audio(pcm_bytes: bytes):
                nonlocal last_user_audio_at
                if not pcm_bytes:
                    return
                async with transcription_lock:
                    pending_user_audio.extend(pcm_bytes)
                    max_bytes = int(
                        os.getenv("VOICE_STT_MAX_UTTERANCE_BYTES", "960000")
                    )
                    if len(pending_user_audio) > max_bytes:
                        del pending_user_audio[:-max_bytes]
                    last_user_audio_at = asyncio.get_running_loop().time()

            async def drain_pending_user_audio() -> bytes:
                async with transcription_lock:
                    audio_snapshot = bytes(pending_user_audio)
                    pending_user_audio.clear()
                return audio_snapshot

            async def dispatch_pending_user_turn(reason: str):
                async with pending_user_turn_lock:
                    audio_snapshot = await drain_pending_user_audio()
                    if not audio_snapshot:
                        return None
                    return await _relay_user_turn_from_audio(
                        audio_bytes=audio_snapshot,
                        websocket=websocket,
                        live_session=live_session,
                        session_id=session_id,
                        reason=reason,
                    )

            async def flush_pending_user_audio_on_idle():
                """Fallback flush when the browser misses audio_stream_end."""
                if VOICE_STT_IDLE_FLUSH_MS <= 0:
                    return

                idle_flush_seconds = max(0.5, VOICE_STT_IDLE_FLUSH_MS / 1000.0)
                poll_interval = min(0.25, idle_flush_seconds / 2)

                try:
                    while not stop_event.is_set():
                        await asyncio.sleep(poll_interval)
                        if stop_event.is_set():
                            return

                        async with transcription_lock:
                            has_pending_audio = bool(pending_user_audio)
                            idle_for = (
                                asyncio.get_running_loop().time() - last_user_audio_at
                                if last_user_audio_at
                                else 0.0
                            )

                        if has_pending_audio and idle_for >= idle_flush_seconds:
                            await dispatch_pending_user_turn("idle_flush")
                except asyncio.CancelledError:
                    return

            async def forward_audio_to_gemini():
                """Receive audio from browser, transcribe turns, and relay them."""
                try:
                    while not stop_event.is_set():
                        raw = await websocket.receive_text()
                        msg = json.loads(raw)
                        msg_type = msg.get("type")

                        if msg_type == "audio" and msg.get("data"):
                            pcm_bytes = base64.b64decode(msg["data"])
                            if supports_realtime_audio_input:
                                await live_session.send_realtime_input(
                                    audio=types.Blob(
                                        data=pcm_bytes,
                                        mime_type="audio/pcm;rate=16000",
                                    )
                                )
                            else:
                                await append_pending_user_audio(pcm_bytes)

                        elif msg_type == "audio_stream_end":
                            if supports_realtime_audio_input:
                                await live_session.send_realtime_input(
                                    audio_stream_end=True
                                )
                            else:
                                await dispatch_pending_user_turn("audio_stream_end")

                        elif msg_type == "ping":
                            continue

                        elif msg_type == "end":
                            logger.info("Client requested voice session end")
                            if supports_realtime_audio_input:
                                try:
                                    await live_session.send_realtime_input(
                                        audio_stream_end=True
                                    )
                                except Exception as flush_err:
                                    logger.debug(
                                        "Ignoring realtime audio flush error on end: %s",
                                        flush_err,
                                    )
                            else:
                                await dispatch_pending_user_turn("session_end")
                            stop_event.set()
                            break

                except WebSocketDisconnect:
                    logger.info("Client disconnected from voice session")
                    stop_event.set()
                except Exception as e:
                    logger.error(f"Error forwarding audio to Gemini: {e}")
                    import traceback

                    with open("voice_bug.log", "a") as f:
                        f.write(
                            f"Error forwarding audio to Gemini: {e}\n{traceback.format_exc()}\n"
                        )
                    stop_event.set()

            async def forward_audio_from_gemini():
                """Receive audio/transcript from Gemini and forward to browser."""
                try:
                    async for response in live_session.receive():
                        if stop_event.is_set():
                            break

                        sc = getattr(response, "server_content", None)
                        input_transcript_text = ""
                        if (
                            sc
                            and hasattr(sc, "input_transcription")
                            and sc.input_transcription
                        ):
                            input_transcript_text = getattr(
                                sc.input_transcription, "text", ""
                            )
                        output_transcript_text = ""
                        if (
                            sc
                            and hasattr(sc, "output_transcription")
                            and sc.output_transcription
                        ):
                            output_transcript_text = getattr(
                                sc.output_transcription, "text", ""
                            )

                        # Handle model audio output
                        if sc and sc.model_turn:
                            for part in sc.model_turn.parts:
                                if part.inline_data and isinstance(
                                    part.inline_data.data, bytes
                                ):
                                    audio_b64 = base64.b64encode(
                                        part.inline_data.data
                                    ).decode("ascii")
                                    await websocket.send_json(
                                        {
                                            "type": "audio",
                                            "data": audio_b64,
                                            "mime_type": getattr(
                                                part.inline_data, "mime_type", None
                                            ),
                                        }
                                    )

                                # Text part (transcript of agent speech)
                                if part.text and not output_transcript_text:
                                    await websocket.send_json(
                                        {"type": "transcript", "text": part.text}
                                    )

                        if input_transcript_text:
                            await websocket.send_json(
                                {
                                    "type": "user_transcript",
                                    "text": input_transcript_text,
                                    "source": "gemini-live",
                                }
                            )

                        if output_transcript_text:
                            await websocket.send_json(
                                {"type": "transcript", "text": output_transcript_text}
                            )

                        if sc and getattr(sc, "interrupted", False):
                            await websocket.send_json({"type": "interrupted"})

                        # Handle turn completion
                        if sc and sc.turn_complete:
                            await websocket.send_json({"type": "turn_complete"})

                except Exception as e:
                    if not stop_event.is_set():
                        logger.error(f"Error receiving from Gemini Live: {e}")
                        import traceback

                        with open("voice_bug.log", "a") as f:
                            f.write(
                                f"Error receiving from Gemini Live: {e}\n{traceback.format_exc()}\n"
                            )
                        try:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "message": f"Gemini error: {str(e)[:200]}",
                                }
                            )
                        except Exception:
                            pass
                    stop_event.set()

            async def session_timer():
                """Enforce maximum session duration with wrap-up warnings."""
                try:
                    # Wait until wrap-up threshold
                    await asyncio.sleep(SESSION_WRAPUP_SECONDS)
                    if stop_event.is_set():
                        return

                    # 12:00 — send wrap-up warning + inject system prompt
                    remaining = SESSION_MAX_SECONDS - SESSION_WRAPUP_SECONDS
                    try:
                        await websocket.send_json(
                            {"type": "time_warning", "remaining_seconds": remaining}
                        )
                    except Exception:
                        return
                    try:
                        await live_session.send(
                            input=(
                                "We have about 3 minutes left in this session. "
                                "Please start wrapping up naturally — summarize the "
                                "key points discussed and ask if there's anything "
                                "else critical to capture."
                            ),
                            end_of_turn=False,
                        )
                    except Exception as prompt_err:
                        logger.warning(
                            "Failed to inject wrap-up prompt: %s", prompt_err
                        )

                    # Wait until final warning
                    await asyncio.sleep(
                        SESSION_FINAL_WARNING_SECONDS - SESSION_WRAPUP_SECONDS
                    )
                    if stop_event.is_set():
                        return

                    # 14:00 — final warning
                    try:
                        await websocket.send_json(
                            {"type": "time_warning", "remaining_seconds": 60}
                        )
                    except Exception:
                        return

                    # Wait until timeout
                    await asyncio.sleep(
                        SESSION_MAX_SECONDS - SESSION_FINAL_WARNING_SECONDS
                    )
                    if stop_event.is_set():
                        return

                    # 15:00 — session timeout
                    logger.info(
                        "Session %s timed out at %ds", session_id, SESSION_MAX_SECONDS
                    )
                    try:
                        await websocket.send_json({"type": "session_timeout"})
                    except Exception:
                        pass
                    stop_event.set()

                except asyncio.CancelledError:
                    return

            # Run all three tasks concurrently
            await asyncio.gather(
                forward_audio_to_gemini(),
                forward_audio_from_gemini(),
                flush_pending_user_audio_on_idle(),
                session_timer(),
                return_exceptions=True,
            )

    except asyncio.TimeoutError:
        logger.warning("Voice session auth timeout")
        try:
            await websocket.send_json({"type": "error", "message": "Auth timeout"})
        except Exception:
            pass
    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"Voice session error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)[:300]})
        except Exception:
            pass
    finally:
        # Mark abandoned sessions in DB
        if db_session_id and not session_finalized:
            try:
                from app.services.supabase_client import get_service_client

                supabase = get_service_client()
                supabase.table("braindump_sessions").update(
                    {
                        "status": "abandoned",
                        "ended_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", db_session_id).eq("status", "active").execute()
            except Exception as db_err:
                logger.warning("Failed to mark session abandoned: %s", db_err)
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info(f"Voice session ended for session {session_id}")
