"""Evaluate Locust load-test artifacts against Phase 55 thresholds."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_CHAT_REQUEST_NAME = "/a2a/app/run_sse [chat]"
DEFAULT_REQUIRED_REQUESTS = ("/health/connections",)
POOL_HEALTH_ERROR_TOKENS = (
    "too many clients",
    "pool exhausted",
    "connection pool exhausted",
    "timeout acquiring connection",
    "remaining connection slots are reserved",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check Locust stats CSV output against explicit pass/fail thresholds "
            "for the Phase 55 load-test contract."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help=(
            "Path to a Locust stats CSV file or to the base --csv prefix. "
            "Examples: tests/load_test/.results/staging_100u_stats.csv "
            "or tests/load_test/.results/staging_100u"
        ),
    )
    parser.add_argument(
        "--max-p95-ms",
        type=float,
        default=3000.0,
        help="Maximum acceptable p95 latency for the chat SSE request.",
    )
    parser.add_argument(
        "--max-fail-ratio",
        type=float,
        default=0.05,
        help="Maximum acceptable aggregate failure ratio (0.05 = 5%%).",
    )
    parser.add_argument(
        "--max-chat-failures",
        type=int,
        default=0,
        help="Maximum acceptable failures for the primary chat SSE request.",
    )
    parser.add_argument(
        "--max-total-failures",
        type=int,
        default=0,
        help="Maximum acceptable failures across the aggregated Locust row.",
    )
    parser.add_argument(
        "--chat-request-name",
        default=DEFAULT_CHAT_REQUEST_NAME,
        help="Request name used in Locust stats for the primary chat SSE request.",
    )
    parser.add_argument(
        "--require-name",
        action="append",
        default=[],
        help=(
            "Additional request name that must be present in the stats CSV. "
            "May be supplied multiple times."
        ),
    )
    parser.add_argument(
        "--pool-health-log",
        help=(
            "Optional path to a JSON, JSONL, or plain-text pool health capture. "
            "If supplied, all parsed statuses must remain 'ok' and no known "
            "pool exhaustion keywords may appear."
        ),
    )
    parser.add_argument(
        "--min-sse-active",
        type=int,
        default=None,
        help=(
            "Optional lower bound for the maximum observed "
            "details.sse_connections.total_active in the pool health log."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON summary instead of human-readable text.",
    )
    return parser


def resolve_stats_csv(input_value: str) -> Path:
    candidate = Path(input_value)
    if candidate.is_file():
        return candidate
    if candidate.suffix == ".csv":
        raise FileNotFoundError(f"Stats CSV not found: {candidate}")

    prefixed = candidate.with_name(f"{candidate.name}_stats.csv")
    if prefixed.is_file():
        return prefixed

    raise FileNotFoundError(
        "Could not resolve a Locust stats CSV from "
        f"{candidate}. Pass a *_stats.csv file or the base --csv prefix."
    )


def parse_number(raw_value: str | None) -> float | None:
    if raw_value is None:
        return None
    cleaned = str(raw_value).strip()
    if not cleaned or cleaned.upper() == "N/A":
        return None
    return float(cleaned)


def load_stats_rows(stats_csv: Path) -> list[dict[str, str]]:
    with stats_csv.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def is_aggregate_row(row: dict[str, str]) -> bool:
    type_name = (row.get("Type") or "").strip().lower()
    request_name = (row.get("Name") or "").strip().lower()
    return request_name == "aggregated" or type_name == "aggregated"


def find_row(rows: list[dict[str, str]], request_name: str) -> dict[str, str] | None:
    for row in rows:
        if (row.get("Name") or "").strip() == request_name:
            return row
    return None


def find_aggregate_row(rows: list[dict[str, str]]) -> dict[str, str] | None:
    for row in rows:
        if is_aggregate_row(row):
            return row
    return None


def parse_pool_health_log(path: Path) -> dict[str, Any]:
    raw_text = path.read_text(encoding="utf-8")
    json_objects: list[dict[str, Any]] = []
    plain_lines: list[str] = []

    try:
        loaded = json.loads(raw_text)
        if isinstance(loaded, dict):
            json_objects = [loaded]
        elif isinstance(loaded, list):
            json_objects = [item for item in loaded if isinstance(item, dict)]
    except json.JSONDecodeError:
        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError:
                plain_lines.append(stripped)
                continue
            if isinstance(item, dict):
                json_objects.append(item)

    if not json_objects and not plain_lines and raw_text.strip():
        plain_lines.append(raw_text.strip())

    keyword_hits = [
        token
        for token in POOL_HEALTH_ERROR_TOKENS
        if token in raw_text.lower()
    ]
    non_ok_statuses = [
        (entry.get("status") or "unknown")
        for entry in json_objects
        if (entry.get("status") or "").lower() != "ok"
    ]

    max_sse_active = None
    for entry in json_objects:
        raw_active = (
            entry.get("details", {})
            .get("sse_connections", {})
            .get("total_active")
        )
        if raw_active is None:
            continue
        active_value = int(raw_active)
        max_sse_active = (
            active_value
            if max_sse_active is None
            else max(max_sse_active, active_value)
        )

    return {
        "sample_count": len(json_objects) + len(plain_lines),
        "json_samples": len(json_objects),
        "non_ok_statuses": non_ok_statuses,
        "keyword_hits": keyword_hits,
        "max_sse_active": max_sse_active,
    }


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    stats_csv = resolve_stats_csv(args.input)
    rows = load_stats_rows(stats_csv)
    aggregate_row = find_aggregate_row(rows)
    chat_row = find_row(rows, args.chat_request_name)
    required_names = list(
        dict.fromkeys(
            [
                args.chat_request_name,
                *DEFAULT_REQUIRED_REQUESTS,
                *args.require_name,
            ]
        )
    )

    errors: list[str] = []
    notes: list[str] = []
    checks: list[dict[str, Any]] = []

    if aggregate_row is None:
        errors.append("Missing Locust aggregated row.")
    else:
        total_requests = int(parse_number(aggregate_row.get("Request Count")) or 0)
        total_failures = int(parse_number(aggregate_row.get("Failure Count")) or 0)
        fail_ratio = (total_failures / total_requests) if total_requests else 0.0
        checks.append(
            {
                "name": "aggregate_fail_ratio",
                "actual": fail_ratio,
                "limit": args.max_fail_ratio,
                "passed": fail_ratio <= args.max_fail_ratio,
            }
        )
        checks.append(
            {
                "name": "aggregate_failure_count",
                "actual": total_failures,
                "limit": args.max_total_failures,
                "passed": total_failures <= args.max_total_failures,
            }
        )
        if fail_ratio > args.max_fail_ratio:
            errors.append(
                f"Aggregate fail ratio {fail_ratio:.2%} exceeds {args.max_fail_ratio:.2%}."
            )
        if total_failures > args.max_total_failures:
            errors.append(
                f"Aggregate failures {total_failures} exceed {args.max_total_failures}."
            )

    if chat_row is None:
        errors.append(f"Missing required chat row: {args.chat_request_name}")
    else:
        chat_p95 = parse_number(chat_row.get("95%"))
        chat_failures = int(parse_number(chat_row.get("Failure Count")) or 0)
        checks.append(
            {
                "name": "chat_p95_ms",
                "actual": chat_p95,
                "limit": args.max_p95_ms,
                "passed": chat_p95 is not None and chat_p95 <= args.max_p95_ms,
            }
        )
        checks.append(
            {
                "name": "chat_failure_count",
                "actual": chat_failures,
                "limit": args.max_chat_failures,
                "passed": chat_failures <= args.max_chat_failures,
            }
        )
        if chat_p95 is None:
            errors.append(f"Could not read the 95% percentile for {args.chat_request_name}.")
        elif chat_p95 > args.max_p95_ms:
            errors.append(
                f"Chat p95 {chat_p95:.0f}ms exceeds {args.max_p95_ms:.0f}ms."
            )
        if chat_failures > args.max_chat_failures:
            errors.append(
                f"Chat failures {chat_failures} exceed {args.max_chat_failures}."
            )

    missing_required_names = [
        request_name
        for request_name in required_names
        if find_row(rows, request_name) is None
    ]
    if missing_required_names:
        errors.extend(
            f"Missing required request row: {request_name}"
            for request_name in missing_required_names
        )

    pool_health_summary = None
    if args.pool_health_log:
        pool_health_summary = parse_pool_health_log(Path(args.pool_health_log))
        if pool_health_summary["sample_count"] == 0:
            errors.append("Pool health log was provided but contained no readable samples.")
        if pool_health_summary["non_ok_statuses"]:
            errors.append(
                "Pool health log contains non-ok statuses: "
                + ", ".join(pool_health_summary["non_ok_statuses"])
            )
        if pool_health_summary["keyword_hits"]:
            errors.append(
                "Pool health log contains exhaustion keywords: "
                + ", ".join(sorted(set(pool_health_summary["keyword_hits"])))
            )
        if (
            args.min_sse_active is not None
            and (pool_health_summary["max_sse_active"] or 0) < args.min_sse_active
        ):
            errors.append(
                "Pool health log never observed the expected SSE concurrency: "
                f"{pool_health_summary['max_sse_active'] or 0} < {args.min_sse_active}."
            )
    else:
        notes.append(
            "Pool health remains an operator-observed check until --pool-health-log is supplied."
        )

    return {
        "ok": not errors,
        "stats_csv": str(stats_csv),
        "chat_request_name": args.chat_request_name,
        "required_requests": required_names,
        "checks": checks,
        "pool_health": pool_health_summary,
        "notes": notes,
        "errors": errors,
    }


def emit_text(summary: dict[str, Any]) -> None:
    headline = "PASS" if summary["ok"] else "FAIL"
    print(f"{headline}: Phase 55 load-test assertions")
    print(f"Stats CSV: {summary['stats_csv']}")

    for check in summary["checks"]:
        actual = check["actual"]
        if isinstance(actual, float):
            actual_text = f"{actual:.2f}"
        else:
            actual_text = str(actual)
        print(
            f"- {check['name']}: actual={actual_text} limit={check['limit']} "
            f"passed={'yes' if check['passed'] else 'no'}"
        )

    if summary["pool_health"] is not None:
        pool_health = summary["pool_health"]
        print(
            "- pool_health: "
            f"samples={pool_health['sample_count']} "
            f"max_sse_active={pool_health['max_sse_active']}"
        )

    for note in summary["notes"]:
        print(f"- note: {note}")

    if summary["errors"]:
        print("Errors:")
        for error in summary["errors"]:
            print(f"  - {error}")


def main() -> int:
    args = build_parser().parse_args()
    summary = build_summary(args)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        emit_text(summary)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
