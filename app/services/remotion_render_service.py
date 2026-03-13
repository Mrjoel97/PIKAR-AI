# Copyright 2025 Pikar AI
# Server-side Remotion render: produce MP4 from scenes (text + duration) and upload to vault.
# Optional: set REMOTION_RENDER_ENABLED=1 and ensure remotion-render package is installed.

import copy
import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit
from urllib.request import urlopen

logger = logging.getLogger(__name__)

# Path to remotion-render package (repo root / remotion-render)
REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTION_RENDER_DIR = os.getenv("REMOTION_RENDER_DIR", str(REPO_ROOT / "remotion-render"))
REMOTION_RENDER_ENABLED = os.getenv("REMOTION_RENDER_ENABLED", "").strip().lower() in ("1", "true", "yes")
REMOTION_RENDER_TIMEOUT = int(os.getenv("REMOTION_RENDER_TIMEOUT", "120"))  # seconds
REMOTION_RENDER_RETRY_ON_TIMEOUT = os.getenv("REMOTION_RENDER_RETRY_ON_TIMEOUT", "1").strip().lower() in ("1", "true", "yes")
REMOTION_RENDER_SCALE = os.getenv("REMOTION_RENDER_SCALE", "").strip()
REMOTION_RENDER_CONCURRENCY = os.getenv("REMOTION_RENDER_CONCURRENCY", "").strip()
REMOTION_RENDER_WIDTH = os.getenv("REMOTION_RENDER_WIDTH", "").strip()
REMOTION_RENDER_HEIGHT = os.getenv("REMOTION_RENDER_HEIGHT", "").strip()
FFMPEG_RENDER_TIMEOUT = int(os.getenv("FFMPEG_RENDER_TIMEOUT", "180"))
FFMPEG_RENDER_PRESET = os.getenv("FFMPEG_RENDER_PRESET", "veryfast").strip() or "veryfast"
FFMPEG_RENDER_CRF = int(os.getenv("FFMPEG_RENDER_CRF", "30"))
FFMPEG_RENDER_AUDIO_BITRATE = os.getenv("FFMPEG_RENDER_AUDIO_BITRATE", "128k").strip() or "128k"
FFMPEG_RENDER_WIDTH = int((os.getenv("FFMPEG_RENDER_WIDTH", "").strip() or REMOTION_RENDER_WIDTH or "1280"))
FFMPEG_RENDER_HEIGHT = int((os.getenv("FFMPEG_RENDER_HEIGHT", "").strip() or REMOTION_RENDER_HEIGHT or "720"))
FFMPEG_RENDER_SAMPLE_RATE = int(os.getenv("FFMPEG_RENDER_SAMPLE_RATE", "48000"))

_LAST_RENDER_DIAGNOSTICS: Dict[str, Any] | None = None


def clear_last_render_diagnostics() -> None:
    global _LAST_RENDER_DIAGNOSTICS
    _LAST_RENDER_DIAGNOSTICS = None


def get_last_render_diagnostics() -> Dict[str, Any] | None:
    if _LAST_RENDER_DIAGNOSTICS is None:
        return None
    return copy.deepcopy(_LAST_RENDER_DIAGNOSTICS)


def _safe_diagnostic_text(value: Any, *, limit: int = 4000) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = str(value)
    text = text.strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...[truncated]"


def _summarize_props(props: Dict[str, Any] | None) -> Dict[str, Any]:
    data = props if isinstance(props, dict) else {}
    scenes = data.get("scenes") if isinstance(data.get("scenes"), list) else []
    return {
        "scene_count": len(scenes),
        "fps": data.get("fps"),
        "duration_in_frames": data.get("durationInFrames"),
        "video_scene_count": sum(1 for scene in scenes if isinstance(scene, dict) and scene.get("videoUrl")),
        "image_scene_count": sum(1 for scene in scenes if isinstance(scene, dict) and scene.get("imageUrl")),
        "voiceover_scene_count": sum(1 for scene in scenes if isinstance(scene, dict) and scene.get("voiceoverUrl")),
        "has_bg_music": bool(data.get("bgMusicUrl")),
    }


