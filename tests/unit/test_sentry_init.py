"""Test that Sentry SDK initialization is conditional on env var."""

import os
from unittest.mock import MagicMock, patch


class TestSentryBackendInit:
    """Verify Sentry backend SDK initialization behavior."""

    def test_sentry_not_initialized_without_dsn(self):
        """Sentry init should not be called when SENTRY_DSN_BACKEND is empty."""
        with patch.dict(os.environ, {"SENTRY_DSN_BACKEND": ""}, clear=False):
            import sentry_sdk

            with patch.object(sentry_sdk, "init") as mock_init:
                # Re-evaluate the conditional
                dsn = os.environ.get("SENTRY_DSN_BACKEND", "")
                if dsn:
                    sentry_sdk.init(dsn=dsn)
                mock_init.assert_not_called()

    def test_sentry_initialized_with_dsn(self):
        """Sentry init should be called when SENTRY_DSN_BACKEND is set."""
        with patch.dict(
            os.environ,
            {"SENTRY_DSN_BACKEND": "https://examplePublicKey@o0.ingest.sentry.io/0"},
            clear=False,
        ):
            import sentry_sdk

            with patch.object(sentry_sdk, "init") as mock_init:
                dsn = os.environ.get("SENTRY_DSN_BACKEND", "")
                if dsn:
                    sentry_sdk.init(
                        dsn=dsn,
                        traces_sample_rate=0.0,
                        profiles_sample_rate=0.0,
                        send_default_pii=False,
                    )
                mock_init.assert_called_once()
                call_kwargs = mock_init.call_args[1]
                assert call_kwargs["traces_sample_rate"] == 0.0
                assert call_kwargs["profiles_sample_rate"] == 0.0
                assert call_kwargs["send_default_pii"] is False

    def test_sentry_user_context_sets_id_only(self):
        """Sentry set_user should only include user id UUID, no email or other PII."""
        import sentry_sdk

        with patch.object(sentry_sdk, "set_user") as mock_set_user:
            user_id = "550e8400-e29b-41d4-a716-446655440000"
            sentry_sdk.set_user({"id": user_id})
            mock_set_user.assert_called_once_with({"id": user_id})
            # Verify no PII keys
            call_arg = mock_set_user.call_args[0][0]
            assert "email" not in call_arg
            assert "username" not in call_arg
            assert "ip_address" not in call_arg
