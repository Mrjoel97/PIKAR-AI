from pathlib import Path

from app.services import video_readiness


def _fixture_dir() -> Path:
    path = Path(__file__).resolve().parent / "_tmp_video_readiness"
    path.mkdir(exist_ok=True)
    return path


def test_video_readiness_accepts_vertex_mode_without_api_key(monkeypatch):
    tmp_path = _fixture_dir()
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "1")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "pikar-ai-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    monkeypatch.setenv("REMOTION_RENDER_ENABLED", "1")
    monkeypatch.setenv("REMOTION_RENDER_DIR", str(tmp_path))
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    # Reload module-level env-derived flags.
    video_readiness.REMOTION_RENDER_DIR = str(tmp_path)
    video_readiness.REMOTION_RENDER_ENABLED = True

    report = video_readiness.get_video_readiness()

    assert report["veo_configured"] is True
    assert report["remotion_configured"] is True
    assert report["details"]["veo"]["GOOGLE_API_KEY_set"] is False
    assert report["details"]["veo"]["vertexai_configured"] is True


def test_video_readiness_requires_project_for_vertex_mode(monkeypatch):
    tmp_path = _fixture_dir()
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "1")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.setenv("REMOTION_RENDER_ENABLED", "0")
    monkeypatch.setenv("REMOTION_RENDER_DIR", str(tmp_path))

    video_readiness.REMOTION_RENDER_DIR = str(tmp_path)
    video_readiness.REMOTION_RENDER_ENABLED = False

    report = video_readiness.get_video_readiness()

    assert report["veo_configured"] is False
    assert report["details"]["veo"]["vertexai_configured"] is False
