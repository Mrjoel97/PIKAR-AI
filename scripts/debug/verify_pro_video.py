import argparse
import asyncio
import logging
import sys
import time
import traceback
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from app.services.long_video_benchmark import (
    DEFAULT_SERVICE_BENCHMARK_TIMEOUT_SECONDS,
    build_benchmark_prompt,
    build_env_overrides,
    build_service_crash_report,
    format_report_summary,
    is_healthy_report,
    run_service_benchmark,
    write_benchmark_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Service-level long-video smoke benchmark.")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--prompt", help="Optional explicit prompt for the benchmark run.")
    parser.add_argument("--user-id-prefix", default="verify-pro-video")
    parser.add_argument("--director-max-concurrency", type=int, default=None)
    parser.add_argument("--veo-poll-interval", type=int, default=None)
    parser.add_argument("--veo-poll-interval-min", type=int, default=None)
    parser.add_argument("--veo-poll-interval-max", type=int, default=None)
    parser.add_argument("--benchmark-timeout", type=int, default=DEFAULT_SERVICE_BENCHMARK_TIMEOUT_SECONDS)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--require-voiceover", action="store_true", help="Fail if generated scenes are missing voiceover.")
    return parser.parse_args()


async def _run() -> int:
    args = parse_args()
    prompt = args.prompt or build_benchmark_prompt(args.duration)
    env_overrides = build_env_overrides(
        director_max_concurrency=args.director_max_concurrency,
        veo_poll_interval=args.veo_poll_interval,
        veo_poll_interval_min=args.veo_poll_interval_min,
        veo_poll_interval_max=args.veo_poll_interval_max,
    )
    started_at_iso = datetime.now(timezone.utc).isoformat()
    started_at = time.perf_counter()

    try:
        report = await run_service_benchmark(
            duration_seconds=args.duration,
            prompt=prompt,
            user_id_prefix=args.user_id_prefix,
            env_overrides=env_overrides,
            benchmark_timeout_seconds=args.benchmark_timeout,
            require_voiceover=args.require_voiceover,
        )
    except BaseException as exc:
        report = build_service_crash_report(
            duration_seconds=args.duration,
            prompt=prompt,
            user_id_prefix=args.user_id_prefix,
            env_overrides=env_overrides,
            started_at_iso=started_at_iso,
            total_wall_time_s=time.perf_counter() - started_at,
            error=str(exc),
            traceback_text=traceback.format_exc(),
        )

    report_path = write_benchmark_report(report, out_dir=args.out_dir, prefix="verify-pro-video")
    print(format_report_summary(report, report_path=report_path))
    return 0 if is_healthy_report(report) else 1


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    raise SystemExit(asyncio.run(_run()))
