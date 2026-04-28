import importlib
from pathlib import Path
from unittest.mock import patch


def test_build_render_cli_args_reads_env(monkeypatch):
    monkeypatch.setenv("REMOTION_RENDER_SCALE", "0.5")
    monkeypatch.setenv("REMOTION_RENDER_CONCURRENCY", "4")
    monkeypatch.setenv("REMOTION_RENDER_WIDTH", "1280")
    monkeypatch.setenv("REMOTION_RENDER_HEIGHT", "720")
    monkeypatch.delenv("REMOTION_BROWSER_EXECUTABLE", raising=False)

    import app.services.remotion_render_service as remotion_render_service

    remotion_render_service = importlib.reload(remotion_render_service)

    args = remotion_render_service._build_render_cli_args()
    # On Windows with Chrome installed, --browser-executable may be prepended
    browser_args = []
    if "--browser-executable" in args:
        idx = args.index("--browser-executable")
        browser_args = args[idx : idx + 2]
        args = args[:idx] + args[idx + 2 :]

    assert args == [
        "--scale",
        "0.5",
        "--concurrency",
        "4",
        "--width",
        "1280",
        "--height",
        "720",
    ]
    if browser_args:
        assert browser_args[0] == "--browser-executable"
        assert browser_args[1]  # non-empty path


def test_run_render_uses_utf8_safe_capture(monkeypatch):
    for key in (
        "REMOTION_RENDER_SCALE",
        "REMOTION_RENDER_CONCURRENCY",
        "REMOTION_RENDER_WIDTH",
        "REMOTION_RENDER_HEIGHT",
        "REMOTION_BROWSER_EXECUTABLE",
    ):
        monkeypatch.delenv(key, raising=False)

    import app.services.remotion_render_service as remotion_render_service

    remotion_render_service = importlib.reload(remotion_render_service)

    with (
        patch.object(
            remotion_render_service, "_resolve_remotion_cli", return_value=["remotion"]
        ),
        patch.object(
            remotion_render_service, "_resolve_browser_executable", return_value=None
        ),
        patch(
            "app.services.remotion_render_service.subprocess.run",
            return_value="ok",
        ) as run_mock,
    ):
        result = remotion_render_service._run_render(
            render_dir=Path("render-dir"),
            out_path=Path("out.mp4"),
            props_path=Path("props.json"),
            timeout=123,
            extra_args=["--gl=angle"],
        )

    assert result == "ok"
    assert run_mock.call_args.args[0] == [
        "remotion",
        "render",
        "src/index.tsx",
        "GeneratedVideo",
        "out.mp4",
        "--props",
        "props.json",
        "--gl=angle",
    ]
    assert run_mock.call_args.kwargs["encoding"] == "utf-8"
    assert run_mock.call_args.kwargs["errors"] == "replace"


def test_last_render_diagnostics_round_trip(monkeypatch):
    for key in (
        "REMOTION_RENDER_SCALE",
        "REMOTION_RENDER_CONCURRENCY",
        "REMOTION_RENDER_WIDTH",
        "REMOTION_RENDER_HEIGHT",
    ):
        monkeypatch.delenv(key, raising=False)

    import app.services.remotion_render_service as remotion_render_service

    remotion_render_service = importlib.reload(remotion_render_service)
    remotion_render_service.clear_last_render_diagnostics()
    remotion_render_service._record_render_diagnostics(
        render_mode="programmatic",
        status="failed",
        reason="timeout",
        command=["remotion", "render"],
        stderr="stderr sample",
        props_summary={"scene_count": 3},
    )

    diagnostics = remotion_render_service.get_last_render_diagnostics()

    assert diagnostics is not None
    assert diagnostics["reason"] == "timeout"
    assert diagnostics["stderr"] == "stderr sample"
    assert diagnostics["props_summary"]["scene_count"] == 3


def test_resolve_ffmpeg_cli_prefers_bundled_binary():
    import app.services.remotion_render_service as remotion_render_service

    remotion_render_service = importlib.reload(remotion_render_service)
    render_dir = Path("render-dir")
    ffmpeg_path = (
        render_dir
        / "node_modules"
        / "@remotion"
        / "compositor-win32-x64-msvc"
        / "ffmpeg.exe"
    )

    with (
        patch.object(Path, "is_dir", return_value=True),
        patch.object(
            Path,
            "glob",
            return_value=[ffmpeg_path],
        ),
        patch.object(Path, "is_file", return_value=True),
        patch(
            "app.services.remotion_render_service.shutil.which",
            return_value=None,
        ),
    ):
        resolved = remotion_render_service._resolve_ffmpeg_cli(render_dir)

    assert resolved == str(ffmpeg_path)


def test_materialize_scene_asset_prefers_local_bytes():
    import app.services.remotion_render_service as remotion_render_service

    remotion_render_service = importlib.reload(remotion_render_service)
    scene = {
        "imageBytes": b"image-bytes",
        "imageUrl": "https://example.com/scene.png",
    }
    captured = {}

    def _capture_write_bytes(self, payload):
        captured["path"] = self
        captured["payload"] = payload
        return len(payload)

    with (
        patch("app.services.remotion_render_service._download_asset") as download_mock,
        patch.object(
            Path,
            "write_bytes",
            _capture_write_bytes,
        ),
    ):
        asset_path, origin = remotion_render_service._materialize_scene_asset(
            work_dir=Path("render-dir"),
            scene=scene,
            index=0,
            label="source",
            url_key="imageUrl",
            bytes_key="imageBytes",
            path_key="imagePath",
            default_suffix=".png",
            mime_type="image/png",
        )

    assert asset_path is not None
    assert asset_path.name == "scene-000-source.png"
    assert captured["payload"] == b"image-bytes"
    assert origin == "local_bytes"
    download_mock.assert_not_called()
