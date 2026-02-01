# Plan: Real Integration & Authentication

## Goal
Enable "real" integration testing by removing mocks for Google Auth and Telemetry, allowing the agent to connect to actual backend services (Vertex AI, Supabase).

## Tasks
- [x] Update `tests/integration/test_a2a_protocol.py` to remove `patch` decorators and use real `TestClient` initialization. [8a8352a]
- [x] Verify `setup_telemetry` can run (handle optional `LOGS_BUCKET_NAME` gracefully). [d5f0e82]
- [x] Verify `google.auth.default()` works or provide clear error/setup instructions if it fails. [24b4213]
- [~] Run `test_a2a_protocol.py` with real dependencies.
- [ ] Verify `evaluate_agent.py` can run against the real agent.

## Phase Checkpoint
**Summary**: Integration tests running with real authentication and cloud services.
