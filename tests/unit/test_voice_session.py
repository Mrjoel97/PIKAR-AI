from unittest.mock import AsyncMock

import pytest

from app.routers import voice_session
from app.services import speech_to_text_service


@pytest.mark.asyncio
async def test_relay_user_turn_from_audio_emits_transcript_and_prompts_live_session(
    monkeypatch,
):
    monkeypatch.setattr(voice_session, "VOICE_STT_FALLBACK_ENABLED", True)
    monkeypatch.setattr(
        speech_to_text_service,
        "transcribe_audio",
        lambda *args, **kwargs: {
            "success": True,
            "transcript": "I want to help restaurants retain customers",
            "confidence": 0.94,
            "error": None,
        },
    )

    websocket = AsyncMock()
    live_session = AsyncMock()

    transcript = await voice_session._relay_user_turn_from_audio(
        audio_bytes=b"pcm-audio",
        websocket=websocket,
        live_session=live_session,
        session_id="brainstorm-123",
        reason="audio_stream_end",
    )

    assert transcript == "I want to help restaurants retain customers"
    websocket.send_json.assert_awaited_once_with(
        {
            "type": "user_transcript",
            "text": "I want to help restaurants retain customers",
            "source": "google-stt",
        }
    )
    live_session.send.assert_awaited_once_with(
        input="I want to help restaurants retain customers",
        end_of_turn=True,
    )


@pytest.mark.asyncio
async def test_relay_user_turn_from_audio_skips_empty_transcript(monkeypatch):
    monkeypatch.setattr(voice_session, "VOICE_STT_FALLBACK_ENABLED", True)
    monkeypatch.setattr(
        speech_to_text_service,
        "transcribe_audio",
        lambda *args, **kwargs: {
            "success": False,
            "transcript": None,
            "confidence": None,
            "error": "No speech detected",
        },
    )

    websocket = AsyncMock()
    live_session = AsyncMock()

    transcript = await voice_session._relay_user_turn_from_audio(
        audio_bytes=b"pcm-audio",
        websocket=websocket,
        live_session=live_session,
        session_id="brainstorm-123",
        reason="audio_stream_end",
    )

    assert transcript is None
    websocket.send_json.assert_not_awaited()
    live_session.send.assert_not_awaited()


def test_format_transcript_markdown_includes_session_metadata():
    markdown = voice_session._format_transcript_markdown(
        session_id="brainstorm-123",
        turns=[
            {"speaker": "user", "text": "I want to build something for creators", "ts_ms": 1_000},
            {"speaker": "agent", "text": "What part feels most urgent?", "ts_ms": 5_000},
        ],
    )

    assert "# Brain Dump Discussion Transcript" in markdown
    assert "| **Session ID** | `brainstorm-123` |" in markdown
    assert "| **Turns** | 2 |" in markdown
    assert "## Conversation" in markdown
    assert "I want to build something for creators" in markdown
    assert "What part feels most urgent?" in markdown


def test_build_live_greeting_prompt_continues_after_refresh_without_reintroducing():
    prompt = voice_session._build_live_greeting_prompt(
        agent_display_name="Pikar AI",
        personalization_context="",
        recent_vault_brief="",
        recent_braindump_context="",
        resume_transcript="USER: I want to help salons get more repeat bookings.\nAGENT: What part feels stuck right now?",
        start_mode="resume",
    )

    assert "Continue the live brainstorm as Pikar AI." in prompt
    assert "Do not introduce yourself again." in prompt
    assert "The browser refreshed mid-session." in prompt
    assert "help salons get more repeat bookings" in prompt
    assert "Introduce yourself as Pikar AI." not in prompt


def test_build_live_voice_instruction_prefers_continuation_when_resume_transcript_exists():
    instruction = voice_session._build_live_voice_instruction(
        agent_display_name="Pikar AI",
        personalization_context="",
        recent_vault_brief="",
        recent_braindump_context="",
        resume_transcript="USER: I am refining the value proposition.\nAGENT: Which segment feels most urgent?",
        start_mode="resume",
    )

    assert "without re-introducing yourself" in instruction
    assert "Continue this exact brainstorm without re-introducing yourself" in instruction
    assert "I am refining the value proposition" in instruction
