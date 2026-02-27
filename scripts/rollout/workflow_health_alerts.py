"""Poll workflow health endpoints and fail on readiness/rollout drift issues.

Usage:
  uv run python scripts/rollout/workflow_health_alerts.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from app.services.workflow_alerts import (
    evaluate_connections_health,
    evaluate_workflow_readiness,
)


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def _fetch_json(url: str, timeout_seconds: float) -> dict[str, Any]:
    req = urllib_request.Request(url, method="GET")
    with urllib_request.urlopen(req, timeout=timeout_seconds) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _send_webhook(webhook_url: str, payload: dict[str, Any], timeout_seconds: float) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        webhook_url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib_request.urlopen(req, timeout=timeout_seconds):
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Workflow health and rollout drift alerts")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--timeout-seconds", type=float, default=8.0, help="HTTP timeout per request")
    parser.add_argument(
        "--expected-canary-enabled",
        default=os.getenv("EXPECTED_WORKFLOW_CANARY_ENABLED"),
        help="Expected canary flag (true|false). Omit to disable drift check.",
    )
    parser.add_argument(
        "--expected-kill-switch",
        default=os.getenv("EXPECTED_WORKFLOW_KILL_SWITCH"),
        help="Expected kill switch flag (true|false). Omit to disable drift check.",
    )
    parser.add_argument("--output-json", default="", help="Optional file path to write full result JSON")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    timestamp = datetime.now(timezone.utc).isoformat()
    result: dict[str, Any] = {
        "timestamp": timestamp,
        "base_url": base_url,
        "status": "ok",
        "issues": [],
        "connections": {},
        "readiness": {},
    }

    try:
        expected_canary = _parse_bool(args.expected_canary_enabled)
        expected_kill = _parse_bool(args.expected_kill_switch)
    except ValueError as parse_exc:
        result["status"] = "error"
        result["issues"] = [{"code": "invalid_arguments", "severity": "critical", "message": str(parse_exc)}]
        print(json.dumps(result, indent=2))
        return 2

    try:
        connections_payload = _fetch_json(f"{base_url}/health/connections", timeout_seconds=args.timeout_seconds)
        readiness_payload = _fetch_json(
            f"{base_url}/health/workflows/readiness",
            timeout_seconds=args.timeout_seconds,
        )
        result["connections"] = connections_payload
        result["readiness"] = readiness_payload
    except (urllib_error.URLError, TimeoutError, json.JSONDecodeError) as fetch_exc:
        result["status"] = "error"
        result["issues"] = [
            {
                "code": "health_fetch_failed",
                "severity": "critical",
                "message": str(fetch_exc),
            }
        ]
        print(json.dumps(result, indent=2))
        return 2

    issues: list[dict[str, Any]] = []
    issues.extend(
        evaluate_connections_health(
            result["connections"],
            expected_canary_enabled=expected_canary,
            expected_kill_switch=expected_kill,
        )
    )
    issues.extend(evaluate_workflow_readiness(result["readiness"]))
    result["issues"] = issues

    if issues:
        result["status"] = "alert"
        webhook_url = os.getenv("WORKFLOW_ALERT_WEBHOOK_URL", "").strip()
        if webhook_url:
            webhook_payload = {
                "text": "Workflow health alert triggered",
                "details": {
                    "timestamp": timestamp,
                    "base_url": base_url,
                    "issue_count": len(issues),
                    "issues": issues,
                },
            }
            try:
                _send_webhook(webhook_url, webhook_payload, timeout_seconds=args.timeout_seconds)
                result["webhook_sent"] = True
            except Exception as webhook_exc:  # pragma: no cover - best effort notification
                result["webhook_sent"] = False
                result.setdefault("notification_errors", []).append(str(webhook_exc))

    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
            fh.write("\n")

    print(json.dumps(result, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
