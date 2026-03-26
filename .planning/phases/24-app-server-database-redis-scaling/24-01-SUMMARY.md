---
phase: 24
plan: "01"
title: "Gunicorn Multi-Worker Server"
status: complete
started: "2026-03-25"
completed: "2026-03-25"
duration_minutes: 15
---

## What Was Built

Replaced single-worker uvicorn with Gunicorn process manager running 4+ uvicorn workers. Created `gunicorn.conf.py` with full production configuration: crash recovery, per-worker concurrency caps, keep-alive timeout, graceful shutdown (30s) for SSE connection draining, and worker restart after 1000 requests to prevent memory leaks.

## Key Files

### Created
- `gunicorn.conf.py` — Full production config: workers, timeouts, graceful shutdown, max_requests

### Modified
- `Dockerfile` — CMD changed to `gunicorn --config gunicorn.conf.py`, added COPY for config file
- `pyproject.toml` — Added `gunicorn>=23.0.0,<24.0.0` dependency

## Requirements Covered

- SERV-01: 4+ workers via WEB_CONCURRENCY env var
- SERV-02: Gunicorn auto-restarts crashed workers
- SERV-03: worker_connections caps concurrency per worker
- SERV-04: keepalive + timeout prevent hanging connections
- SERV-05: graceful_timeout=30 drains SSE before SIGKILL

## Decisions

- No `preload_app=True` — breaks asyncio loop isolation for ADK Runner and StitchMCP
- `max_requests=1000` with jitter prevents gradual memory leaks
