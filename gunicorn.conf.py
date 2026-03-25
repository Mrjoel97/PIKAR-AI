"""Gunicorn configuration for pikar-ai production server.

Reads all values from environment variables with sensible production defaults.
Worker count: WEB_CONCURRENCY (default: 4).
Worker class: uvicorn.workers.UvicornWorker (ASGI-compatible).
Graceful timeout: GRACEFUL_TIMEOUT_SECONDS (default: 30) — workers finish
in-flight requests (including SSE streams) before SIGKILL.
"""

import os

# ---------------------------------------------------------------------------
# Worker count
# ---------------------------------------------------------------------------
# WEB_CONCURRENCY is the Cloud Run / Heroku standard env var for worker count.
# Default 4 workers gives 4x throughput with automatic crash recovery.
workers = int(os.environ.get("WEB_CONCURRENCY", "4"))

# ---------------------------------------------------------------------------
# Worker class — must be uvicorn's ASGI worker
# ---------------------------------------------------------------------------
worker_class = "uvicorn.workers.UvicornWorker"

# ---------------------------------------------------------------------------
# Concurrency cap per worker (SERV-03)
# ---------------------------------------------------------------------------
# Prevents a single worker from accepting unlimited connections and exhausting
# thread/connection pools. Default 1000 is generous but prevents runaway.
# Maps to uvicorn's --limit-concurrency.
worker_connections = int(os.environ.get("WORKER_CONNECTIONS", "1000"))

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
# SERV-04: Keep-alive timeout prevents idle connections hanging indefinitely.
keepalive = int(os.environ.get("KEEPALIVE_TIMEOUT", "5"))

# Graceful shutdown (SERV-05): workers have this many seconds to drain
# active SSE connections before Gunicorn sends SIGKILL.
# Must be > longest expected SSE stream duration but < Cloud Run shutdown timeout (600s).
# Default 30s is appropriate for agent streaming responses.
graceful_timeout = int(os.environ.get("GRACEFUL_TIMEOUT_SECONDS", "30"))

# Overall request timeout — kills hung requests regardless of keep-alive.
timeout = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "120"))

# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------
# Cloud Run passes PORT env var. Bind to 0.0.0.0 so the container is reachable.
port = os.environ.get("PORT", "8000")
bind = f"0.0.0.0:{port}"

# ---------------------------------------------------------------------------
# Process naming and logging
# ---------------------------------------------------------------------------
proc_name = "pikar-ai"
accesslog = "-"   # stdout
errorlog = "-"    # stderr
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# ---------------------------------------------------------------------------
# Worker restart — prevents memory leaks from accumulating indefinitely
# ---------------------------------------------------------------------------
# Restart workers after this many requests (0 = disabled). Restart is graceful.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "100"))
