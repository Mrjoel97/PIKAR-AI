from __future__ import annotations

import asyncio
import importlib
import json
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

DEFAULT_BENCHMARK_DIR = Path("artifacts") / "benchmarks" / "long_video"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_READ_TIMEOUT_SECONDS = 3600
DEFAULT_SERVICE_BENCHMARK_TIMEOUT_SECONDS = 900
DEFAULT_PROMPT_TEMPLATE = (
    "Create a polished promotional video for an AI product launch that lasts approximately "
    "{duration_seconds} seconds. Use multiple coherent scenes, cinematic pacing, clear visual progression, "
    "and a strong closing call to action."
)


def load_local_env_files(paths: tuple[Path, ...] | None = None) -> list[str]:
    """Load local .env files into the current process without overwriting existing env vars."""
    loaded: list[str] = []
    candidate_paths = paths or (Path(".env"), Path("app/.env"))
    for path in candidate_paths:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip(chr(34)).strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        loaded.append(str(path))
    return loaded


@contextmanager
def temporary_env(overrides: dict[str, Any] | None) -> Iterator[None]:
    """Temporarily apply environment overrides for a benchmark run."""
    previous: dict[str, str | None] = {}
    for key, value in (overrides or {}).items():
        previous[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = str(value)
    try:
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def build_benchmark_prompt(duration_seconds: int) -> str:
    """Build a duration-aware prompt for long-video smoke tests."""
    return DEFAULT_PROMPT_TEMPLATE.format(duration_seconds=int(duration_seconds))


def benchmark_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_output_dir(out_dir: Path | str | None = None) -> Path:
    path = Path(out_dir) if out_dir else DEFAULT_BENCHMARK_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_benchmark_report(
    report: dict[str, Any],
    *,
    out_dir: Path | str | None = None,
    prefix: str | None = None,
) -> Path:
    output_dir = ensure_output_dir(out_dir)
    layer = str(report.get("layer") or "benchmark")
    duration = str(report.get("duration_seconds") or "unknown")
    filename = f"{prefix or layer}-{duration}s-{benchmark_timestamp()}.json"
    path = output_dir / filename
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def build_env_overrides(
    *,
    director_max_concurrency: int | None = None,
    veo_poll_interval: int | None = None,
    veo_poll_interval_min: int | None = None,
    veo_poll_interval_max: int | None = None,
) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if director_max_concurrency is not None:
        overrides["DIRECTOR_MAX_CONCURRENCY"] = director_max_concurrency
    if veo_poll_interval is not None:
        overrides["VEO_POLL_INTERVAL"] = veo_poll_interval
    if veo_poll_interval_min is not None:
        overrides["VEO_POLL_INTERVAL_MIN"] = veo_poll_interval_min
    if veo_poll_interval_max is not None:
        overrides["VEO_POLL_INTERVAL_MAX"] = veo_poll_interval_max
    return overrides


def _rounded_seconds(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 3)


def _first_stage_elapsed(
    progress_events: list[dict[str, Any]], stage: str
) -> float | None:
    for event in progress_events:
        if event.get("stage") == stage:
            return float(event["elapsed_s"])
    return None


def _duration_between(
    progress_events: list[dict[str, Any]], start_stage: str, end_stage: str
) -> float | None:
    start = _first_stage_elapsed(progress_events, start_stage)
    end = _first_stage_elapsed(progress_events, end_stage)
    if start is None or end is None or end < start:
        return None
    return _rounded_seconds(end - start)


def _safe_text_sample(value: Any, *, limit: int = 240) -> str:
    if value is None:
        return ""
    text = json.dumps(value, default=str) if not isinstance(value, str) else value
    return text[:limit]


def _extract_output_summary(result_payload: dict[str, Any] | None) -> dict[str, Any]:
    result_payload = result_payload or {}
    storyboard = (
        result_payload.get("storyboard") if isinstance(result_payload, dict) else {}
    )
    planned_scenes = storyboard.get("scenes") if isinstance(storyboard, dict) else []
    actual_scenes = (
        result_payload.get("scenes") if isinstance(result_payload, dict) else []
    )
    actual_scene_by_index = {
        int(scene.get("index", idx)): scene
        for idx, scene in enumerate(actual_scenes or [])
        if isinstance(scene, dict)
    }

    planned_veo_scene_count = 0
    planned_imagen_scene_count = 0
    fallback_scene_count = 0
    for idx, scene in enumerate(planned_scenes or []):
        if not isinstance(scene, dict):
            continue
        render_type = str(scene.get("render_type") or "").strip().lower()
        if render_type == "veo":
            planned_veo_scene_count += 1
            actual_scene = actual_scene_by_index.get(idx) or {}
            if not actual_scene.get("video_url") and actual_scene.get("image_url"):
                fallback_scene_count += 1
        elif render_type == "imagen":
            planned_imagen_scene_count += 1

    actual_video_scene_count = 0
    image_only_scene_count = 0
    voiceover_scene_count = 0
    missing_voiceover_scene_count = 0
    for scene in actual_scenes or []:
        if not isinstance(scene, dict):
            continue
        if scene.get("video_url"):
            actual_video_scene_count += 1
        elif scene.get("image_url"):
            image_only_scene_count += 1
        if scene.get("voiceover_url") or scene.get("voiceover_bytes"):
            voiceover_scene_count += 1
        elif scene.get("text"):
            missing_voiceover_scene_count += 1

    storyboard_captions = (
        result_payload.get("storyboard_captions")
        if isinstance(result_payload, dict)
        else []
    )

    return {
        "asset_id": result_payload.get("asset_id")
        if isinstance(result_payload, dict)
        else None,
        "video_url": result_payload.get("video_url")
        if isinstance(result_payload, dict)
        else None,
        "render_backend": result_payload.get("render_backend")
        if isinstance(result_payload, dict)
        else None,
        "scene_count": len(actual_scenes or []),
        "storyboard_caption_count": len(storyboard_captions or []),
        "planned_veo_scene_count": planned_veo_scene_count,
        "planned_imagen_scene_count": planned_imagen_scene_count,
        "actual_video_scene_count": actual_video_scene_count,
        "image_only_scene_count": image_only_scene_count,
        "fallback_scene_count": fallback_scene_count,
        "voiceover_scene_count": voiceover_scene_count,
        "missing_voiceover_scene_count": missing_voiceover_scene_count,
    }


def build_service_report(
    *,
    duration_seconds: int,
    prompt: str,
    user_id: str,
    env_overrides: dict[str, Any] | None,
    progress_events: list[dict[str, Any]],
    result_payload: dict[str, Any] | None,
    started_at_iso: str,
    total_wall_time_s: float,
    error: str | None = None,
    diagnostics: dict[str, Any] | None = None,
    require_voiceover: bool = False,
) -> dict[str, Any]:
    output = _extract_output_summary(result_payload)
    failed_events = [
        event for event in progress_events if event.get("stage") == "failed"
    ]
    failure_payload = failed_events[-1].get("payload") if failed_events else {}
    stage_sequence = [str(event.get("stage") or "") for event in progress_events]
    voiceover_missing = bool(
        require_voiceover
        and output.get("scene_count")
        and output.get("missing_voiceover_scene_count")
    )
    success = bool(output.get("video_url")) and not error and not failed_events
    diagnostics_payload = dict(diagnostics or {})
    if failure_payload:
        diagnostics_payload.setdefault("failure_payload", failure_payload)
    if require_voiceover:
        diagnostics_payload["voiceover_required"] = True

    report = {
        "layer": "service",
        "success": success and not voiceover_missing,
        "started_at": started_at_iso,
        "duration_seconds": int(duration_seconds),
        "prompt": prompt,
        "user_id": user_id,
        "env_overrides": env_overrides or {},
        "timings_s": {
            "total_wall_time": _rounded_seconds(total_wall_time_s),
            "planning": _duration_between(
                progress_events, "planning_started", "planning_done"
            ),
            "asset_generation": _duration_between(
                progress_events, "planning_done", "assets_done"
            ),
            "render_upload": _duration_between(
                progress_events, "rendering_started", "completed"
            ),
            "time_to_first_progress": _first_stage_elapsed(
                progress_events, stage_sequence[0]
            )
            if stage_sequence
            else None,
        },
        "progress": {
            "stage_sequence": stage_sequence,
            "event_count": len(progress_events),
            "events": progress_events,
        },
        "output": output,
        "error": (
            error
            or failure_payload.get("error")
            or failure_payload.get("reason")
            or ("voiceover_required_but_missing" if voiceover_missing else None)
        ),
    }
    if diagnostics_payload:
        report["diagnostics"] = diagnostics_payload
    return report


def build_service_crash_report(
    *,
    duration_seconds: int,
    prompt: str,
    user_id_prefix: str,
    env_overrides: dict[str, Any] | None,
    started_at_iso: str,
    total_wall_time_s: float,
    error: str,
    traceback_text: str | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = build_service_report(
        duration_seconds=duration_seconds,
        prompt=prompt,
        user_id=f"{user_id_prefix}-crash",
        env_overrides=env_overrides,
        progress_events=[],
        result_payload=None,
        started_at_iso=started_at_iso,
        total_wall_time_s=total_wall_time_s,
        error=error,
        diagnostics=diagnostics,
    )
    if traceback_text:
        report.setdefault("diagnostics", {})["traceback"] = traceback_text
    return report


async def run_service_benchmark(
    *,
    duration_seconds: int,
    prompt: str | None = None,
    user_id_prefix: str = "long-video-benchmark",
    env_overrides: dict[str, Any] | None = None,
    benchmark_timeout_seconds: int | None = DEFAULT_SERVICE_BENCHMARK_TIMEOUT_SECONDS,
    require_voiceover: bool = False,
) -> dict[str, Any]:
    load_local_env_files()
    prompt = prompt or build_benchmark_prompt(duration_seconds)
    user_id = f"{user_id_prefix}-{benchmark_timestamp()}-{uuid.uuid4().hex[:8]}"
    started_at_iso = datetime.now(timezone.utc).isoformat()
    started_at = time.perf_counter()
    progress_events: list[dict[str, Any]] = []
    error: str | None = None
    result_payload: dict[str, Any] | None = None
    remotion_diagnostics: dict[str, Any] | None = None

    with temporary_env(env_overrides):
        if env_overrides and any(key.startswith("VEO_") for key in env_overrides):
            from app.services import vertex_video_service

            importlib.reload(vertex_video_service)

        from app.services import remotion_render_service

        if env_overrides and any(key.startswith("REMOTION_") for key in env_overrides):
            importlib.reload(remotion_render_service)
        remotion_render_service.clear_last_render_diagnostics()

        from app.services.director_service import DirectorService

        try:
            director = DirectorService()
        except Exception as exc:
            error = str(exc)
            director = None

        async def _progress_callback(
            stage: str, payload: dict[str, Any] | None
        ) -> None:
            progress_events.append(
                {
                    "stage": stage,
                    "payload": payload or {},
                    "elapsed_s": _rounded_seconds(time.perf_counter() - started_at),
                }
            )

        async def _invoke_director() -> None:
            nonlocal result_payload
            maybe_result = await director.create_pro_video(
                prompt,
                user_id,
                progress_callback=_progress_callback,
                return_metadata=True,
                target_duration_seconds=duration_seconds,
            )
            if isinstance(maybe_result, dict):
                result_payload = maybe_result
            elif maybe_result:
                result_payload = {"video_url": maybe_result}

        if director is not None:
            try:
                if benchmark_timeout_seconds and benchmark_timeout_seconds > 0:
                    await asyncio.wait_for(
                        _invoke_director(), timeout=benchmark_timeout_seconds
                    )
                else:
                    await _invoke_director()
            except asyncio.TimeoutError:
                error = (
                    f"benchmark_timeout_after_{int(benchmark_timeout_seconds or 0)}s"
                )
                remotion_diagnostics = (
                    remotion_render_service.get_last_render_diagnostics()
                )
                progress_events.append(
                    {
                        "stage": "failed",
                        "payload": {
                            "reason": "benchmark_timeout",
                            "benchmark_timeout_seconds": int(
                                benchmark_timeout_seconds or 0
                            ),
                            **(
                                {"remotion_diagnostics": remotion_diagnostics}
                                if remotion_diagnostics
                                else {}
                            ),
                        },
                        "elapsed_s": _rounded_seconds(time.perf_counter() - started_at),
                    }
                )
            except Exception as exc:
                error = str(exc)

        if remotion_diagnostics is None:
            remotion_diagnostics = remotion_render_service.get_last_render_diagnostics()

    total_wall_time_s = time.perf_counter() - started_at
    diagnostics = (
        {"remotion_diagnostics": remotion_diagnostics} if remotion_diagnostics else None
    )
    return build_service_report(
        duration_seconds=duration_seconds,
        prompt=prompt,
        user_id=user_id,
        env_overrides=env_overrides,
        progress_events=progress_events,
        result_payload=result_payload,
        started_at_iso=started_at_iso,
        total_wall_time_s=total_wall_time_s,
        error=error,
        diagnostics=diagnostics,
        require_voiceover=require_voiceover,
    )


def _extract_video_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("videoUrl"), str):
            return data["videoUrl"]
        widget = payload.get("widget")
        nested = _extract_video_url(widget)
        if nested:
            return nested
        for value in payload.values():
            nested = _extract_video_url(value)
            if nested:
                return nested
    elif isinstance(payload, list):
        for item in payload:
            nested = _extract_video_url(item)
            if nested:
                return nested
    return None


def _collect_widget_types(payload: Any) -> set[str]:
    widget_types: set[str] = set()
    if isinstance(payload, dict):
        widget_type = payload.get("type")
        if isinstance(widget_type, str):
            widget_types.add(widget_type)
        for value in payload.values():
            widget_types.update(_collect_widget_types(value))
    elif isinstance(payload, list):
        for item in payload:
            widget_types.update(_collect_widget_types(item))
    return widget_types


def build_sse_report(
    *,
    duration_seconds: int,
    prompt: str,
    session_id: str,
    api_base_url: str,
    agent_mode: str,
    response_status: int,
    event_samples: list[dict[str, Any]],
    progress_stages: list[str],
    first_sse_event_s: float | None,
    first_progress_event_s: float | None,
    first_video_widget_s: float | None,
    total_wall_time_s: float,
    final_video_url: str | None,
    widget_types: set[str],
    error: str | None = None,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    success = bool(final_video_url) and not error and response_status == 200
    return {
        "layer": "sse",
        "success": success and not voiceover_missing,
        "duration_seconds": int(duration_seconds),
        "prompt": prompt,
        "session_id": session_id,
        "api_base_url": api_base_url,
        "agent_mode": agent_mode,
        "response_status": response_status,
        "timings_s": {
            "first_sse_event": _rounded_seconds(first_sse_event_s),
            "first_progress_event": _rounded_seconds(first_progress_event_s),
            "first_video_widget": _rounded_seconds(first_video_widget_s),
            "total_wall_time": _rounded_seconds(total_wall_time_s),
        },
        "progress": {
            "stage_sequence": progress_stages,
            "event_count": len(event_samples),
            "events": event_samples,
        },
        "output": {
            "video_url": final_video_url,
            "widget_types": sorted(widget_types),
        },
        "error": error,
        "blocked_reason": blocked_reason,
    }


def run_sse_benchmark(
    *,
    duration_seconds: int,
    prompt: str | None = None,
    api_base_url: str = DEFAULT_API_BASE_URL,
    token: str | None = None,
    agent_mode: str = "auto",
    session_id: str | None = None,
    connect_timeout_seconds: int = 30,
    read_timeout_seconds: int = DEFAULT_READ_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    load_local_env_files()
    prompt = prompt or build_benchmark_prompt(duration_seconds)
    session_id = (
        session_id or f"long-video-sse-{benchmark_timestamp()}-{uuid.uuid4().hex[:8]}"
    )
    api_base_url = api_base_url.rstrip("/")
    if not token:
        return build_sse_report(
            duration_seconds=duration_seconds,
            prompt=prompt,
            session_id=session_id,
            api_base_url=api_base_url,
            agent_mode=agent_mode,
            response_status=0,
            event_samples=[],
            progress_stages=[],
            first_sse_event_s=None,
            first_progress_event_s=None,
            first_video_widget_s=None,
            total_wall_time_s=0.0,
            final_video_url=None,
            widget_types=set(),
            blocked_reason="Missing bearer token for authenticated SSE benchmark",
        )

    url = f"{api_base_url}/a2a/app/run_sse"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    body = {
        "session_id": session_id,
        "new_message": {"parts": [{"text": prompt}]},
        "agent_mode": agent_mode,
    }
    started_at = time.perf_counter()
    response_status = 0
    first_sse_event_s: float | None = None
    first_progress_event_s: float | None = None
    first_video_widget_s: float | None = None
    final_video_url: str | None = None
    error: str | None = None
    progress_stages: list[str] = []
    widget_types: set[str] = set()
    event_samples: list[dict[str, Any]] = []

    try:
        with requests.post(
            url,
            json=body,
            headers=headers,
            stream=True,
            timeout=(connect_timeout_seconds, read_timeout_seconds),
        ) as response:
            response_status = response.status_code
            if response.status_code != 200:
                error = response.text[:500]
            else:
                for raw in response.iter_lines(decode_unicode=True):
                    line = (raw or "").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    elapsed_s = time.perf_counter() - started_at
                    if first_sse_event_s is None:
                        first_sse_event_s = elapsed_s
                    payload_text = line[5:].strip()
                    try:
                        payload = json.loads(payload_text)
                    except json.JSONDecodeError:
                        payload = {"raw": payload_text}

                    sample: dict[str, Any] = {
                        "elapsed_s": _rounded_seconds(elapsed_s),
                        "event_type": payload.get("event_type")
                        if isinstance(payload, dict)
                        else None,
                        "stage": payload.get("stage")
                        if isinstance(payload, dict)
                        else None,
                        "has_video_widget": False,
                        "sample": _safe_text_sample(payload),
                    }

                    if isinstance(payload, dict) and payload.get("error") and not error:
                        error = str(payload.get("error"))

                    if (
                        isinstance(payload, dict)
                        and payload.get("event_type") == "director_progress"
                    ):
                        if first_progress_event_s is None:
                            first_progress_event_s = elapsed_s
                        stage = str(payload.get("stage") or "")
                        if stage:
                            progress_stages.append(stage)

                    video_url = _extract_video_url(payload)
                    if video_url:
                        sample["has_video_widget"] = True
                        final_video_url = video_url
                        if first_video_widget_s is None:
                            first_video_widget_s = elapsed_s
                    widget_types.update(_collect_widget_types(payload))
                    event_samples.append(sample)
    except Exception as exc:
        error = str(exc)

    total_wall_time_s = time.perf_counter() - started_at
    return build_sse_report(
        duration_seconds=duration_seconds,
        prompt=prompt,
        session_id=session_id,
        api_base_url=api_base_url,
        agent_mode=agent_mode,
        response_status=response_status,
        event_samples=event_samples,
        progress_stages=progress_stages,
        first_sse_event_s=first_sse_event_s,
        first_progress_event_s=first_progress_event_s,
        first_video_widget_s=first_video_widget_s,
        total_wall_time_s=total_wall_time_s,
        final_video_url=final_video_url,
        widget_types=widget_types,
        error=error,
    )


def is_healthy_report(report: dict[str, Any]) -> bool:
    if report.get("blocked_reason"):
        return False
    return bool(report.get("success"))


def choose_best_service_report(reports: list[dict[str, Any]]) -> dict[str, Any] | None:
    successful_reports = [report for report in reports if is_healthy_report(report)]
    if not successful_reports:
        return None
    return min(
        successful_reports,
        key=lambda report: float(
            report.get("timings_s", {}).get("total_wall_time") or float("inf")
        ),
    )


def format_report_summary(
    report: dict[str, Any], *, report_path: Path | None = None
) -> str:
    lines = [
        f"layer={report.get('layer')} success={report.get('success')} duration={report.get('duration_seconds')}s",
        f"total_wall_time_s={report.get('timings_s', {}).get('total_wall_time')}",
    ]
    video_url = report.get("output", {}).get("video_url")
    if video_url:
        lines.append(f"video_url={video_url}")
    error = report.get("error") or report.get("blocked_reason")
    if error:
        lines.append(f"error={error}")
    if report_path is not None:
        lines.append(f"report={report_path}")
    return "\n".join(lines)
