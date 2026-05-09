"""Smoke tests for LONGTASK-02 deploy artifacts.

These tests validate that the deploy scripts and config exist on disk and
contain the expected anchors. They do NOT execute gcloud or docker —
that would require live cloud credentials.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Resolve repo root from this test file: tests/unit/test_deploy_scripts.py
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def deploy_script_text() -> str:
    path = REPO_ROOT / "scripts" / "deploy" / "cloud_run_job.ps1"
    assert path.is_file(), f"Missing deploy script: {path}"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cloudbuild_text() -> str:
    path = REPO_ROOT / "cloudbuild.yaml"
    assert path.is_file(), f"Missing cloudbuild config: {path}"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def worker_dockerfile_text() -> str:
    path = REPO_ROOT / "Dockerfile.worker"
    assert path.is_file(), f"Missing Dockerfile.worker: {path}"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def runbook_text() -> str:
    path = REPO_ROOT / "docs" / "deploy" / "workflow-worker.md"
    assert path.is_file(), f"Missing runbook: {path}"
    return path.read_text(encoding="utf-8")


# --- cloud_run_job.ps1 -------------------------------------------------------


def test_deploy_script_creates_run_job(deploy_script_text: str) -> None:
    assert "gcloud run jobs create" in deploy_script_text
    assert "gcloud run jobs update" in deploy_script_text


def test_deploy_script_configures_scheduler(deploy_script_text: str) -> None:
    assert "gcloud scheduler jobs create" in deploy_script_text
    assert "gcloud scheduler jobs update" in deploy_script_text
    # Default cadence: every 5 minutes
    assert "*/5 * * * *" in deploy_script_text


def test_deploy_script_uses_agents_service_account(deploy_script_text: str) -> None:
    assert "agents@pikar-ai-project.iam.gserviceaccount.com" in deploy_script_text


def test_deploy_script_default_project_matches_memory(deploy_script_text: str) -> None:
    # Per project_cloud_run_migration.md memory note
    assert "pikar-ai-project" in deploy_script_text


def test_deploy_script_sets_resource_limits(deploy_script_text: str) -> None:
    assert "1Gi" in deploy_script_text
    assert "3600s" in deploy_script_text  # task-timeout
    assert "max-retries" in deploy_script_text
    assert "parallelism" in deploy_script_text


def test_deploy_script_passes_required_env_keys(deploy_script_text: str) -> None:
    for key in (
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "REDIS_HOST",
        "REDIS_PORT",
        "GOOGLE_CLOUD_PROJECT",
        "ENABLE_CONVERSATION_SUMMARIZER",
        "SESSION_MAX_EVENTS",
    ):
        assert key in deploy_script_text, f"Missing env key wiring: {key}"


def test_deploy_script_quotes_comma_bearing_flags(deploy_script_text: str) -> None:
    """Per project_cloud_run_source_rebuild_broken_2026_05_07: PowerShell eats
    unquoted commas in flag values. We sidestep this by storing such values in
    $variables (e.g. $envFlag, $memory, $taskTimeout) rather than inlining."""
    assert "$envFlag" in deploy_script_text
    assert "$memory" in deploy_script_text
    assert "$taskTimeout" in deploy_script_text


def test_deploy_script_prints_manual_trigger(deploy_script_text: str) -> None:
    assert "gcloud run jobs execute" in deploy_script_text


# --- cloudbuild.yaml ---------------------------------------------------------


def test_cloudbuild_has_substitutions_block(cloudbuild_text: str) -> None:
    assert "substitutions:" in cloudbuild_text
    for sub in ("_REGION", "_PROJECT_ID", "_REPOSITORY", "_IMAGE_TAG"):
        assert sub in cloudbuild_text, f"Missing substitution: {sub}"


def test_cloudbuild_build_push_deploy_steps(cloudbuild_text: str) -> None:
    assert "docker build" in cloudbuild_text
    assert "docker push" in cloudbuild_text
    assert "gcloud run jobs update" in cloudbuild_text


def test_cloudbuild_uses_buildkit_caching(cloudbuild_text: str) -> None:
    assert "DOCKER_BUILDKIT=1" in cloudbuild_text
    assert "--cache-from" in cloudbuild_text


def test_cloudbuild_runs_as_agents_service_account(cloudbuild_text: str) -> None:
    assert "agents@pikar-ai-project.iam.gserviceaccount.com" in cloudbuild_text


def test_cloudbuild_documents_trigger_registration(cloudbuild_text: str) -> None:
    """cloudbuild.yaml header should document how to register the trigger."""
    assert "gcloud builds triggers create github" in cloudbuild_text
    assert "app/workflows/**" in cloudbuild_text
    assert "Dockerfile.worker" in cloudbuild_text


# --- Dockerfile.worker -------------------------------------------------------


def test_worker_dockerfile_uses_python_312_slim(worker_dockerfile_text: str) -> None:
    assert "python:3.12-slim" in worker_dockerfile_text


def test_worker_dockerfile_uses_uv(worker_dockerfile_text: str) -> None:
    assert "uv sync --frozen" in worker_dockerfile_text


def test_worker_dockerfile_runs_worker_module(worker_dockerfile_text: str) -> None:
    """Entrypoint must launch app.workflows.worker, mirroring run_worker.py."""
    assert "app.workflows.worker" in worker_dockerfile_text


def test_worker_dockerfile_no_exposed_port(worker_dockerfile_text: str) -> None:
    """Cloud Run Jobs do not expose ports — no EXPOSE directive."""
    # Look for an actual Dockerfile EXPOSE directive (start of line),
    # not the word "EXPOSE" used inside a comment.
    expose_directives = [
        line
        for line in worker_dockerfile_text.splitlines()
        if line.strip().startswith("EXPOSE ")
    ]
    assert not expose_directives, f"Unexpected EXPOSE directive(s): {expose_directives}"


# --- runbook -----------------------------------------------------------------


def test_runbook_covers_first_time_and_subsequent(runbook_text: str) -> None:
    assert "First-time deploy" in runbook_text
    assert "Subsequent deploys" in runbook_text
    assert "Manual trigger" in runbook_text
    assert "Troubleshooting" in runbook_text


def test_runbook_includes_logs_command(runbook_text: str) -> None:
    assert "gcloud run jobs logs read" in runbook_text