def _record_render_diagnostics(
    *,
    render_mode: str,
    status: str,
    reason: str,
    command: List[str] | None = None,
    timeout_seconds: int | None = None,
    returncode: int | None = None,
    stdout: Any = None,
    stderr: Any = None,
    props_summary: Dict[str, Any] | None = None,
    **extra: Any,
) -> None:
    global _LAST_RENDER_DIAGNOSTICS
    payload: Dict[str, Any] = {
        "render_mode": render_mode,
        "status": status,
        "reason": reason,
        "command": list(command or []),
        "timeout_seconds": timeout_seconds,
        "returncode": returncode,
        "stdout": _safe_diagnostic_text(stdout),
        "stderr": _safe_diagnostic_text(stderr),
        "props_summary": props_summary or {},
    }
    for key, value in extra.items():
        if value is not None:
            payload[key] = value
    _LAST_RENDER_DIAGNOSTICS = payload


def _resolve_remotion_cli(render_dir: Path) -> List[str]:
    """Prefer local CLI for lower cold-start overhead; fallback to npx."""
    cli_name = "remotion.cmd" if os.name == "nt" else "remotion"
    local_cli = render_dir / "node_modules" / ".bin" / cli_name
    if local_cli.is_file():
        return [str(local_cli)]
    return ["npx", "remotion"]


def _build_render_cli_args() -> List[str]:
    """Build optional CLI arguments for faster server-side renders."""
    args: List[str] = []
    if REMOTION_RENDER_SCALE:
        args.extend(["--scale", REMOTION_RENDER_SCALE])
    if REMOTION_RENDER_CONCURRENCY:
        args.extend(["--concurrency", REMOTION_RENDER_CONCURRENCY])
    if REMOTION_RENDER_WIDTH:
        args.extend(["--width", REMOTION_RENDER_WIDTH])
    if REMOTION_RENDER_HEIGHT:
        args.extend(["--height", REMOTION_RENDER_HEIGHT])
    return args


def _resolve_ffmpeg_cli(render_dir: Path) -> Optional[str]:
    binary_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    remotion_dir = render_dir / "node_modules" / "@remotion"
    if remotion_dir.is_dir():
        for candidate in sorted(remotion_dir.glob(f"compositor-*/{binary_name}")):
            if candidate.is_file():
                return str(candidate)
    return shutil.which("ffmpeg")


