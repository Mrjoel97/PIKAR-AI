"""Unit tests for the Supabase circuit breaker resilience layer."""

from __future__ import annotations

import time

import pytest

# Re-import triggers the singleton constructor — reset before each test.
from app.services.supabase_resilience import (
    SB_CB_FAILURE_THRESHOLD,
    SB_CB_RECOVERY_TIMEOUT,
    SupabaseCircuitBreaker,
    supabase_circuit_breaker,
    with_supabase_resilience,
)


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset the singleton circuit breaker before every test."""
    supabase_circuit_breaker.reset()
    yield
    supabase_circuit_breaker.reset()


# ---------------------------------------------------------------------------
# State machine — basic transitions
# ---------------------------------------------------------------------------


class TestInitialState:
    """Circuit breaker starts in closed state and allows requests."""

    def test_initial_state_is_closed(self):
        status = supabase_circuit_breaker.get_status()
        assert status["state"] == "closed"

    def test_allows_requests_when_closed(self):
        assert supabase_circuit_breaker.should_allow_request() is True

    def test_initial_consecutive_failures_is_zero(self):
        assert supabase_circuit_breaker.get_status()["consecutive_failures"] == 0


class TestClosedToOpen:
    """Circuit transitions closed -> open after failure threshold is reached."""

    def test_single_failure_stays_closed(self):
        supabase_circuit_breaker.record_failure()
        assert supabase_circuit_breaker.get_status()["state"] == "closed"

    def test_failures_below_threshold_stay_closed(self):
        for _ in range(SB_CB_FAILURE_THRESHOLD - 1):
            supabase_circuit_breaker.record_failure()
        assert supabase_circuit_breaker.get_status()["state"] == "closed"

    def test_threshold_failures_open_circuit(self):
        for _ in range(SB_CB_FAILURE_THRESHOLD):
            supabase_circuit_breaker.record_failure()
        assert supabase_circuit_breaker.get_status()["state"] == "open"

    def test_open_circuit_blocks_requests(self):
        for _ in range(SB_CB_FAILURE_THRESHOLD):
            supabase_circuit_breaker.record_failure()
        assert supabase_circuit_breaker.should_allow_request() is False

    def test_consecutive_failures_tracked(self):
        for _ in range(SB_CB_FAILURE_THRESHOLD):
            supabase_circuit_breaker.record_failure()
        status = supabase_circuit_breaker.get_status()
        assert status["consecutive_failures"] == SB_CB_FAILURE_THRESHOLD


class TestOpenToHalfOpen:
    """Circuit transitions open -> half_open after recovery timeout elapses."""

    def _open_circuit(self):
        for _ in range(SB_CB_FAILURE_THRESHOLD):
            supabase_circuit_breaker.record_failure()

    def test_open_stays_blocked_before_timeout(self):
        self._open_circuit()
        # Force last_failure_time to now (timeout has not passed)
        supabase_circuit_breaker._last_failure_time = time.time()
        assert supabase_circuit_breaker.should_allow_request() is False

    def test_open_transitions_to_half_open_after_timeout(self):
        self._open_circuit()
        # Simulate timeout expiry
        supabase_circuit_breaker._last_failure_time = (
            time.time() - SB_CB_RECOVERY_TIMEOUT - 1
        )
        result = supabase_circuit_breaker.should_allow_request()
        assert result is True
        assert supabase_circuit_breaker.get_status()["state"] == "half_open"


class TestHalfOpenTransitions:
    """half_open -> closed on success; half_open -> open on failure."""

    def _set_half_open(self):
        supabase_circuit_breaker._state = "half_open"

    def test_success_in_half_open_closes_circuit(self):
        self._set_half_open()
        supabase_circuit_breaker.record_success()
        assert supabase_circuit_breaker.get_status()["state"] == "closed"

    def test_success_resets_consecutive_failures(self):
        supabase_circuit_breaker._consecutive_failures = 3
        self._set_half_open()
        supabase_circuit_breaker.record_success()
        assert supabase_circuit_breaker.get_status()["consecutive_failures"] == 0

    def test_failure_in_half_open_reopens_circuit(self):
        self._set_half_open()
        supabase_circuit_breaker.record_failure(RuntimeError("probe failed"))
        assert supabase_circuit_breaker.get_status()["state"] == "open"

    def test_half_open_allows_request(self):
        self._set_half_open()
        assert supabase_circuit_breaker.should_allow_request() is True


class TestReset:
    """reset() unconditionally restores closed state."""

    def test_reset_from_open(self):
        for _ in range(SB_CB_FAILURE_THRESHOLD):
            supabase_circuit_breaker.record_failure()
        supabase_circuit_breaker.reset()
        status = supabase_circuit_breaker.get_status()
        assert status["state"] == "closed"
        assert status["consecutive_failures"] == 0

    def test_reset_allows_requests(self):
        for _ in range(SB_CB_FAILURE_THRESHOLD):
            supabase_circuit_breaker.record_failure()
        supabase_circuit_breaker.reset()
        assert supabase_circuit_breaker.should_allow_request() is True

    def test_reset_clears_last_failure_time(self):
        supabase_circuit_breaker.record_failure()
        supabase_circuit_breaker.reset()
        assert supabase_circuit_breaker.get_status()["last_failure_time"] is None


class TestGetStatus:
    """get_status() returns the expected keys."""

    def test_status_contains_required_keys(self):
        status = supabase_circuit_breaker.get_status()
        assert "state" in status
        assert "consecutive_failures" in status
        assert "failure_threshold" in status
        assert "recovery_timeout_seconds" in status
        assert "last_failure_time" in status

    def test_status_failure_threshold_matches_env(self):
        assert (
            supabase_circuit_breaker.get_status()["failure_threshold"]
            == SB_CB_FAILURE_THRESHOLD
        )

    def test_status_recovery_timeout_matches_env(self):
        assert (
            supabase_circuit_breaker.get_status()["recovery_timeout_seconds"]
            == SB_CB_RECOVERY_TIMEOUT
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    """SupabaseCircuitBreaker is a singleton."""

    def test_two_instances_are_same_object(self):
        a = SupabaseCircuitBreaker()
        b = SupabaseCircuitBreaker()
        assert a is b

    def test_module_level_singleton_is_same_object(self):
        new_instance = SupabaseCircuitBreaker()
        assert new_instance is supabase_circuit_breaker


# ---------------------------------------------------------------------------
# Decorator: with_supabase_resilience
# ---------------------------------------------------------------------------


class TestWithSupabaseResilienceDecorator:
    """with_supabase_resilience wraps async functions correctly."""

    @pytest.mark.asyncio
    async def test_returns_function_result_when_circuit_closed(self):
        @with_supabase_resilience(default_return=[])
        async def fetch():
            return [{"id": 1}]

        result = await fetch()
        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_records_success_on_clean_call(self):
        @with_supabase_resilience(default_return=None)
        async def noop():
            return "ok"

        await noop()
        assert supabase_circuit_breaker.get_status()["consecutive_failures"] == 0

    @pytest.mark.asyncio
    async def test_returns_default_on_exception(self):
        @with_supabase_resilience(default_return="fallback")
        async def broken():
            raise RuntimeError("db down")

        result = await broken()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_records_failure_on_exception(self):
        @with_supabase_resilience(default_return=None)
        async def broken():
            raise RuntimeError("db down")

        await broken()
        assert supabase_circuit_breaker.get_status()["consecutive_failures"] == 1

    @pytest.mark.asyncio
    async def test_returns_default_when_circuit_is_open(self):
        # Open the circuit
        for _ in range(SB_CB_FAILURE_THRESHOLD):
            supabase_circuit_breaker.record_failure()

        call_count = 0

        @with_supabase_resilience(default_return="default")
        async def should_not_be_called():
            nonlocal call_count
            call_count += 1
            return "real"

        result = await should_not_be_called()
        assert result == "default"
        assert call_count == 0, (
            "Wrapped function must not be called when circuit is open"
        )

    @pytest.mark.asyncio
    async def test_default_return_none_by_default(self):
        @with_supabase_resilience()
        async def broken():
            raise RuntimeError("db down")

        result = await broken()
        assert result is None

    @pytest.mark.asyncio
    async def test_preserves_function_name(self):
        @with_supabase_resilience(default_return=[])
        async def my_special_function():
            return []

        assert my_special_function.__name__ == "my_special_function"

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self):
        received = {}

        @with_supabase_resilience(default_return=None)
        async def takes_args(a, b, *, key="default"):
            received["a"] = a
            received["b"] = b
            received["key"] = key
            return "done"

        await takes_args(1, 2, key="custom")
        assert received == {"a": 1, "b": 2, "key": "custom"}

    @pytest.mark.asyncio
    async def test_open_circuit_does_not_increment_failures(self):
        # Drive circuit to open
        for _ in range(SB_CB_FAILURE_THRESHOLD):
            supabase_circuit_breaker.record_failure()

        failures_before = supabase_circuit_breaker.get_status()["consecutive_failures"]

        @with_supabase_resilience(default_return=None)
        async def blocked():
            return "never"

        await blocked()
        # Failures should not increase when the circuit short-circuits
        assert (
            supabase_circuit_breaker.get_status()["consecutive_failures"]
            == failures_before
        )
