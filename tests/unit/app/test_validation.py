from __future__ import annotations

import pytest

from app.config.validation import EnvironmentError, validate_google_ai_config


def test_validate_google_ai_config_accepts_cloud_run_adc(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "pikar-ai-project")
    monkeypatch.setenv("K_SERVICE", "pikar-ai")

    assert validate_google_ai_config() is True


def test_validate_google_ai_config_requires_any_google_ai_credential(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_RUN", raising=False)

    with pytest.raises(EnvironmentError):
        validate_google_ai_config()
