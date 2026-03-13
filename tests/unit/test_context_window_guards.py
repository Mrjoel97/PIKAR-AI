import sys
import types

from app.agents.tools.brain_dump import _truncate_text_for_model


def _load_session_compactor():
    fake_google = sys.modules.setdefault("google", types.ModuleType("google"))
    fake_adk = sys.modules.setdefault("google.adk", types.ModuleType("google.adk"))

    fake_events = types.ModuleType("google.adk.events")

    class Event:
        @staticmethod
        def model_validate(data):
            return data

    fake_events.Event = Event

    fake_sessions = types.ModuleType("google.adk.sessions")

    class Session:  # pragma: no cover - test stub
        pass

    class BaseSessionService:  # pragma: no cover - test stub
        pass

    fake_sessions.Session = Session
    fake_sessions.BaseSessionService = BaseSessionService

    fake_google.adk = fake_adk
    sys.modules["google.adk.events"] = fake_events
    sys.modules["google.adk.sessions"] = fake_sessions

    fake_kv = types.ModuleType("app.rag.knowledge_vault")
    fake_kv.get_supabase_client = lambda: None
    sys.modules["app.rag.knowledge_vault"] = fake_kv

    fake_cache = types.ModuleType("app.services.cache")
    fake_cache.get_cache_service = lambda: None
    sys.modules["app.services.cache"] = fake_cache

    from app.persistence.supabase_session_service import _compact_event_for_context

    return _compact_event_for_context


def test_truncate_text_for_model_preserves_head_and_tail():
    raw = "HEAD-" + ("x" * 12000) + "-TAIL"

    truncated = _truncate_text_for_model(raw, max_chars=1200, label="chat history")

    assert len(truncated) < len(raw)
    assert truncated.startswith("HEAD-")
    assert truncated.endswith("-TAIL")
    assert "chat history truncated" in truncated


def test_compact_event_for_context_truncates_large_text_and_urls():
    compact_event = _load_session_compactor()
    event = {
        "content": {
            "parts": [
                {"text": "A" * 50000},
                {
                    "function_response": {
                        "response": {
                            "type": "image",
                            "data": {
                                "imageUrl": "data:" + ("b" * 50000),
                            },
                        }
                    }
                },
            ]
        }
    }

    compacted = compact_event(event)

    text_part = compacted["content"]["parts"][0]["text"]
    image_url = compacted["content"]["parts"][1]["function_response"]["response"]["data"]["imageUrl"]

    assert len(text_part) < 13000
    assert "characters omitted" in text_part
    assert image_url == "[stored in knowledge vault]"
