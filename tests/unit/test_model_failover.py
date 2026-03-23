"""Unit tests for the model failover circuit breaker."""

import time
from unittest.mock import patch

from app.services.model_failover import (
    FAILOVER_FAILURE_THRESHOLD,
    FAILOVER_RECOVERY_TIMEOUT,
    ModelFailover,
)


def _fresh() -> ModelFailover:
    """Return a fresh, isolated ModelFailover instance (not the singleton)."""
    fb = object.__new__(ModelFailover)
    fb._initialized = False
    fb.__init__()
    return fb


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_initial_state_is_closed():
    fb = _fresh()
    assert fb.state == "closed"


def test_initial_active_model_is_primary():
    fb = _fresh()
    assert fb.active_model_name == "gemini-2.5-pro"


# ---------------------------------------------------------------------------
# Failure accumulation → OPEN
# ---------------------------------------------------------------------------


def test_single_failure_does_not_open_circuit():
    fb = _fresh()
    fb.record_failure()
    assert fb.state == "closed"


def test_failures_below_threshold_stay_closed():
    fb = _fresh()
    for _ in range(FAILOVER_FAILURE_THRESHOLD - 1):
        fb.record_failure()
    assert fb.state == "closed"


def test_threshold_failures_open_circuit():
    fb = _fresh()
    for _ in range(FAILOVER_FAILURE_THRESHOLD):
        fb.record_failure()
    assert fb.state == "open"


def test_open_circuit_returns_fallback_model():
    fb = _fresh()
    for _ in range(FAILOVER_FAILURE_THRESHOLD):
        fb.record_failure()
    assert fb.active_model_name == "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# OPEN → HALF_OPEN after recovery timeout
# ---------------------------------------------------------------------------


def test_open_transitions_to_half_open_after_timeout():
    fb = _fresh()
    for _ in range(FAILOVER_FAILURE_THRESHOLD):
        fb.record_failure()
    assert fb.state == "open"

    # Simulate recovery timeout elapsed
    fb._last_failure_time = time.time() - (FAILOVER_RECOVERY_TIMEOUT + 1)

    # Calling get_active_model triggers the open → half_open transition
    fb.get_active_model()
    assert fb.state == "half_open"


def test_half_open_returns_primary_model():
    fb = _fresh()
    for _ in range(FAILOVER_FAILURE_THRESHOLD):
        fb.record_failure()
    fb._last_failure_time = time.time() - (FAILOVER_RECOVERY_TIMEOUT + 1)
    fb.get_active_model()  # transitions to half_open
    assert fb.active_model_name == "gemini-2.5-pro"


def test_open_still_returns_fallback_before_timeout():
    fb = _fresh()
    for _ in range(FAILOVER_FAILURE_THRESHOLD):
        fb.record_failure()
    # Not enough time has passed
    fb._last_failure_time = time.time() - (FAILOVER_RECOVERY_TIMEOUT - 10)
    assert fb.active_model_name == "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# HALF_OPEN success → CLOSED
# ---------------------------------------------------------------------------


def test_success_in_half_open_closes_circuit():
    fb = _fresh()
    for _ in range(FAILOVER_FAILURE_THRESHOLD):
        fb.record_failure()
    fb._last_failure_time = time.time() - (FAILOVER_RECOVERY_TIMEOUT + 1)
    fb.get_active_model()  # open → half_open
    assert fb.state == "half_open"

    fb.record_success()
    assert fb.state == "closed"


def test_success_in_half_open_resets_failure_counter():
    fb = _fresh()
    for _ in range(FAILOVER_FAILURE_THRESHOLD):
        fb.record_failure()
    fb._last_failure_time = time.time() - (FAILOVER_RECOVERY_TIMEOUT + 1)
    fb.get_active_model()
    fb.record_success()
    assert fb._consecutive_failures == 0


# ---------------------------------------------------------------------------
# HALF_OPEN failure → OPEN
# ---------------------------------------------------------------------------


def test_failure_in_half_open_reopens_circuit():
    fb = _fresh()
    for _ in range(FAILOVER_FAILURE_THRESHOLD):
        fb.record_failure()
    fb._last_failure_time = time.time() - (FAILOVER_RECOVERY_TIMEOUT + 1)
    fb.get_active_model()  # open → half_open
    assert fb.state == "half_open"

    fb.record_failure()
    assert fb.state == "open"


