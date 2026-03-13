from app.services.long_video_benchmark import (
    build_service_crash_report,
    build_service_report,
    build_sse_report,
    choose_best_service_report,
    is_healthy_report,
)


def test_build_service_report_tracks_stage_timings_and_fallbacks():
    progress_events = [
        {"stage": "planning_started", "payload": {}, "elapsed_s": 0.1},
        {"stage": "planning_done", "payload": {}, "elapsed_s": 1.2},
        {"stage": "assets_done", "payload": {"scene_count": 3}, "elapsed_s": 8.5},
        {"stage": "rendering_started", "payload": {"duration_frames": 1800}, "elapsed_s": 9.0},
        {"stage": "completed", "payload": {"video_url": "https://example.com/final.mp4"}, "elapsed_s": 14.4},
    ]
    result_payload = {
        "asset_id": "asset-123",
        "video_url": "https://example.com/final.mp4",
        "storyboard_captions": ["Hook", "Middle", "CTA"],
        "storyboard": {
            "scenes": [
                {"render_type": "veo"},
                {"render_type": "veo"},
                {"render_type": "imagen"},
            ]
        },
        "scenes": [
            {
                "index": 0,
                "text": "Hook",
                "video_url": "https://example.com/scene-0.mp4",
                "image_url": "https://example.com/scene-0.png",
                "voiceover_url": "https://example.com/scene-0.mp3",
            },
            {"index": 1, "text": "Middle", "video_url": None, "image_url": "https://example.com/scene-1.png"},
            {"index": 2, "text": "CTA", "video_url": None, "image_url": "https://example.com/scene-2.png"},
        ],
    }

    report = build_service_report(
        duration_seconds=60,
        prompt="benchmark prompt",
        user_id="benchmark-user",
        env_overrides={"DIRECTOR_MAX_CONCURRENCY": 3},
        progress_events=progress_events,
        result_payload=result_payload,
        started_at_iso="2026-03-11T00:00:00Z",
        total_wall_time_s=14.4,
    )

    assert report["success"] is True
    assert report["timings_s"]["planning"] == 1.1
    assert report["timings_s"]["asset_generation"] == 7.3
    assert report["timings_s"]["render_upload"] == 5.4
    assert report["output"]["storyboard_caption_count"] == 3
    assert report["output"]["planned_veo_scene_count"] == 2
    assert report["output"]["fallback_scene_count"] == 1
    assert report["output"]["image_only_scene_count"] == 2
    assert report["output"]["voiceover_scene_count"] == 1
    assert report["output"]["missing_voiceover_scene_count"] == 2


def test_build_service_report_can_require_voiceover():
    progress_events = [
        {"stage": "planning_started", "payload": {}, "elapsed_s": 0.1},
        {"stage": "completed", "payload": {"video_url": "https://example.com/final.mp4"}, "elapsed_s": 14.4},
    ]
    result_payload = {
        "video_url": "https://example.com/final.mp4",
        "scenes": [
            {"index": 0, "text": "Hook", "video_url": "https://example.com/scene-0.mp4", "voiceover_url": None},
            {"index": 1, "text": "CTA", "image_url": "https://example.com/scene-1.png", "voiceover_url": None},
        ],
    }

    report = build_service_report(
        duration_seconds=60,
        prompt="benchmark prompt",
        user_id="benchmark-user",
        env_overrides=None,
        progress_events=progress_events,
        result_payload=result_payload,
        started_at_iso="2026-03-11T00:00:00Z",
        total_wall_time_s=14.4,
        require_voiceover=True,
    )

    assert report["success"] is False
    assert report["error"] == "voiceover_required_but_missing"
    assert report["diagnostics"]["voiceover_required"] is True


def test_build_sse_report_tracks_video_widget_timings():
    report = build_sse_report(
        duration_seconds=60,
        prompt="benchmark prompt",
        session_id="sess-123",
        api_base_url="http://localhost:8000",
        agent_mode="auto",
        response_status=200,
        event_samples=[
            {"elapsed_s": 0.2, "event_type": "director_progress", "stage": "planning_started", "has_video_widget": False},
            {"elapsed_s": 12.0, "event_type": None, "stage": None, "has_video_widget": True},
        ],
        progress_stages=["planning_started", "planning_done", "completed"],
        first_sse_event_s=0.2,
        first_progress_event_s=0.2,
        first_video_widget_s=12.0,
        total_wall_time_s=12.5,
        final_video_url="https://example.com/final.mp4",
        widget_types={"video", "image"},
    )

    assert report["success"] is True
    assert report["timings_s"]["first_progress_event"] == 0.2
    assert report["timings_s"]["first_video_widget"] == 12.0
    assert report["output"]["video_url"] == "https://example.com/final.mp4"
    assert report["output"]["widget_types"] == ["image", "video"]


def test_choose_best_service_report_prefers_fastest_success():
    slow_success = {
        "success": True,
        "timings_s": {"total_wall_time": 30.0},
        "output": {"video_url": "https://example.com/slow.mp4"},
    }
    fast_success = {
        "success": True,
        "timings_s": {"total_wall_time": 12.5},
        "output": {"video_url": "https://example.com/fast.mp4"},
    }
    failed = {
        "success": False,
        "timings_s": {"total_wall_time": 5.0},
        "output": {"video_url": None},
    }

    winner = choose_best_service_report([slow_success, failed, fast_success])

    assert winner is fast_success
    assert is_healthy_report(winner) is True



def test_build_service_report_includes_failure_payload_and_diagnostics():
    progress_events = [
        {
            "stage": "failed",
            "payload": {
                "reason": "remotion_render_failed",
                "remotion_diagnostics": {
                    "status": "failed",
                    "stderr": "Remotion stderr sample",
                },
            },
            "elapsed_s": 12.4,
        }
    ]

    report = build_service_report(
        duration_seconds=60,
        prompt="benchmark prompt",
        user_id="benchmark-user",
        env_overrides=None,
        progress_events=progress_events,
        result_payload=None,
        started_at_iso="2026-03-11T00:00:00Z",
        total_wall_time_s=12.4,
        diagnostics={"remotion_diagnostics": {"status": "failed", "stderr": "Remotion stderr sample"}},
    )

    assert report["success"] is False
    assert report["error"] == "remotion_render_failed"
    assert report["diagnostics"]["remotion_diagnostics"]["stderr"] == "Remotion stderr sample"
    assert report["diagnostics"]["failure_payload"]["reason"] == "remotion_render_failed"



def test_build_service_crash_report_preserves_traceback():
    report = build_service_crash_report(
        duration_seconds=60,
        prompt="benchmark prompt",
        user_id_prefix="verify-pro-video",
        env_overrides={"DIRECTOR_MAX_CONCURRENCY": 2},
        started_at_iso="2026-03-11T00:00:00Z",
        total_wall_time_s=3.5,
        error="boom",
        traceback_text="Traceback line 1\nTraceback line 2",
    )

    assert report["success"] is False
    assert report["error"] == "boom"
    assert report["diagnostics"]["traceback"] == "Traceback line 1\nTraceback line 2"
