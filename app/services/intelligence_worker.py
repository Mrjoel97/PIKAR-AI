# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Background worker that consumes research events and executes jobs.

Can run as:
1. Standalone process: python -m app.services.intelligence_worker
2. Background task in FastAPI lifespan (for simpler deployments)

Consumes from the Redis Streams event bus and routes events to the
intelligence scheduler's _execute_research_job function.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal

logger = logging.getLogger(__name__)

MAX_CONCURRENT = int(os.getenv("RESEARCH_MAX_CONCURRENT", "3"))
POLL_INTERVAL = int(os.getenv("RESEARCH_POLL_INTERVAL", "5"))


class IntelligenceWorker:
    """Consumes research events and executes research jobs."""

    def __init__(self) -> None:
        self.running = False
        self._active_jobs = 0
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self._tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start the event consumption loop."""
        self.running = True
        logger.info(
            "Intelligence worker started (max_concurrent=%d, poll_interval=%ds)",
            MAX_CONCURRENT,
            POLL_INTERVAL,
        )

        from app.services.research_event_bus import get_event_bus

        bus = get_event_bus()

        while self.running:
            try:
                events = await bus.consume_batch(
                    max_events=MAX_CONCURRENT - self._active_jobs,
                    block_ms=POLL_INTERVAL * 1000,
                )

                for event in events:
                    task = asyncio.create_task(self._process_event(event, bus))
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)

            except asyncio.CancelledError:
                logger.info("Intelligence worker cancelled")
                break
            except Exception as e:
                logger.error("Worker loop error: %s", e)
                await asyncio.sleep(POLL_INTERVAL)

        logger.info("Intelligence worker stopped")

    async def stop(self) -> None:
        """Signal the worker to stop."""
        self.running = False

    async def _process_event(self, event: dict, bus) -> None:
        """Process a single research event."""
        async with self._semaphore:
            self._active_jobs += 1
            try:
                from app.services.intelligence_scheduler import _execute_research_job

                result = await _execute_research_job(
                    query=event.get("topic", ""),
                    domain=event.get("domain", "general"),
                    depth=event.get("suggested_depth", "standard"),
                    triggered_by=event.get("trigger_type", "event"),
                )

                # Acknowledge the event
                msg_id = event.get("_msg_id")
                if msg_id:
                    await bus.acknowledge(msg_id)

                if result.get("success"):
                    logger.info(
                        "Research event processed: %s/%s (%d findings, $%.4f)",
                        event.get("domain"),
                        event.get("topic", "")[:40],
                        result.get("findings", 0),
                        result.get("cost_usd", 0),
                    )
                else:
                    logger.warning(
                        "Research event failed: %s/%s — %s",
                        event.get("domain"),
                        event.get("topic", "")[:40],
                        result.get("error"),
                    )

            except Exception as e:
                logger.error("Event processing error: %s", e)
            finally:
                self._active_jobs -= 1


async def main():
    """Entry point for standalone worker process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    worker = IntelligenceWorker()

    shutdown_tasks: set[asyncio.Task] = set()

    def _request_shutdown() -> None:
        task = asyncio.create_task(worker.stop())
        shutdown_tasks.add(task)
        task.add_done_callback(shutdown_tasks.discard)

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