# ---------------------------------------------------------------------------
# Success in CLOSED state
# ---------------------------------------------------------------------------


def test_success_in_closed_resets_failures():
    fb = _fresh()
    fb.record_failure()
    fb.record_failure()
    fb.record_success()
    assert fb._consecutive_failures == 0
    assert fb.state == "closed"


def test_success_in_closed_stays_closed():
    fb = _fresh()
    fb.record_success()
    assert fb.state == "closed"


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------


def test_reset_restores_closed_state():
    fb = _fresh()
    for _ in range(FAILOVER_FAILURE_THRESHOLD):
        fb.record_failure()
    assert fb.state == "open"
    fb.reset()
    assert fb.state == "closed"


def test_reset_clears_failure_counter():
    fb = _fresh()
    fb.record_failure()
    fb.record_failure()
    fb.reset()
    assert fb._consecutive_failures == 0


def test_reset_clears_last_failure_time():
    fb = _fresh()
    fb.record_failure()
    fb.reset()
    assert fb._last_failure_time == 0.0


# ---------------------------------------------------------------------------
# get_status()
# ---------------------------------------------------------------------------


def test_get_status_shape():
    fb = _fresh()
    status = fb.get_status()
    assert set(status.keys()) == {
        "state",
        "active_model",
        "consecutive_failures",
        "primary_model",
        "fallback_model",
        "failure_threshold",
        "recovery_timeout_seconds",
    }


def test_get_status_closed_values():
    fb = _fresh()
    status = fb.get_status()
    assert status["state"] == "closed"
    assert status["active_model"] == "gemini-2.5-pro"
    assert status["consecutive_failures"] == 0
    assert status["primary_model"] == "gemini-2.5-pro"
    assert status["fallback_model"] == "gemini-2.5-flash"
    assert status["failure_threshold"] == FAILOVER_FAILURE_THRESHOLD
    assert status["recovery_timeout_seconds"] == FAILOVER_RECOVERY_TIMEOUT


def test_get_status_open_values():
    fb = _fresh()
    for _ in range(FAILOVER_FAILURE_THRESHOLD):
        fb.record_failure()
    status = fb.get_status()
    assert status["state"] == "open"
    assert status["active_model"] == "gemini-2.5-flash"
    assert status["consecutive_failures"] == FAILOVER_FAILURE_THRESHOLD


# ---------------------------------------------------------------------------
# get_active_model() returns a Gemini instance
# ---------------------------------------------------------------------------


def test_get_active_model_returns_gemini_instance():
    """get_active_model() should return a Gemini object (mocked by conftest)."""
    fb = _fresh()
    model = fb.get_active_model()
    # conftest.py mocks google.adk.models.Gemini as a MagicMock, so calling it
    # returns a MagicMock instance rather than None.
    assert model is not None


def test_get_active_model_passes_retry_options():
    """When retry_options is provided it is forwarded to Gemini constructor."""
    from unittest.mock import MagicMock, patch

    fb = _fresh()
    mock_retry = MagicMock()

    with patch("app.services.model_failover.Gemini") as MockGemini:
        fb.get_active_model(retry_options=mock_retry)
        MockGemini.assert_called_once_with(model="gemini-2.5-pro", retry_options=mock_retry)


def test_get_active_model_no_retry_options():
    """When no retry_options provided, Gemini is called without that kwarg."""
    from unittest.mock import patch

    fb = _fresh()

    with patch("app.services.model_failover.Gemini") as MockGemini:
        fb.get_active_model()
        MockGemini.assert_called_once_with(model="gemini-2.5-pro")


# ---------------------------------------------------------------------------
# Environment variable overrides
# ---------------------------------------------------------------------------


def test_env_override_primary_model():
    with patch.dict("os.environ", {"GEMINI_AGENT_MODEL_PRIMARY": "gemini-1.5-pro"}):
        fb = _fresh()
        assert fb._primary_model == "gemini-1.5-pro"


def test_env_override_fallback_model():
    with patch.dict("os.environ", {"GEMINI_AGENT_MODEL_FALLBACK": "gemini-1.5-flash"}):
        fb = _fresh()
        assert fb._fallback_model == "gemini-1.5-flash"
