"""Workflow health alert evaluation helpers."""

from __future__ import annotations

from typing import Any


def evaluate_connections_health(
    payload: dict[str, Any],
    *,
    expected_canary_enabled: bool | None = None,
    expected_kill_switch: bool | None = None,
) -> list[dict[str, Any]]:
    """Evaluate `/health/connections` payload for rollout-related issues."""
    issues: list[dict[str, Any]] = []

    if payload.get("status") != "healthy":
        issues.append(
            {
                "code": "connections_unhealthy",
                "severity": "critical",
                "message": "Health endpoint /health/connections is not healthy",
                "details": {
                    "status": payload.get("status"),
                    "error": payload.get("error"),
                },
            }
        )
        return issues

    config_readiness = payload.get("config_readiness") or {}
    if config_readiness.get("status") != "ready":
        issues.append(
            {
                "code": "config_not_ready",
                "severity": "critical",
                "message": "Workflow runtime configuration is not ready",
                "details": {
                    "missing_required": config_readiness.get("missing_required", []),
                    "missing_recommended": config_readiness.get(
                        "missing_recommended", []
                    ),
                },
            }
        )

    rollout = payload.get("workflow_rollout")
    if not isinstance(rollout, dict):
        issues.append(
            {
                "code": "rollout_status_missing",
                "severity": "critical",
                "message": "workflow_rollout block missing from /health/connections payload",
            }
        )
        return issues

    canary_enabled = bool(rollout.get("canary_enabled"))
    kill_switch_enabled = bool(rollout.get("kill_switch_enabled"))
    canary_user_count = int(rollout.get("canary_user_count") or 0)

    if canary_enabled and canary_user_count <= 0:
        issues.append(
            {
                "code": "canary_allowlist_empty",
                "severity": "critical",
                "message": "Canary mode is enabled but WORKFLOW_CANARY_USER_IDS is empty",
            }
        )

    if (
        expected_canary_enabled is not None
        and canary_enabled != expected_canary_enabled
    ):
        issues.append(
            {
                "code": "rollout_flag_drift_canary",
                "severity": "warning",
                "message": "WORKFLOW_CANARY_ENABLED does not match expected state",
                "details": {
                    "expected": expected_canary_enabled,
                    "actual": canary_enabled,
                },
            }
        )

    if expected_kill_switch is not None and kill_switch_enabled != expected_kill_switch:
        issues.append(
            {
                "code": "rollout_flag_drift_kill_switch",
                "severity": "warning",
                "message": "WORKFLOW_KILL_SWITCH does not match expected state",
                "details": {
                    "expected": expected_kill_switch,
                    "actual": kill_switch_enabled,
                },
            }
        )

    return issues


def evaluate_workflow_readiness(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Evaluate `/health/workflows/readiness` payload."""
    issues: list[dict[str, Any]] = []

    status = payload.get("status")
    if status != "ready":
        issues.append(
            {
                "code": "workflow_readiness_not_ready",
                "severity": "critical",
                "message": "Workflow readiness preflight status is not ready",
                "details": {
                    "status": status,
                    "failing_checks": payload.get("failing_checks", []),
                },
            }
        )
    return issues
