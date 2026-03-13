import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from app.services.long_video_benchmark import (
    DEFAULT_API_BASE_URL,
    build_benchmark_prompt,
    build_env_overrides,
    choose_best_service_report,
    format_report_summary,
    is_healthy_report,
    run_service_benchmark,
    run_sse_benchmark,
    write_benchmark_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark long-video generation through service and SSE layers.")
    parser.add_argument("--mode", choices=("service", "sse", "staged"), default="staged")
    parser.add_argument("--duration", type=int, default=60, help="Duration to benchmark in service or sse mode.")
    parser.add_argument(
        "--durations",
        type=int,
        nargs="*",
        default=[60, 180],
        help="Durations to benchmark in staged mode.",
    )
    parser.add_argument("--prompt", help="Optional explicit prompt. Defaults to a duration-aware benchmark prompt.")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--token", default=None, help="Bearer token for authenticated SSE benchmark.")
    parser.add_argument("--agent-mode", default="auto")
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--user-id-prefix", default="long-video-benchmark")
    parser.add_argument("--tune", action="store_true", help="Run a 60s service-level concurrency sweep before longer runs.")
    parser.add_argument(
        "--concurrency-sweep",
        type=int,
        nargs="*",
        default=[2, 3, 4],
        help="Concurrency values to test when --tune is enabled.",
    )
    parser.add_argument("--director-max-concurrency", type=int, default=None)
    parser.add_argument("--veo-poll-interval", type=int, default=None)
    parser.add_argument("--veo-poll-interval-min", type=int, default=None)
    parser.add_argument("--veo-poll-interval-max", type=int, default=None)
    parser.add_argument("--read-timeout-seconds", type=int, default=3600)
    parser.add_argument("--require-voiceover", action="store_true", help="Fail service-layer runs if generated scenes are missing voiceover.")
    return parser.parse_args()


async def _run_service_once(
    *,
    duration_seconds: int,
    prompt: str,
    user_id_prefix: str,
    env_overrides: dict[str, Any],
    out_dir: str | None,
    prefix: str,
    require_voiceover: bool,
) -> tuple[dict[str, Any], Path]:
    report = await run_service_benchmark(
        duration_seconds=duration_seconds,
        prompt=prompt,
        user_id_prefix=user_id_prefix,
        env_overrides=env_overrides,
        require_voiceover=require_voiceover,
    )
    path = write_benchmark_report(report, out_dir=out_dir, prefix=prefix)
    print(format_report_summary(report, report_path=path))
    print()
    return report, path


def _run_sse_once(
    *,
    duration_seconds: int,
    prompt: str,
    api_base_url: str,
    token: str | None,
    agent_mode: str,
    read_timeout_seconds: int,
    out_dir: str | None,
    prefix: str,
) -> tuple[dict[str, Any], Path]:
    report = run_sse_benchmark(
        duration_seconds=duration_seconds,
        prompt=prompt,
        api_base_url=api_base_url,
        token=token,
        agent_mode=agent_mode,
        read_timeout_seconds=read_timeout_seconds,
    )
    path = write_benchmark_report(report, out_dir=out_dir, prefix=prefix)
    print(format_report_summary(report, report_path=path))
    print()
    return report, path


def _service_should_gate_next_step(report: dict[str, Any]) -> bool:
    return is_healthy_report(report)


def _sse_should_gate_next_step(report: dict[str, Any] | None) -> bool:
    if report is None:
        return True
    if report.get("blocked_reason"):
        return True
    return is_healthy_report(report)


def _write_summary(summary: dict[str, Any], out_dir: str | None) -> Path:
    output_dir = Path(out_dir) if out_dir else Path("artifacts") / "benchmarks" / "long_video"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"staged-summary-{summary['timestamp']}.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()
    token = args.token or os.getenv("SMOKE_BEARER_TOKEN") or os.getenv("BENCHMARK_BEARER_TOKEN")
    out_dir = args.out_dir
    base_env_overrides = build_env_overrides(
        director_max_concurrency=args.director_max_concurrency,
        veo_poll_interval=args.veo_poll_interval,
        veo_poll_interval_min=args.veo_poll_interval_min,
        veo_poll_interval_max=args.veo_poll_interval_max,
    )

    if args.mode == "service":
        prompt = args.prompt or build_benchmark_prompt(args.duration)
        report, _ = asyncio.run(
            _run_service_once(
                duration_seconds=args.duration,
                prompt=prompt,
                user_id_prefix=args.user_id_prefix,
                env_overrides=base_env_overrides,
                out_dir=out_dir,
                prefix="service-benchmark",
                require_voiceover=args.require_voiceover,
            )
        )
        return 0 if is_healthy_report(report) else 1

    if args.mode == "sse":
        prompt = args.prompt or build_benchmark_prompt(args.duration)
        report, _ = _run_sse_once(
            duration_seconds=args.duration,
            prompt=prompt,
            api_base_url=args.api_base_url,
            token=token,
            agent_mode=args.agent_mode,
            read_timeout_seconds=args.read_timeout_seconds,
            out_dir=out_dir,
            prefix="sse-benchmark",
        )
        return 0 if is_healthy_report(report) else 1

    durations = [int(value) for value in args.durations]
    if not durations:
        print("No durations provided for staged mode.", file=sys.stderr)
        return 1

    summary: dict[str, Any] = {
        "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
        "api_base_url": args.api_base_url,
        "token_provided": bool(token),
        "baseline_env_overrides": base_env_overrides,
        "reports": [],
        "tuning": {},
        "recommended_env_overrides": dict(base_env_overrides),
    }

    baseline_duration = durations[0]
    baseline_prompt = args.prompt or build_benchmark_prompt(baseline_duration)
    service_report, service_path = asyncio.run(
        _run_service_once(
            duration_seconds=baseline_duration,
            prompt=baseline_prompt,
            user_id_prefix=args.user_id_prefix,
            env_overrides=base_env_overrides,
            out_dir=out_dir,
            prefix="service-baseline",
            require_voiceover=args.require_voiceover,
        )
    )
    summary["reports"].append({"layer": "service", "duration_seconds": baseline_duration, "path": str(service_path)})
    if not _service_should_gate_next_step(service_report):
        summary["stopped_after"] = f"service-{baseline_duration}s"
        summary_path = _write_summary(summary, out_dir)
        print(f"staged_summary={summary_path}")
        return 1

    sse_report = None
    if token:
        sse_report, sse_path = _run_sse_once(
            duration_seconds=baseline_duration,
            prompt=baseline_prompt,
            api_base_url=args.api_base_url,
            token=token,
            agent_mode=args.agent_mode,
            read_timeout_seconds=args.read_timeout_seconds,
            out_dir=out_dir,
            prefix="sse-baseline",
        )
        summary["reports"].append({"layer": "sse", "duration_seconds": baseline_duration, "path": str(sse_path)})
        if not _sse_should_gate_next_step(sse_report):
            summary["stopped_after"] = f"sse-{baseline_duration}s"
            summary_path = _write_summary(summary, out_dir)
            print(f"staged_summary={summary_path}")
            return 1
    else:
        print("Skipping SSE baseline because no bearer token was provided.\n")
        summary["sse_blocked_reason"] = "Missing bearer token for authenticated SSE benchmark"

    effective_service_overrides = dict(base_env_overrides)
    if args.tune:
        sweep_reports: list[dict[str, Any]] = []
        sweep_records: list[dict[str, Any]] = []
        for concurrency in args.concurrency_sweep:
            tuned_overrides = dict(base_env_overrides)
            tuned_overrides["DIRECTOR_MAX_CONCURRENCY"] = concurrency
            tuned_prompt = build_benchmark_prompt(baseline_duration)
            tuned_report, tuned_path = asyncio.run(
                _run_service_once(
                    duration_seconds=baseline_duration,
                    prompt=tuned_prompt,
                    user_id_prefix=args.user_id_prefix,
                    env_overrides=tuned_overrides,
                    out_dir=out_dir,
                    prefix=f"service-tune-c{concurrency}",
                    require_voiceover=args.require_voiceover,
                )
            )
            summary["reports"].append({"layer": "service", "duration_seconds": baseline_duration, "path": str(tuned_path)})
            sweep_reports.append(tuned_report)
            sweep_records.append(
                {
                    "concurrency": concurrency,
                    "path": str(tuned_path),
                    "success": tuned_report.get("success"),
                    "total_wall_time": tuned_report.get("timings_s", {}).get("total_wall_time"),
                }
            )
        summary["tuning"]["service_concurrency_sweep"] = sweep_records
        best_report = choose_best_service_report(sweep_reports)
        if best_report and best_report.get("env_overrides", {}).get("DIRECTOR_MAX_CONCURRENCY") is not None:
            best_concurrency = int(best_report["env_overrides"]["DIRECTOR_MAX_CONCURRENCY"])
            effective_service_overrides["DIRECTOR_MAX_CONCURRENCY"] = best_concurrency
            summary["recommended_env_overrides"]["DIRECTOR_MAX_CONCURRENCY"] = best_concurrency

    for duration in durations[1:]:
        prompt = build_benchmark_prompt(duration)
        service_report, service_path = asyncio.run(
            _run_service_once(
                duration_seconds=duration,
                prompt=prompt,
                user_id_prefix=args.user_id_prefix,
                env_overrides=effective_service_overrides,
                out_dir=out_dir,
                prefix="service-staged",
                require_voiceover=args.require_voiceover,
            )
        )
        summary["reports"].append({"layer": "service", "duration_seconds": duration, "path": str(service_path)})
        if not _service_should_gate_next_step(service_report):
            summary["stopped_after"] = f"service-{duration}s"
            break

        if token:
            sse_report, sse_path = _run_sse_once(
                duration_seconds=duration,
                prompt=prompt,
                api_base_url=args.api_base_url,
                token=token,
                agent_mode=args.agent_mode,
                read_timeout_seconds=args.read_timeout_seconds,
                out_dir=out_dir,
                prefix="sse-staged",
            )
            summary["reports"].append({"layer": "sse", "duration_seconds": duration, "path": str(sse_path)})
            if not _sse_should_gate_next_step(sse_report):
                summary["stopped_after"] = f"sse-{duration}s"
                break

    summary_path = _write_summary(summary, out_dir)
    print(f"staged_summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