def _build_render_command(
    *,
    render_dir: Path,
    out_path: Path,
    props_path: Path,
    extra_args: Optional[List[str]] = None,
) -> List[str]:
    cmd = [
        *_resolve_remotion_cli(render_dir),
        "render",
        "src/index.tsx",
        "GeneratedVideo",
        str(out_path),
        "--props",
        str(props_path),
        *_build_render_cli_args(),
    ]
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def _run_render(
    *,
    render_dir: Path,
    out_path: Path,
    props_path: Path,
    timeout: int,
    extra_args: Optional[List[str]] = None,
) -> subprocess.CompletedProcess[str]:
    cmd = _build_render_command(
        render_dir=render_dir,
        out_path=out_path,
        props_path=props_path,
        extra_args=extra_args,
    )
    return subprocess.run(
        cmd,
        cwd=str(render_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _run_command(
    command: List[str],
    *,
    cwd: Optional[Path] = None,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _ffmpeg_video_filter(*, width: int, height: int, fps: int) -> str:
    del fps
    return f"scale={width}:{height}"


def _asset_suffix(url: str, default_suffix: str) -> str:
    suffix = Path(urlsplit(url).path).suffix.lower()
    return suffix or default_suffix


def _mime_suffix(mime_type: str | None, default_suffix: str) -> str:
    normalized = str(mime_type or "").strip().lower()
    mapping = {
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
    }
    return mapping.get(normalized, default_suffix)


def _download_asset(url: str, destination: Path) -> None:
    with urlopen(url, timeout=120) as response:
        destination.write_bytes(response.read())


def _materialize_scene_asset(
    *,
    work_dir: Path,
    scene: Dict[str, Any],
    index: int,
    label: str,
    url_key: str,
    bytes_key: str,
    path_key: str,
    default_suffix: str,
    mime_type: str | None = None,
) -> tuple[Optional[Path], Optional[str]]:
    local_path = str(scene.get(path_key) or "").strip()
    if local_path:
        candidate = Path(local_path)
        if candidate.is_file():
            return candidate, "local_path"

    payload = scene.get(bytes_key)
    if isinstance(payload, bytearray):
        payload = bytes(payload)
    if isinstance(payload, bytes) and payload:
        destination = work_dir / f"scene-{index:03d}-{label}{_mime_suffix(mime_type, default_suffix)}"
        destination.write_bytes(payload)
        return destination, "local_bytes"

    asset_url = str(scene.get(url_key) or "").strip()
    if asset_url:
        destination = work_dir / f"scene-{index:03d}-{label}{_asset_suffix(asset_url, default_suffix)}"
        _download_asset(asset_url, destination)
        return destination, "remote_url"

    return None, None


def _write_concat_manifest(manifest_path: Path, segment_paths: List[Path]) -> None:
    lines = []
    for segment in segment_paths:
        normalized = segment.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{normalized}'")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _scenes_from_prompt(prompt: str, duration_seconds: int, image_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """Build a single scene or split into a few scenes for the given duration."""
    return [{"text": prompt, "duration": max(1, duration_seconds), "imageUrl": image_url}]


def render_scenes_to_mp4(
    prompt: str,
    duration_seconds: int,
    user_id: str,
    image_url: Optional[str] = None,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Render a programmatic video (scenes from prompt) to MP4 using the remotion-render package.
    Optionally includes an AI-generated image URL for background.
    Returns (mp4_bytes, asset_id) on success, or (None, None) if render is disabled or fails.
    """
    fps = 30
    duration_in_frames = max(1, duration_seconds * fps)
    props = {
        "scenes": _scenes_from_prompt(prompt, duration_seconds, image_url),
        "fps": fps,
        "durationInFrames": duration_in_frames,
    }
    props_summary = _summarize_props(props)
    clear_last_render_diagnostics()

    if not REMOTION_RENDER_ENABLED:
        logger.debug("Remotion render disabled (REMOTION_RENDER_ENABLED not set)")
        _record_render_diagnostics(
            render_mode="simple",
            status="skipped",
            reason="render_disabled",
            props_summary=props_summary,
            user_id=user_id,
        )
        return None, None

    render_dir = Path(REMOTION_RENDER_DIR)
    if not render_dir.is_dir():
        logger.warning("Remotion render dir not found: %s", render_dir)
        _record_render_diagnostics(
            render_mode="simple",
            status="failed",
            reason="render_dir_missing",
            props_summary=props_summary,
            user_id=user_id,
            render_dir=str(render_dir),
        )
        return None, None

    asset_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as tmp:
        props_path = Path(tmp) / "props.json"
        out_path = Path(tmp) / "out.mp4"
        command = _build_render_command(render_dir=render_dir, out_path=out_path, props_path=props_path)

        try:
            props_path.write_text(json.dumps(props), encoding="utf-8")
            _record_render_diagnostics(
                render_mode="simple",
                status="running",
                reason="render_in_progress",
                command=command,
                timeout_seconds=REMOTION_RENDER_TIMEOUT,
                props_summary=props_summary,
                user_id=user_id,
            )
            result = _run_render(
                render_dir=render_dir,
                out_path=out_path,
                props_path=props_path,
                timeout=REMOTION_RENDER_TIMEOUT,
            )
            if result.returncode != 0:
                logger.warning("Remotion render failed: stdout=%s stderr=%s", result.stdout, result.stderr)
                _record_render_diagnostics(
                    render_mode="simple",
                    status="failed",
                    reason="nonzero_exit",
                    command=command,
                    timeout_seconds=REMOTION_RENDER_TIMEOUT,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    props_summary=props_summary,
                    user_id=user_id,
                )
                return None, None
            if not out_path.is_file():
                logger.warning("Remotion render did not produce output file")
                _record_render_diagnostics(
                    render_mode="simple",
                    status="failed",
                    reason="output_missing",
                    command=command,
                    timeout_seconds=REMOTION_RENDER_TIMEOUT,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    props_summary=props_summary,
                    user_id=user_id,
                )
                return None, None
            mp4_bytes = out_path.read_bytes()
            _record_render_diagnostics(
                render_mode="simple",
                status="success",
                reason="completed",
                command=command,
                timeout_seconds=REMOTION_RENDER_TIMEOUT,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                props_summary=props_summary,
                user_id=user_id,
                output_size_bytes=len(mp4_bytes),
            )
            return mp4_bytes, asset_id
        except subprocess.TimeoutExpired as exc:
            logger.warning("Remotion render timed out after %s seconds", REMOTION_RENDER_TIMEOUT)
            logger.warning("Timeout output: stdout=%s stderr=%s", exc.stdout, exc.stderr)
            _record_render_diagnostics(
                render_mode="simple",
                status="failed",
                reason="timeout",
                command=command,
                timeout_seconds=REMOTION_RENDER_TIMEOUT,
                stdout=exc.stdout,
                stderr=exc.stderr,
                props_summary=props_summary,
                user_id=user_id,
            )
            if REMOTION_RENDER_RETRY_ON_TIMEOUT:
                try:
                    retry_timeout = int(REMOTION_RENDER_TIMEOUT * 1.5)
                    result = _run_render(
                        render_dir=render_dir,
                        out_path=out_path,
                        props_path=props_path,
                        timeout=retry_timeout,
                    )
                    if result.returncode == 0 and out_path.is_file():
                        mp4_bytes = out_path.read_bytes()
                        _record_render_diagnostics(
                            render_mode="simple",
                            status="success",
                            reason="completed_after_retry",
                            command=command,
                            timeout_seconds=retry_timeout,
                            returncode=result.returncode,
                            stdout=result.stdout,
                            stderr=result.stderr,
                            props_summary=props_summary,
                            user_id=user_id,
                            attempt="retry",
                            output_size_bytes=len(mp4_bytes),
                        )
                        return mp4_bytes, asset_id
                    _record_render_diagnostics(
                        render_mode="simple",
                        status="failed",
                        reason="retry_nonzero_exit",
                        command=command,
                        timeout_seconds=retry_timeout,
                        returncode=result.returncode,
                        stdout=result.stdout,
                        stderr=result.stderr,
                        props_summary=props_summary,
                        user_id=user_id,
                        attempt="retry",
                    )
                except Exception as retry_exc:
                    logger.warning("Retry after timeout failed: %s", retry_exc)
                    _record_render_diagnostics(
                        render_mode="simple",
                        status="failed",
                        reason="retry_after_timeout_failed",
                        command=command,
                        timeout_seconds=int(REMOTION_RENDER_TIMEOUT * 1.5),
                        props_summary=props_summary,
                        user_id=user_id,
                        attempt="retry",
                        exception=str(retry_exc),
                    )
            return None, None
        except FileNotFoundError:
            logger.warning("npx/remotion not found; is Node installed and remotion-render deps installed?")
            _record_render_diagnostics(
                render_mode="simple",
                status="failed",
                reason="cli_not_found",
                command=command,
                timeout_seconds=REMOTION_RENDER_TIMEOUT,
                props_summary=props_summary,
                user_id=user_id,
            )
            return None, None
        except Exception as exc:
            logger.warning("Remotion render error: %s", exc)
            _record_render_diagnostics(
                render_mode="simple",
                status="failed",
                reason="exception",
                command=command,
                timeout_seconds=REMOTION_RENDER_TIMEOUT,
                props_summary=props_summary,
                user_id=user_id,
                exception=str(exc),
            )
            return None, None


def _render_scene_segment(
    *,
    ffmpeg_cli: str,
    work_dir: Path,
    scene: Dict[str, Any],
    index: int,
    fps: int,
    width: int,
    height: int,
) -> tuple[Path, Dict[str, str]]:
    duration = max(1, int(scene.get("duration") or 4))
    source_path, source_origin = _materialize_scene_asset(
        work_dir=work_dir,
        scene=scene,
        index=index,
        label="source",
        url_key="videoUrl" if scene.get("videoUrl") else "imageUrl",
        bytes_key="videoBytes" if scene.get("videoUrl") or scene.get("videoBytes") else "imageBytes",
        path_key="videoPath" if scene.get("videoUrl") or scene.get("videoBytes") else "imagePath",
        default_suffix=".mp4" if scene.get("videoUrl") or scene.get("videoBytes") else ".png",
        mime_type="video/mp4" if scene.get("videoUrl") or scene.get("videoBytes") else "image/png",
    )
    if source_path is None:
        raise ValueError(f"Scene {index} is missing both video and image assets")

    audio_path, audio_origin = _materialize_scene_asset(
        work_dir=work_dir,
        scene=scene,
        index=index,
        label="audio",
        url_key="voiceoverUrl",
        bytes_key="voiceoverBytes",
        path_key="voiceoverPath",
        default_suffix=".mp3",
        mime_type=scene.get("voiceoverMimeType"),
    )

    segment_path = work_dir / f"scene-{index:03d}.mp4"
    command: List[str] = [ffmpeg_cli, "-y"]
    if str(scene.get("videoUrl") or "").strip() or scene.get("videoBytes"):
        command.extend(["-stream_loop", "-1", "-i", str(source_path)])
    else:
        command.extend(["-loop", "1", "-i", str(source_path)])
    if audio_path is not None:
        command.extend(["-i", str(audio_path)])
    else:
        command.extend(["-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate={FFMPEG_RENDER_SAMPLE_RATE}"])
    command.extend(
        [
            "-t",
            str(duration),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-vf",
            _ffmpeg_video_filter(width=width, height=height, fps=fps),
            "-r",
            str(fps),
            "-af",
            f"apad=pad_dur={duration},atrim=0:{duration}",
            "-c:v",
            "libx264",
            "-preset",
            FFMPEG_RENDER_PRESET,
            "-crf",
            str(FFMPEG_RENDER_CRF),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            FFMPEG_RENDER_AUDIO_BITRATE,
            "-ar",
            str(FFMPEG_RENDER_SAMPLE_RATE),
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(segment_path),
        ]
    )
    result = _run_command(command, timeout=FFMPEG_RENDER_TIMEOUT)
    if result.returncode != 0 or not segment_path.is_file():
        raise RuntimeError(result.stderr or result.stdout or f"Scene {index} ffmpeg render failed")
    return segment_path, {
        "source_origin": source_origin or "missing",
        "audio_origin": audio_origin or "missing",
    }



def render_programmatic_video_ffmpeg(
    props: Dict[str, Any],
    user_id: str,
) -> Tuple[Optional[bytes], Optional[str]]:
    """Render a long-form video by turning scenes into normalized MP4 segments and concatenating them."""
    props_summary = _summarize_props(props)
    clear_last_render_diagnostics()

    render_dir = Path(REMOTION_RENDER_DIR)
    ffmpeg_cli = _resolve_ffmpeg_cli(render_dir)
    if not ffmpeg_cli:
        _record_render_diagnostics(
            render_mode="ffmpeg_concat",
            status="failed",
            reason="ffmpeg_not_found",
            props_summary=props_summary,
            user_id=user_id,
            renderer="ffmpeg",
        )
        return None, None

    scenes = props.get("scenes") if isinstance(props.get("scenes"), list) else []
    if not scenes:
        _record_render_diagnostics(
            render_mode="ffmpeg_concat",
            status="failed",
            reason="no_scenes",
            props_summary=props_summary,
            user_id=user_id,
            renderer="ffmpeg",
        )
        return None, None

    asset_id = str(uuid.uuid4())
    fps = max(1, int(props.get("fps") or 24))
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        out_path = work_dir / "out.mp4"
        concat_path = work_dir / "concat.txt"
        _record_render_diagnostics(
            render_mode="ffmpeg_concat",
            status="running",
            reason="segment_render_in_progress",
            command=[ffmpeg_cli],
            timeout_seconds=FFMPEG_RENDER_TIMEOUT,
            props_summary=props_summary,
            user_id=user_id,
            renderer="ffmpeg",
        )
        try:
            segment_results = [
                _render_scene_segment(
                    ffmpeg_cli=ffmpeg_cli,
                    work_dir=work_dir,
                    scene=scene,
                    index=index,
                    fps=fps,
                    width=FFMPEG_RENDER_WIDTH,
                    height=FFMPEG_RENDER_HEIGHT,
                )
                for index, scene in enumerate(scenes)
            ]
            segment_paths = [segment_path for segment_path, _origins in segment_results]
            local_scene_source_count = sum(1 for _segment_path, origins in segment_results if origins.get("source_origin") in {"local_bytes", "local_path"})
            remote_scene_source_count = sum(1 for _segment_path, origins in segment_results if origins.get("source_origin") == "remote_url")
            local_audio_source_count = sum(1 for _segment_path, origins in segment_results if origins.get("audio_origin") in {"local_bytes", "local_path"})
            remote_audio_source_count = sum(1 for _segment_path, origins in segment_results if origins.get("audio_origin") == "remote_url")
            _write_concat_manifest(concat_path, segment_paths)
            concat_command = [
                ffmpeg_cli,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(out_path),
            ]
            result = _run_command(concat_command, timeout=FFMPEG_RENDER_TIMEOUT)
            if result.returncode != 0 or not out_path.is_file():
                concat_command = [
                    ffmpeg_cli,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_path),
                    "-c:v",
                    "libx264",
                    "-preset",
                    FFMPEG_RENDER_PRESET,
                    "-crf",
                    str(FFMPEG_RENDER_CRF),
                    "-c:a",
                    "aac",
                    "-b:a",
                    FFMPEG_RENDER_AUDIO_BITRATE,
                    "-movflags",
                    "+faststart",
                    str(out_path),
                ]
                result = _run_command(concat_command, timeout=FFMPEG_RENDER_TIMEOUT)
            if result.returncode != 0 or not out_path.is_file():
                _record_render_diagnostics(
                    render_mode="ffmpeg_concat",
                    status="failed",
                    reason="concat_failed",
                    command=concat_command,
                    timeout_seconds=FFMPEG_RENDER_TIMEOUT,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    props_summary=props_summary,
                    user_id=user_id,
                    renderer="ffmpeg",
                    bg_music_omitted=bool(props.get("bgMusicUrl")),
                    local_scene_source_count=local_scene_source_count,
                    remote_scene_source_count=remote_scene_source_count,
                    local_audio_source_count=local_audio_source_count,
                    remote_audio_source_count=remote_audio_source_count,
                )
                return None, None
            mp4_bytes = out_path.read_bytes()
            _record_render_diagnostics(
                render_mode="ffmpeg_concat",
                status="success",
                reason="completed",
                command=concat_command,
                timeout_seconds=FFMPEG_RENDER_TIMEOUT,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                props_summary=props_summary,
                user_id=user_id,
                output_size_bytes=len(mp4_bytes),
                renderer="ffmpeg",
                bg_music_omitted=bool(props.get("bgMusicUrl")),
                local_scene_source_count=local_scene_source_count,
                remote_scene_source_count=remote_scene_source_count,
                local_audio_source_count=local_audio_source_count,
                remote_audio_source_count=remote_audio_source_count,
            )
            return mp4_bytes, asset_id
        except subprocess.TimeoutExpired as exc:
            _record_render_diagnostics(
                render_mode="ffmpeg_concat",
                status="failed",
                reason="timeout",
                command=[ffmpeg_cli],
                timeout_seconds=FFMPEG_RENDER_TIMEOUT,
                stdout=exc.stdout,
                stderr=exc.stderr,
                props_summary=props_summary,
                user_id=user_id,
                renderer="ffmpeg",
            )
            return None, None
        except Exception as exc:
            _record_render_diagnostics(
                render_mode="ffmpeg_concat",
                status="failed",
                reason="exception",
                command=[ffmpeg_cli],
                timeout_seconds=FFMPEG_RENDER_TIMEOUT,
                props_summary=props_summary,
                user_id=user_id,
                renderer="ffmpeg",
                exception=str(exc),
            )
            return None, None


def render_programmatic_video(
    props: Dict[str, Any],
    user_id: str,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Render a complex video using arbitrary props (for DirectorService).
    Expects props to match GeneratedVideoInputProps interface (scenes, fps, bgMusicUrl).
    Returns (mp4_bytes, asset_id).
    """
    props_summary = _summarize_props(props)
    clear_last_render_diagnostics()

    if not REMOTION_RENDER_ENABLED:
        logger.debug("Remotion render disabled (REMOTION_RENDER_ENABLED not set)")
        _record_render_diagnostics(
            render_mode="programmatic",
            status="skipped",
            reason="render_disabled",
            props_summary=props_summary,
            user_id=user_id,
        )
        return None, None

    render_dir = Path(REMOTION_RENDER_DIR)
    if not render_dir.is_dir():
        logger.warning("Remotion render dir not found: %s", render_dir)
        _record_render_diagnostics(
            render_mode="programmatic",
            status="failed",
            reason="render_dir_missing",
            props_summary=props_summary,
            user_id=user_id,
            render_dir=str(render_dir),
        )
        return None, None

    asset_id = str(uuid.uuid4())
    extra_args = ["--gl=angle"]
    with tempfile.TemporaryDirectory() as tmp:
        props_path = Path(tmp) / "props.json"
        out_path = Path(tmp) / "out.mp4"
        timeout = REMOTION_RENDER_TIMEOUT * 3
        command = _build_render_command(
            render_dir=render_dir,
            out_path=out_path,
            props_path=props_path,
            extra_args=extra_args,
        )

        try:
            props_path.write_text(json.dumps(props), encoding="utf-8")
            _record_render_diagnostics(
                render_mode="programmatic",
                status="running",
                reason="render_in_progress",
                command=command,
                timeout_seconds=timeout,
                props_summary=props_summary,
                user_id=user_id,
            )
            result = _run_render(
                render_dir=render_dir,
                out_path=out_path,
                props_path=props_path,
                timeout=timeout,
                extra_args=extra_args,
            )
            if result.returncode != 0:
                logger.warning("Remotion render failed: stdout=%s stderr=%s", result.stdout, result.stderr)
                if "EACCES" in (result.stderr or ""):
                    logger.error("Permission error running remotion CLI")
                _record_render_diagnostics(
                    render_mode="programmatic",
                    status="failed",
                    reason="nonzero_exit",
                    command=command,
                    timeout_seconds=timeout,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    props_summary=props_summary,
                    user_id=user_id,
                )
                return None, None
            if not out_path.is_file():
                logger.warning("Remotion render did not produce output file")
                _record_render_diagnostics(
                    render_mode="programmatic",
                    status="failed",
                    reason="output_missing",
                    command=command,
                    timeout_seconds=timeout,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    props_summary=props_summary,
                    user_id=user_id,
                )
                return None, None
            mp4_bytes = out_path.read_bytes()
            _record_render_diagnostics(
                render_mode="programmatic",
                status="success",
                reason="completed",
                command=command,
                timeout_seconds=timeout,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                props_summary=props_summary,
                user_id=user_id,
                output_size_bytes=len(mp4_bytes),
            )
            return mp4_bytes, asset_id
        except subprocess.TimeoutExpired as exc:
            logger.warning("Remotion render timed out after %s seconds", timeout)
            _record_render_diagnostics(
                render_mode="programmatic",
                status="failed",
                reason="timeout",
                command=command,
                timeout_seconds=timeout,
                stdout=exc.stdout,
                stderr=exc.stderr,
                props_summary=props_summary,
                user_id=user_id,
            )
            if REMOTION_RENDER_RETRY_ON_TIMEOUT:
                try:
                    retry_timeout = int(timeout * 1.5)
                    result = _run_render(
                        render_dir=render_dir,
                        out_path=out_path,
                        props_path=props_path,
                        timeout=retry_timeout,
                        extra_args=extra_args,
                    )
                    if result.returncode == 0 and out_path.is_file():
                        mp4_bytes = out_path.read_bytes()
                        _record_render_diagnostics(
                            render_mode="programmatic",
                            status="success",
                            reason="completed_after_retry",
                            command=command,
                            timeout_seconds=retry_timeout,
                            returncode=result.returncode,
                            stdout=result.stdout,
                            stderr=result.stderr,
                            props_summary=props_summary,
                            user_id=user_id,
                            attempt="retry",
                            output_size_bytes=len(mp4_bytes),
                        )
                        return mp4_bytes, asset_id
                    _record_render_diagnostics(
                        render_mode="programmatic",
                        status="failed",
                        reason="retry_nonzero_exit",
                        command=command,
                        timeout_seconds=retry_timeout,
                        returncode=result.returncode,
                        stdout=result.stdout,
                        stderr=result.stderr,
                        props_summary=props_summary,
                        user_id=user_id,
                        attempt="retry",
                    )
                except Exception as retry_exc:
                    logger.warning("Retry after timeout failed: %s", retry_exc)
                    _record_render_diagnostics(
                        render_mode="programmatic",
                        status="failed",
                        reason="retry_after_timeout_failed",
                        command=command,
                        timeout_seconds=int(timeout * 1.5),
                        props_summary=props_summary,
                        user_id=user_id,
                        attempt="retry",
                        exception=str(retry_exc),
                    )
            return None, None
        except FileNotFoundError:
            logger.warning("npx/remotion not found; is Node installed and remotion-render deps installed?")
            _record_render_diagnostics(
                render_mode="programmatic",
                status="failed",
                reason="cli_not_found",
                command=command,
                timeout_seconds=timeout,
                props_summary=props_summary,
                user_id=user_id,
            )
            return None, None
        except Exception as exc:
            logger.warning("Remotion render error: %s", exc)
            _record_render_diagnostics(
                render_mode="programmatic",
                status="failed",
                reason="exception",
                command=command,
                timeout_seconds=timeout,
                props_summary=props_summary,
                user_id=user_id,
                exception=str(exc),
            )
            return None, None
