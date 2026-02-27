# Copyright 2025 Pikar AI
# Server-side Remotion render: produce MP4 from scenes (text + duration) and upload to vault.
# Optional: set REMOTION_RENDER_ENABLED=1 and ensure remotion-render package is installed.

import json
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Path to remotion-render package (repo root / remotion-render)
REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTION_RENDER_DIR = os.getenv("REMOTION_RENDER_DIR", str(REPO_ROOT / "remotion-render"))
REMOTION_RENDER_ENABLED = os.getenv("REMOTION_RENDER_ENABLED", "").strip().lower() in ("1", "true", "yes")
REMOTION_RENDER_TIMEOUT = int(os.getenv("REMOTION_RENDER_TIMEOUT", "120"))  # seconds
REMOTION_RENDER_RETRY_ON_TIMEOUT = os.getenv("REMOTION_RENDER_RETRY_ON_TIMEOUT", "1").strip().lower() in ("1", "true", "yes")


def _resolve_remotion_cli(render_dir: Path) -> List[str]:
    """Prefer local CLI for lower cold-start overhead; fallback to npx."""
    cli_name = "remotion.cmd" if os.name == "nt" else "remotion"
    local_cli = render_dir / "node_modules" / ".bin" / cli_name
    if local_cli.is_file():
        return [str(local_cli)]
    return ["npx", "remotion"]


def _run_render(
    *,
    render_dir: Path,
    out_path: Path,
    props_path: Path,
    timeout: int,
    extra_args: Optional[List[str]] = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        *_resolve_remotion_cli(render_dir),
        "render",
        "src/index.tsx",
        "GeneratedVideo",
        str(out_path),
        "--props",
        str(props_path),
    ]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd,
        cwd=str(render_dir),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _scenes_from_prompt(prompt: str, duration_seconds: int, image_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """Build a single scene or split into a few scenes for the given duration."""
    # Single scene with the full prompt and requested duration + optional image
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
    if not REMOTION_RENDER_ENABLED:
        logger.debug("Remotion render disabled (REMOTION_RENDER_ENABLED not set)")
        return None, None

    render_dir = Path(REMOTION_RENDER_DIR)
    if not render_dir.is_dir():
        logger.warning("Remotion render dir not found: %s", render_dir)
        return None, None

    fps = 30
    duration_in_frames = max(1, duration_seconds * fps)
    scenes = _scenes_from_prompt(prompt, duration_seconds, image_url)

    props = {
        "scenes": scenes,
        "fps": fps,
        "durationInFrames": duration_in_frames,
    }

    asset_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as tmp:
        props_path = Path(tmp) / "props.json"
        out_path = Path(tmp) / "out.mp4"
        props_path.write_text(json.dumps(props), encoding="utf-8")

        try:
            result = _run_render(
                render_dir=render_dir,
                out_path=out_path,
                props_path=props_path,
                timeout=REMOTION_RENDER_TIMEOUT,
            )
            if result.returncode != 0:
                logger.warning(
                    "Remotion render failed: stdout=%s stderr=%s",
                    result.stdout,
                    result.stderr,
                )
                return None, None
            if not out_path.is_file():
                logger.warning("Remotion render did not produce output file")
                return None, None
            mp4_bytes = out_path.read_bytes()
            return mp4_bytes, asset_id
        except subprocess.TimeoutExpired as e:
            logger.warning("Remotion render timed out after %s seconds", REMOTION_RENDER_TIMEOUT)
            logger.warning("Timeout output: stdout=%s stderr=%s", e.stdout, e.stderr)
            if REMOTION_RENDER_RETRY_ON_TIMEOUT:
                try:
                    result = _run_render(
                        render_dir=render_dir,
                        out_path=out_path,
                        props_path=props_path,
                        timeout=int(REMOTION_RENDER_TIMEOUT * 1.5),
                    )
                    if result.returncode == 0 and out_path.is_file():
                        return out_path.read_bytes(), asset_id
                except Exception as retry_exc:
                    logger.warning("Retry after timeout failed: %s", retry_exc)
            return None, None
        except FileNotFoundError:
            logger.warning("npx/remotion not found; is Node installed and remotion-render deps installed?")
            return None, None
        except Exception as e:
            logger.warning("Remotion render error: %s", e)
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
    if not REMOTION_RENDER_ENABLED:
        logger.debug("Remotion render disabled (REMOTION_RENDER_ENABLED not set)")
        return None, None

    render_dir = Path(REMOTION_RENDER_DIR)
    if not render_dir.is_dir():
        logger.warning("Remotion render dir not found: %s", render_dir)
        return None, None

    asset_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as tmp:
        props_path = Path(tmp) / "props.json"
        out_path = Path(tmp) / "out.mp4"
        props_path.write_text(json.dumps(props), encoding="utf-8")

        try:
            # Increase timeout for complex renders (videos/assets take longer to load/process)
            timeout = REMOTION_RENDER_TIMEOUT * 3 
            result = _run_render(
                render_dir=render_dir,
                out_path=out_path,
                props_path=props_path,
                timeout=timeout,
                extra_args=["--gl=angle"],  # Force software rendering if GPU fails in container
            )
            if result.returncode != 0:
                logger.warning(
                    "Remotion render failed: stdout=%s stderr=%s",
                    result.stdout,
                    result.stderr,
                )
                if "EACCES" in result.stderr:
                    logger.error("Permission error running remotion CLI")
                return None, None
            if not out_path.is_file():
                logger.warning("Remotion render did not produce output file")
                return None, None
            mp4_bytes = out_path.read_bytes()
            return mp4_bytes, asset_id
        except subprocess.TimeoutExpired as e:
            logger.warning("Remotion render timed out after %s seconds", timeout)
            # logger.warning("Timeout output: stdout=%s stderr=%s", e.stdout, e.stderr)
            if REMOTION_RENDER_RETRY_ON_TIMEOUT:
                try:
                    result = _run_render(
                        render_dir=render_dir,
                        out_path=out_path,
                        props_path=props_path,
                        timeout=int(timeout * 1.5),
                        extra_args=["--gl=angle"],
                    )
                    if result.returncode == 0 and out_path.is_file():
                        return out_path.read_bytes(), asset_id
                except Exception as retry_exc:
                    logger.warning("Retry after timeout failed: %s", retry_exc)
            return None, None
        except Exception as e:
            logger.warning("Remotion render error: %s", e)
            return None, None
