"""Run strict-mode reruns for AGENT-2 integration workflows and capture evidence.

This script is designed to be safe in partially configured environments:
- It records per-workflow evidence even when DB/network/env blockers prevent starts.
- It forces strict workflow flags for the process (without persisting env changes).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LANE_JSON = ROOT / "plans" / "workflow-e2e-remediation-20260223" / "worktree-lanes" / "AGENT-2-INTEGRATIONS" / "lane.json"
DEFAULT_EVIDENCE_DIR = ROOT / "plans" / "workflow-e2e-remediation-20260223" / "worktree-lanes" / "AGENT-2-INTEGRATIONS" / "evidence"
DEFAULT_TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


STRICT_ENV_OVERRIDES = {
    "WORKFLOW_STRICT_TOOL_RESOLUTION": "true",
    "WORKFLOW_STRICT_CRITICAL_TOOL_GUARD": "true",
    "WORKFLOW_ALLOW_FALLBACK_SIMULATION": "false",
    "WORKFLOW_ENFORCE_READINESS_GATE": "true",
}


@dataclass
class RunContext:
    run_id: str
    out_dir: Path
    jsonl_path: Path
    summary_path: Path


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in records:
            fh.write(json.dumps(row, default=str) + "\n")


def _bool_env_snapshot() -> dict[str, Any]:
    return {
        "WORKFLOW_STRICT_TOOL_RESOLUTION": os.getenv("WORKFLOW_STRICT_TOOL_RESOLUTION"),
        "WORKFLOW_STRICT_CRITICAL_TOOL_GUARD": os.getenv("WORKFLOW_STRICT_CRITICAL_TOOL_GUARD"),
        "WORKFLOW_ALLOW_FALLBACK_SIMULATION": os.getenv("WORKFLOW_ALLOW_FALLBACK_SIMULATION"),
        "WORKFLOW_ENFORCE_READINESS_GATE": os.getenv("WORKFLOW_ENFORCE_READINESS_GATE"),
        "BACKEND_API_URL_set": bool((os.getenv("BACKEND_API_URL") or "").strip()),
        "WORKFLOW_SERVICE_SECRET_set": bool((os.getenv("WORKFLOW_SERVICE_SECRET") or "").strip()),
        "SUPABASE_URL_set": bool((os.getenv("SUPABASE_URL") or "").strip()),
        "SUPABASE_SERVICE_ROLE_KEY_set": bool((os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()),
        "SUPABASE_SERVICE_KEY_set": bool((os.getenv("SUPABASE_SERVICE_KEY") or "").strip()),
        "GOOGLE_API_KEY_set": bool((os.getenv("GOOGLE_API_KEY") or "").strip()),
    }


def _load_lane_workflows(lane_json: Path) -> list[str]:
    data = json.loads(lane_json.read_text(encoding="utf-8"))
    workflows = data.get("assigned_workflows") or []
    return [str(name) for name in workflows]


def _render_summary(ctx: RunContext, records: list[dict[str, Any]], preflight: dict[str, Any]) -> None:
    starts = [r for r in records if r.get("kind") == "workflow_rerun"]
    status_counts: dict[str, int] = {}
    for row in starts:
        status = row.get("result_type", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    lines = [
        "# AGENT-2 Integration Workflow Strict Reruns",
        "",
        f"- Run ID: `{ctx.run_id}`",
        f"- Timestamp: `{_now_iso()}`",
        f"- Workflows attempted: `{len(starts)}`",
        f"- Evidence JSONL: `{ctx.jsonl_path}`",
        "",
        "## Preflight",
        "",
        f"- Env snapshot: `{json.dumps(preflight.get('env', {}), sort_keys=True)}`",
    ]
    if preflight.get("readiness_error"):
        lines.append(f"- Readiness report error: `{preflight['readiness_error']}`")
    else:
        lines.append("- Readiness report fetched: `true`")
        if preflight.get("readiness_report_status"):
            lines.append(f"- Readiness report status: `{preflight['readiness_report_status']}`")
    lines.extend(["", "## Result Counts", ""])
    if status_counts:
        for key in sorted(status_counts):
            lines.append(f"- `{key}`: `{status_counts[key]}`")
    else:
        lines.append("- No workflow attempts were recorded.")
    lines.extend(["", "## Per-Workflow Results", ""])
    for row in starts:
        wf = row.get("workflow_name")
        result_type = row.get("result_type")
        error_code = row.get("error_code")
        message = row.get("message") or row.get("error") or ""
        if len(message) > 240:
            message = message[:237] + "..."
        extra = []
        if row.get("execution_id"):
            extra.append(f"execution_id={row['execution_id']}")
        if error_code:
            extra.append(f"error_code={error_code}")
        if row.get("http_status"):
            extra.append(f"http_status={row['http_status']}")
        suffix = f" ({', '.join(extra)})" if extra else ""
        lines.append(f"- `{wf}`: `{result_type}`{suffix} {message}".rstrip())

    ctx.summary_path.parent.mkdir(parents=True, exist_ok=True)
    ctx.summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _attempt_workflow_reruns(workflows: list[str], user_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    preflight: dict[str, Any] = {"env": _bool_env_snapshot()}

    try:
        from app.workflows.readiness import build_workflow_readiness_report

        try:
            report = build_workflow_readiness_report()
            preflight["readiness_report_status"] = report.get("status")
            preflight["readiness_checks"] = report.get("checks")
        except Exception as exc:
            preflight["readiness_error"] = str(exc)
    except Exception as exc:
        preflight["readiness_error"] = f"import_failed: {exc}"

    try:
        from app.workflows.engine import WorkflowEngine

        engine = WorkflowEngine()
        engine_init_error: str | None = None
    except Exception as exc:
        engine = None
        engine_init_error = str(exc)

    if engine_init_error:
        for name in workflows:
            records.append(
                {
                    "kind": "workflow_rerun",
                    "ts": _now_iso(),
                    "workflow_name": name,
                    "run_source": "agent_ui",
                    "result_type": "blocked_engine_init",
                    "error": engine_init_error,
                    "error_code": "engine_init_failed",
                }
            )
        return records, preflight

    for name in workflows:
        row: dict[str, Any] = {
            "kind": "workflow_rerun",
            "ts": _now_iso(),
            "workflow_name": name,
            "run_source": "agent_ui",
        }
        try:
            result = await engine.start_workflow(
                user_id=user_id,
                template_name=name,
                run_source="agent_ui",
            )
            row["start_result"] = result
            if "error" in result:
                row["result_type"] = "start_error"
                row["error"] = result.get("error")
                row["error_code"] = result.get("error_code")
                if "readiness" in result:
                    row["readiness"] = result.get("readiness")
            else:
                row["result_type"] = "start_ok"
                row["execution_id"] = result.get("execution_id")
                row["message"] = result.get("message")
                row["status"] = result.get("status")
                execution_id = result.get("execution_id")
                if execution_id:
                    try:
                        status = await engine.get_execution_status(execution_id)
                        row["execution_status_snapshot"] = status
                    except Exception as status_exc:
                        row["execution_status_error"] = str(status_exc)
        except Exception as exc:
            row["result_type"] = "exception"
            row["error"] = str(exc)
            row["error_code"] = "exception"
        records.append(row)

    return records, preflight


def _build_run_context(out_dir: Path) -> RunContext:
    run_id = datetime.now().strftime("agent2-strict-rerun-%Y%m%d-%H%M%S")
    return RunContext(
        run_id=run_id,
        out_dir=out_dir,
        jsonl_path=out_dir / f"{run_id}.jsonl",
        summary_path=out_dir / f"{run_id}.md",
    )


async def _async_main(args: argparse.Namespace) -> int:
    for key, value in STRICT_ENV_OVERRIDES.items():
        os.environ[key] = value

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    lane_json = Path(args.lane_json).resolve()
    out_dir = Path(args.out_dir).resolve()
    workflows = _load_lane_workflows(lane_json)
    ctx = _build_run_context(out_dir)

    records, preflight = await _attempt_workflow_reruns(workflows, user_id=args.user_id)
    _write_jsonl(ctx.jsonl_path, records)
    _render_summary(ctx, records, preflight)

    print(f"Wrote per-workflow evidence: {ctx.jsonl_path}")
    print(f"Wrote summary: {ctx.summary_path}")

    failures = [r for r in records if r.get("result_type") != "start_ok"]
    print(f"Workflow reruns attempted: {len(records)}")
    print(f"Start OK: {len(records) - len(failures)}")
    print(f"Non-start outcomes: {len(failures)}")

    if args.fail_on_non_start and failures:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AGENT-2 strict workflow reruns and capture evidence.")
    parser.add_argument("--lane-json", default=str(DEFAULT_LANE_JSON))
    parser.add_argument("--out-dir", default=str(DEFAULT_EVIDENCE_DIR))
    parser.add_argument("--user-id", default=DEFAULT_TEST_USER_ID)
    parser.add_argument("--fail-on-non-start", action="store_true")
    args = parser.parse_args()

    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
