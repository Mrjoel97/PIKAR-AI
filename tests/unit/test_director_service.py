from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.director_service import DirectorService, _clamp_scene_duration


class _StorageBucketStub:
    def upload(self, *args, **kwargs):
        return {"ok": True}

    def get_public_url(self, path: str):
        return f"https://example.com/{path}"


class _StorageStub:
    def from_(self, _bucket: str):
        return _StorageBucketStub()


class _SupabaseStub:
    storage = _StorageStub()


@pytest.fixture
def director():
    with patch("app.services.director_service.get_service_client", return_value=_SupabaseStub()), patch(
        "app.services.director_service.genai.Client", return_value=MagicMock(), create=True
    ):
        return DirectorService()


def test_clamp_scene_duration():
    assert _clamp_scene_duration(None) == 4
    assert _clamp_scene_duration("x") == 4
    assert _clamp_scene_duration(1) == 4
    assert _clamp_scene_duration(5) == 6
    assert _clamp_scene_duration(9) == 8


def test_normalize_storyboard_maps_desc_and_duration(director: DirectorService):
    storyboard = {
        "audio_mood": "upbeat",
        "scenes": [
            {"desc": "scene one", "text": "hello", "duration": 5},
            {"description": "scene two", "duration": 12},
        ],
    }
    normalized = director._normalize_storyboard(storyboard, "prompt")
    assert normalized["mood"] == "upbeat"
    assert len(normalized["scenes"]) == 2
    assert normalized["scenes"][0]["description"] == "scene one"
    assert normalized["scenes"][0]["duration"] == 6
    assert normalized["scenes"][1]["duration"] == 8


@pytest.mark.asyncio
async def test_create_pro_video_sets_duration_frames(director: DirectorService):
    with patch.object(
        director, "_generate_storyboard", AsyncMock(return_value={"scenes": [{"description": "a", "duration": 4}]})
    ), patch.object(
        director,
        "_process_scene",
        AsyncMock(return_value={"index": 0, "duration": 4, "text": "a", "video_url": "https://example.com/a.mp4"}),
    ), patch(
        "app.services.director_service.remotion_render_service.render_programmatic_video",
        return_value=(b"mp4-bytes", "asset-1"),
    ) as render_mock:
        result = await director.create_pro_video("prompt", "user-1")

    assert result is not None
    props = render_mock.call_args.args[0]
    assert props["fps"] == 30
    assert props["durationInFrames"] == 120
    assert len(props["scenes"]) == 1
    assert props["scenes"][0]["transition"]["type"] == "fade"
    assert props["scenes"][0]["captions"][0]["text"] == "a"


@pytest.mark.asyncio
async def test_create_pro_video_emits_progress_and_music_url(director: DirectorService):
    progress = []

    def callback(stage, payload):
        progress.append((stage, payload))

    with patch.object(
        director, "_generate_storyboard", AsyncMock(return_value={"mood": "upbeat", "scenes": [{"description": "a", "duration": 4}]})
    ), patch.object(
        director,
        "_process_scene",
        AsyncMock(return_value={"index": 0, "duration": 4, "text": "a", "video_url": "https://example.com/a.mp4"}),
    ), patch(
        "app.services.director_service.audio_music_service.select_background_music_url",
        return_value="https://example.com/bgm.mp3",
    ), patch(
        "app.services.director_service.remotion_render_service.render_programmatic_video",
        return_value=(b"mp4-bytes", "asset-2"),
    ) as render_mock:
        result = await director.create_pro_video("prompt", "user-1", progress_callback=callback)

    assert result is not None
    props = render_mock.call_args.args[0]
    assert props["bgMusicUrl"] == "https://example.com/bgm.mp3"
    assert any(stage == "planning_started" for stage, _ in progress)
    assert any(stage == "completed" for stage, _ in progress)


@pytest.mark.asyncio
async def test_create_pro_video_can_return_metadata_with_storyboard_captions(director: DirectorService):
    progress = []

    def callback(stage, payload):
        progress.append((stage, payload))

    with patch.object(
        director,
        "_generate_storyboard",
        AsyncMock(
            return_value={
                "mood": "upbeat",
                "scenes": [
                    {"description": "scene one", "text": "Hook line", "duration": 4},
                    {"description": "scene two", "text": "CTA line", "duration": 4},
                ],
            }
        ),
    ), patch.object(
        director,
        "_process_scene",
        AsyncMock(return_value={"index": 0, "duration": 4, "text": "Hook line", "video_url": "https://example.com/a.mp4"}),
    ), patch(
        "app.services.director_service.remotion_render_service.render_programmatic_video",
        return_value=(b"mp4-bytes", "asset-3"),
    ):
        result = await director.create_pro_video(
            "prompt",
            "user-1",
            progress_callback=callback,
            return_metadata=True,
        )

    assert isinstance(result, dict)
    assert result["video_url"] == "https://example.com/user-1/asset-3.mp4"
    assert result["storyboard_captions"] == ["Hook line", "CTA line"]
    completed_payloads = [payload for stage, payload in progress if stage == "completed"]
    assert completed_payloads
    assert completed_payloads[0]["storyboard_captions"] == ["Hook line", "CTA line"]


@pytest.mark.asyncio
async def test_process_scene_adds_voiceover_url(director: DirectorService):
    with patch(
        "app.services.director_service.vertex_video_service.generate_video",
        return_value={"success": True, "video_bytes": b"video-bytes", "video_url": None},
    ), patch(
        "app.services.director_service.voiceover_service.synthesize_speech",
        return_value={"success": True, "audio_bytes": b"audio-bytes", "mime_type": "audio/mpeg"},
    ):
        scene = await director._process_scene(0, {"description": "desc", "text": "caption", "duration": 4}, "user-1")

    assert scene is not None
    assert scene["video_url"].startswith("https://example.com/")
    assert scene["voiceover_url"].startswith("https://example.com/")
