"""Speech-to-text service with graceful fallback.

Primary path uses Google Cloud Speech-to-Text when available/configured.
If the client library is unavailable, the service falls back to the REST API
using the project's existing Google credentials.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

_MP3_MIME_TYPES = {"audio/mpeg", "audio/mp3"}
_OGG_MIME_TYPES = {"audio/ogg"}
_WEBM_MIME_TYPES = {"audio/webm"}
_LINEAR16_MIME_TYPES = {
    "audio/pcm",
    "audio/l16",
    "audio/raw",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
}
_SPEECH_SCOPE = ["https://www.googleapis.com/auth/cloud-platform"]
_SPEECH_RECOGNIZE_URL = "https://speech.googleapis.com/v1/speech:recognize"


def _normalize_mime_type(mime_type: str) -> str:
    return (mime_type or "audio/pcm").split(";", 1)[0].strip().lower()


def _rest_encoding_for_mime_type(mime_type: str) -> str:
    normalized_mime = _normalize_mime_type(mime_type)
    if normalized_mime in _MP3_MIME_TYPES:
        return "MP3"
    if normalized_mime in _OGG_MIME_TYPES:
        return "OGG_OPUS"
    if normalized_mime in _WEBM_MIME_TYPES:
        return "WEBM_OPUS"
    return "LINEAR16"


def _normalize_result_payload(results: list[Any]) -> dict[str, Any]:
    transcripts: list[str] = []
    confidences: list[float] = []
    for result in results or []:
        alternatives = getattr(result, "alternatives", None)
        if alternatives is None and isinstance(result, dict):
            alternatives = result.get("alternatives")
        if not alternatives:
            continue
        best = alternatives[0]
        text = (
            getattr(best, "transcript", None)
            if not isinstance(best, dict)
            else best.get("transcript")
        ) or ""
        text = str(text).strip()
        if text:
            transcripts.append(text)
        confidence = (
            getattr(best, "confidence", None)
            if not isinstance(best, dict)
            else best.get("confidence")
        )
        if confidence is not None:
            try:
                confidences.append(float(confidence))
            except Exception:
                pass

    transcript = " ".join(part for part in transcripts if part).strip()
    if not transcript:
        return {
            "success": False,
            "transcript": None,
            "confidence": None,
            "error": "No speech detected",
        }

    avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else None
    return {
        "success": True,
        "transcript": transcript,
        "confidence": avg_confidence,
        "error": None,
    }


def _load_google_access_token() -> str:
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    max_attempts = max(1, int(os.getenv("GOOGLE_SPEECH_AUTH_RETRIES", "3")))
    base_delay = float(os.getenv("GOOGLE_SPEECH_AUTH_RETRY_DELAY_SECONDS", "1.0"))
    last_exc: Exception | None = None

    for attempt in range(max_attempts):
        try:
            if credentials_path:
                from google.auth.transport.requests import Request
                from google.oauth2 import service_account

                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=_SPEECH_SCOPE,
                )
            else:
                import google.auth
                from google.auth.transport.requests import Request

                credentials, _project_id = google.auth.default(scopes=_SPEECH_SCOPE)

            credentials.refresh(Request())
            if not credentials.token:
                raise RuntimeError("No access token returned by Google credentials")
            return credentials.token
        except Exception as exc:  # pragma: no cover - depends on external auth state
            last_exc = exc
            if attempt < max_attempts - 1:
                time.sleep(base_delay * (attempt + 1))
                continue
            raise RuntimeError(f"Failed to load Google auth token: {exc}") from exc

    raise RuntimeError(f"Failed to load Google auth token: {last_exc}")


def _build_rest_config(*, sample_rate_hz: int, language_code: str, mime_type: str) -> dict[str, Any]:
    normalized_mime = _normalize_mime_type(mime_type)
    config: dict[str, Any] = {
        "languageCode": language_code,
        "enableAutomaticPunctuation": True,
        "encoding": _rest_encoding_for_mime_type(normalized_mime),
    }
    model_name = os.getenv("GOOGLE_SPEECH_MODEL", "latest_short").strip()
    if model_name:
        config["model"] = model_name

    if normalized_mime in _LINEAR16_MIME_TYPES:
        config["sampleRateHertz"] = int(sample_rate_hz)
    return config


def _transcribe_via_rest(
    audio_bytes: bytes,
    *,
    sample_rate_hz: int,
    language_code: str,
    mime_type: str,
) -> dict[str, Any]:
    max_attempts = max(1, int(os.getenv("GOOGLE_SPEECH_HTTP_RETRIES", "2")))
    base_delay = float(os.getenv("GOOGLE_SPEECH_HTTP_RETRY_DELAY_SECONDS", "1.0"))
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        token = _load_google_access_token()
        try:
            response = requests.post(
                _SPEECH_RECOGNIZE_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "config": _build_rest_config(
                        sample_rate_hz=sample_rate_hz,
                        language_code=language_code,
                        mime_type=mime_type,
                    ),
                    "audio": {"content": base64.b64encode(audio_bytes).decode("ascii")},
                },
                timeout=45,
            )
            payload = response.json() if response.content else {}
            if not response.ok:
                error_payload = payload.get("error") if isinstance(payload, dict) else None
                error_message = (
                    (error_payload or {}).get("message")
                    if isinstance(error_payload, dict)
                    else None
                )
                return {
                    "success": False,
                    "transcript": None,
                    "confidence": None,
                    "error": error_message or f"HTTP {response.status_code}",
                }
            return _normalize_result_payload(
                payload.get("results") if isinstance(payload, dict) else []
            )
        except requests.RequestException as exc:
            last_error = exc
            if attempt < max_attempts - 1:
                time.sleep(base_delay * (attempt + 1))
                continue
            raise

    raise RuntimeError(f"Speech-to-Text REST request failed: {last_error}")


def _client_encoding_for_mime_type(speech_module: Any, mime_type: str):
    normalized_mime = _normalize_mime_type(mime_type)
    encoding_name = _rest_encoding_for_mime_type(normalized_mime)
    return getattr(speech_module.RecognitionConfig.AudioEncoding, encoding_name)


def _transcribe_via_google_cloud_client(
    audio_bytes: bytes,
    *,
    sample_rate_hz: int,
    language_code: str,
    mime_type: str,
) -> dict[str, Any]:
    from google.cloud import speech_v1 as speech

    normalized_mime = _normalize_mime_type(mime_type)
    config_kwargs: dict[str, Any] = {
        "language_code": language_code,
        "enable_automatic_punctuation": True,
        "encoding": _client_encoding_for_mime_type(speech, normalized_mime),
    }
    model_name = os.getenv("GOOGLE_SPEECH_MODEL", "latest_short").strip()
    if model_name:
        config_kwargs["model"] = model_name
    if normalized_mime in _LINEAR16_MIME_TYPES:
        config_kwargs["sample_rate_hertz"] = int(sample_rate_hz)

    try:
        client = speech.SpeechClient()
        response = client.recognize(
            config=speech.RecognitionConfig(**config_kwargs),
            audio=speech.RecognitionAudio(content=audio_bytes),
        )
        return _normalize_result_payload(response.results)
    except Exception as exc:  # pragma: no cover - external dependency branch
        logger.warning("Speech transcription failed via client library: %s", exc)
        return {
            "success": False,
            "transcript": None,
            "confidence": None,
            "error": str(exc),
        }


def transcribe_audio(
    audio_bytes: bytes,
    *,
    sample_rate_hz: int = 16000,
    language_code: str = "en-US",
    mime_type: str = "audio/pcm",
) -> dict[str, Any]:
    """Transcribe short audio content into text."""
    clean_audio = audio_bytes or b""
    if not clean_audio:
        return {
            "success": False,
            "transcript": None,
            "confidence": None,
            "error": "Empty audio",
        }

    try:
        return _transcribe_via_google_cloud_client(
            clean_audio,
            sample_rate_hz=sample_rate_hz,
            language_code=language_code,
            mime_type=mime_type,
        )
    except ImportError as exc:  # pragma: no cover - depends on optional package
        logger.info("Google Cloud Speech client unavailable, using REST fallback: %s", exc)

    try:
        return _transcribe_via_rest(
            clean_audio,
            sample_rate_hz=sample_rate_hz,
            language_code=language_code,
            mime_type=mime_type,
        )
    except Exception as exc:  # pragma: no cover - external dependency branch
        logger.warning("Speech transcription failed via REST fallback: %s", exc)
        return {
            "success": False,
            "transcript": None,
            "confidence": None,
            "error": str(exc),
        }
