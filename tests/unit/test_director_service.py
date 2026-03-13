from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.director_service import DirectorService, _build_storyboard_system_prompt, _clamp_scene_duration


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


def test_build_storyboard_prompt_prefers_fewer_scenes_for_long_videos():
    prompt = _build_storyboard_system_prompt("always", 180)
    assert "approximately 23 scenes" in prompt
    assert "prefer 8-second scenes" in prompt
    assert "ONLY 2 high-impact scene(s)" in prompt


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


def test_normalize_storyboard_preserves_render_type(director: DirectorService):
    storyboard = {
        "scenes": [
            {"description": "hero shot", "duration": 8, "render_type": "imagen"},
            {"description": "cta", "duration": 4, "render_type": "veo"},
        ],
    }

    normalized = director._normalize_storyboard(storyboard, "prompt")

    assert normalized["scenes"][0]["render_type"] == "imagen"
    assert normalized["scenes"][1]["render_type"] == "veo"


def test_normalize_storyboard_caps_veo_for_long_videos(director: DirectorService):
    storyboard = {
        "scenes": [
            {"description": "hook", "duration": 8, "render_type": "veo"},
            {"description": "feature one", "duration": 8, "render_type": "veo"},
            {"description": "feature two", "duration": 8, "render_type": "veo"},
            {"description": "cta", "duration": 8, "render_type": "veo"},
        ],
    }

    normalized = director._normalize_storyboard(storyboard, "prompt", target_duration_seconds=60)

    assert [scene["render_type"] for scene in normalized["scenes"]] == ["veo", "imagen", "imagen", "veo"]


@pytest.mark.asyncio
async def test_create_pro_video_sets_duration_frames(director: DirectorService):
    storyboard_mock = AsyncMock(return_value={"scenes": [{"description": "a", "duration": 4}]})
    with patch.object(
        director, "_generate_storyboard", storyboard_mock
    ), patch.object(
        director,
        "_process_scene",
        AsyncMock(return_value={"index": 0, "duration": 4, "text": "a", "video_url": "https://example.com/a.mp4"}),
    ), patch(
        "app.services.director_service.remotion_render_service.render_programmatic_video",
        return_value=(b"mp4-bytes", "asset-1"),
    ) as render_mock:
        result = await director.create_pro_video("prompt", "user-1", target_duration_seconds=240)

    assert result is not None
    assert storyboard_mock.await_args.kwargs["target_duration_seconds"] == 180
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




@pytest.mark.asyncio
async def test_process_scene_veo_path_skips_image_generation(director: DirectorService):
    image_helper = AsyncMock(return_value=("https://example.com/fallback.png", b"image-bytes"))
    with patch.object(director, "_generate_image_asset_for_scene", image_helper), patch(
        "app.services.director_service.vertex_video_service.generate_video",
        return_value={"success": True, "video_bytes": b"video-bytes", "video_url": None},
    ), patch(
        "app.services.director_service.voiceover_service.synthesize_speech",
        return_value={"success": True, "audio_bytes": b"audio-bytes", "mime_type": "audio/mpeg"},
    ):
        scene = await director._process_scene(
            0,
            {"description": "desc", "text": "caption", "duration": 4, "render_type": "veo"},
            "user-1",
        )

    assert scene is not None
    assert scene["video_url"].startswith("https://example.com/")
    image_helper.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_scene_imagen_path_skips_video_generation(director: DirectorService):
    image_helper = AsyncMock(return_value=("https://example.com/scene.png", b"image-bytes"))
    with patch.object(director, "_generate_image_asset_for_scene", image_helper), patch(
        "app.services.director_service.vertex_video_service.generate_video"
    ) as video_mock, patch(
        "app.services.director_service.voiceover_service.synthesize_speech",
        return_value={"success": True, "audio_bytes": b"audio-bytes", "mime_type": "audio/mpeg"},
    ):
        scene = await director._process_scene(
            0,
            {"description": "desc", "text": "caption", "duration": 4, "render_type": "imagen"},
            "user-1",
        )

    assert scene is not None
    assert scene["video_url"] is None
    assert scene["image_url"] == "https://example.com/scene.png"
    image_helper.assert_awaited_once()
    video_mock.assert_not_called()


