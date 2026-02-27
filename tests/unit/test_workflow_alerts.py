from app.services.workflow_alerts import (
    evaluate_connections_health,
    evaluate_workflow_readiness,
)


def test_evaluate_connections_health_no_issues_when_healthy() -> None:
    payload = {
        "status": "healthy",
        "config_readiness": {"status": "ready", "missing_required": [], "missing_recommended": []},
        "workflow_rollout": {
            "kill_switch_enabled": False,
            "canary_enabled": True,
            "canary_user_count": 2,
        },
    }

    issues = evaluate_connections_health(payload, expected_canary_enabled=True, expected_kill_switch=False)
    assert issues == []


def test_evaluate_connections_health_detects_canary_allowlist_issue() -> None:
    payload = {
        "status": "healthy",
        "config_readiness": {"status": "ready"},
        "workflow_rollout": {
            "kill_switch_enabled": False,
            "canary_enabled": True,
            "canary_user_count": 0,
        },
    }

    issues = evaluate_connections_health(payload)
    codes = {issue["code"] for issue in issues}
    assert "canary_allowlist_empty" in codes


def test_evaluate_connections_health_detects_flag_drift() -> None:
    payload = {
        "status": "healthy",
        "config_readiness": {"status": "ready"},
        "workflow_rollout": {
            "kill_switch_enabled": True,
            "canary_enabled": False,
            "canary_user_count": 0,
        },
    }

    issues = evaluate_connections_health(payload, expected_canary_enabled=True, expected_kill_switch=False)
    codes = {issue["code"] for issue in issues}
    assert "rollout_flag_drift_canary" in codes
    assert "rollout_flag_drift_kill_switch" in codes


def test_evaluate_workflow_readiness_reports_not_ready() -> None:
    payload = {"status": "not_ready", "failing_checks": ["workflow_readiness_table_accessible"]}
    issues = evaluate_workflow_readiness(payload)
    assert len(issues) == 1
    assert issues[0]["code"] == "workflow_readiness_not_ready"
