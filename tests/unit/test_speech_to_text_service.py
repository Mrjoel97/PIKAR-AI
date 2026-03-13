import sys
import types

from app.services import speech_to_text_service


class _FakeRecognitionConfig:
    class AudioEncoding:
        LINEAR16 = "LINEAR16"
        MP3 = "MP3"
        OGG_OPUS = "OGG_OPUS"
        WEBM_OPUS = "WEBM_OPUS"

    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _FakeRecognitionAudio:
    def __init__(self, *, content: bytes):
        self.content = content


class _FakeAlternative:
    def __init__(self, transcript: str, confidence: float = 0.9):
        self.transcript = transcript
        self.confidence = confidence


class _FakeResult:
    def __init__(self, transcript: str, confidence: float = 0.9):
        self.alternatives = [_FakeAlternative(transcript, confidence)]


class _FakeResponse:
    def __init__(self, *transcripts: str):
        self.results = [_FakeResult(t) for t in transcripts]


class _FakeSpeechClient:
    def __init__(self, response: _FakeResponse, seen: dict):
        self._response = response
        self._seen = seen

    def recognize(self, *, config, audio):
        self._seen["config"] = config.kwargs
        self._seen["audio"] = audio.content
        return self._response


def _install_fake_speech(monkeypatch, response: _FakeResponse, seen: dict):
    google_cloud = types.ModuleType("google.cloud")
    speech_v1 = types.ModuleType("google.cloud.speech_v1")
    speech_v1.RecognitionConfig = _FakeRecognitionConfig
    speech_v1.RecognitionAudio = _FakeRecognitionAudio
    speech_v1.SpeechClient = lambda: _FakeSpeechClient(response, seen)
    google_cloud.speech_v1 = speech_v1
    monkeypatch.setitem(sys.modules, "google.cloud", google_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.speech_v1", speech_v1)


def test_transcribe_audio_falls_back_to_rest_when_client_package_missing(monkeypatch):
    google_cloud = types.ModuleType("google.cloud")
    monkeypatch.setitem(sys.modules, "google.cloud", google_cloud)
    monkeypatch.delitem(sys.modules, "google.cloud.speech_v1", raising=False)
    monkeypatch.setattr(
        speech_to_text_service,
        "_transcribe_via_rest",
        lambda *args, **kwargs: {"success": True, "transcript": "rest fallback", "confidence": 0.8, "error": None},
    )

    result = speech_to_text_service.transcribe_audio(b"abc")

    assert result["success"] is True
    assert result["transcript"] == "rest fallback"


def test_transcribe_audio_uses_linear16_for_pcm(monkeypatch):
    seen = {}
    _install_fake_speech(monkeypatch, _FakeResponse("hello world"), seen)

    result = speech_to_text_service.transcribe_audio(
        b"pcm-bytes",
        sample_rate_hz=16000,
        language_code="en-US",
        mime_type="audio/pcm",
    )

    assert result["success"] is True
    assert result["transcript"] == "hello world"
    assert seen["audio"] == b"pcm-bytes"
    assert seen["config"]["encoding"] == _FakeRecognitionConfig.AudioEncoding.LINEAR16
    assert seen["config"]["sample_rate_hertz"] == 16000
    assert seen["config"]["language_code"] == "en-US"


def test_transcribe_audio_uses_mp3_encoding_when_requested(monkeypatch):
    seen = {}
    _install_fake_speech(monkeypatch, _FakeResponse("voiceover smoke test"), seen)

    result = speech_to_text_service.transcribe_audio(
        b"mp3-bytes",
        mime_type="audio/mpeg",
    )

    assert result["success"] is True
    assert result["transcript"] == "voiceover smoke test"
    assert seen["config"]["encoding"] == _FakeRecognitionConfig.AudioEncoding.MP3
    assert "sample_rate_hertz" not in seen["config"]


def test_transcribe_audio_uses_webm_opus_for_browser_recordings(monkeypatch):
    seen = {}
    _install_fake_speech(monkeypatch, _FakeResponse("browser mic transcript"), seen)

    result = speech_to_text_service.transcribe_audio(
        b"webm-bytes",
        mime_type="audio/webm;codecs=opus",
    )

    assert result["success"] is True
    assert result["transcript"] == "browser mic transcript"
    assert seen["config"]["encoding"] == _FakeRecognitionConfig.AudioEncoding.WEBM_OPUS
    assert "sample_rate_hertz" not in seen["config"]