def test_director_uses_configured_render_fps(monkeypatch):
    monkeypatch.setenv('DIRECTOR_RENDER_FPS', '24')
    with patch('app.services.director_service.get_service_client', return_value=_SupabaseStub()), patch(
        'app.services.director_service.genai.Client', return_value=MagicMock(), create=True
    ):
        director = DirectorService()

    assert director.fps == 24




def test_normalize_storyboard_caps_long_video_veo_budget(director: DirectorService):
    storyboard = {
        "scenes": [
            {"description": "hook", "duration": 8, "render_type": "veo"},
            {"description": "beat 1", "duration": 8, "render_type": "imagen"},
            {"description": "beat 2", "duration": 8, "render_type": "imagen"},
            {"description": "beat 3", "duration": 8, "render_type": "imagen"},
            {"description": "beat 4", "duration": 8, "render_type": "imagen"},
            {"description": "beat 5", "duration": 8, "render_type": "imagen"},
            {"description": "climax", "duration": 8, "render_type": "veo"},
            {"description": "cta", "duration": 8, "render_type": "veo"},
        ],
    }

    normalized = director._normalize_storyboard(storyboard, "prompt", target_duration_seconds=60)
    veo_indices = [index for index, scene in enumerate(normalized["scenes"]) if scene["render_type"] == "veo"]

    assert veo_indices == [0, 7]



def test_normalize_storyboard_assigns_anchor_veo_scenes_when_missing_render_types(director: DirectorService):
    storyboard = {
        "scenes": [
            {"description": "scene 1", "duration": 8},
            {"description": "scene 2", "duration": 8},
            {"description": "scene 3", "duration": 8},
            {"description": "scene 4", "duration": 8},
            {"description": "scene 5", "duration": 8},
            {"description": "scene 6", "duration": 8},
            {"description": "scene 7", "duration": 8},
            {"description": "scene 8", "duration": 8},
        ],
    }

    normalized = director._normalize_storyboard(storyboard, "prompt", target_duration_seconds=60)
    veo_indices = [index for index, scene in enumerate(normalized["scenes"]) if scene["render_type"] == "veo"]

    assert veo_indices == [0, 7]


@pytest.mark.asyncio
async def test_create_pro_video_uses_ffmpeg_renderer_for_long_multi_scene_outputs(director: DirectorService):
    storyboard = {
        "mood": "upbeat",
        "scenes": [
            {"description": "scene one", "duration": 8, "text": "Hook"},
            {"description": "scene two", "duration": 8, "text": "Middle"},
            {"description": "scene three", "duration": 8, "text": "CTA"},
            {"description": "scene four", "duration": 8, "text": "End"},
            {"description": "scene five", "duration": 8, "text": "Outro"},
            {"description": "scene six", "duration": 8, "text": "Final"},
            {"description": "scene seven", "duration": 8, "text": "Close"},
            {"description": "scene eight", "duration": 8, "text": "Brand"},
        ],
    }
    processed = [
        {
            "index": index,
            "duration": 8,
            "text": scene["text"],
            "image_url": f"https://example.com/{index}.png",
            "image_bytes": f"image-{index}".encode("utf-8"),
        }
        for index, scene in enumerate(storyboard["scenes"])
    ]
    processed[0]["video_url"] = "https://example.com/scene-0.mp4"
    processed[0]["video_bytes"] = b"video-0"

    with patch.object(
        director,
        "_generate_storyboard",
        AsyncMock(return_value=storyboard),
    ), patch.object(
        director,
        "_process_scene",
        AsyncMock(side_effect=processed),
    ), patch(
        "app.services.director_service.remotion_render_service.render_programmatic_video_ffmpeg",
        return_value=(b"mp4-bytes", "asset-ffmpeg"),
    ) as ffmpeg_render_mock, patch(
        "app.services.director_service.remotion_render_service.render_programmatic_video",
    ) as remotion_render_mock:
        result = await director.create_pro_video(
            "prompt",
            "user-1",
            target_duration_seconds=60,
            return_metadata=True,
        )

    assert result is not None
    assert result["render_backend"] == "ffmpeg"
    assert ffmpeg_render_mock.called is True
    render_props = ffmpeg_render_mock.call_args.args[0]
    assert render_props["scenes"][0]["videoBytes"] == b"video-0"
    assert render_props["scenes"][1]["imageBytes"] == b"image-1"
    remotion_render_mock.assert_not_called()
