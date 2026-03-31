# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# =============================================================================
# Stage 1: Builder — install all dependencies
# =============================================================================
FROM python:3.12-slim AS builder

# Install uv
# Pin version here — keep in sync with .uv-version
ARG UV_VERSION=0.8.13
RUN pip install --no-cache-dir uv==${UV_VERSION}

# Install build-time tools for NodeSource GPG-verified apt repo
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg ca-certificates && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy dependency files first (layer cache)
COPY ./pyproject.toml ./README.md ./uv.lock* ./
COPY ./remotion-render/package.json ./remotion-render/package-lock.json ./remotion-render/

# Install Python dependencies
ENV UV_HTTP_TIMEOUT=600
RUN uv sync --frozen

# Install Node dependencies for Remotion
RUN cd /code/remotion-render && npm ci --omit=dev

# =============================================================================
# Stage 2: Runtime — minimal production image
# =============================================================================
FROM python:3.12-slim

# Create non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

# Install only runtime system dependencies (no curl, gnupg, or build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install uv in runtime (needed for `uv run`)
# Pin version here — keep in sync with .uv-version
ARG UV_VERSION=0.8.13
RUN pip install --no-cache-dir uv==${UV_VERSION}

WORKDIR /code

# Copy pre-built dependencies from builder
COPY --from=builder /code/.venv /code/.venv
COPY --from=builder /code/remotion-render/node_modules /code/remotion-render/node_modules
COPY --from=builder /usr/bin/node /usr/bin/node
COPY --from=builder /usr/lib/x86_64-linux-gnu/libnode* /usr/lib/x86_64-linux-gnu/ 2>/dev/null || true

# Copy dependency manifests (needed by uv run)
COPY ./pyproject.toml ./README.md ./uv.lock* ./

# Copy application code
COPY ./app ./app
COPY ./remotion-render ./remotion-render
COPY ./gunicorn.conf.py ./gunicorn.conf.py

# Fix permissions for non-root user
RUN mkdir -p /code/.cache && chown -R appuser:appuser /code

ENV UV_CACHE_DIR=/code/.cache

# Switch to non-privileged user
USER appuser
ENV HOME=/home/appuser

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

# Default port matches docker-compose.yml and local dev.
# Cloud Run deployments override via PORT env var.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
  CMD python -c 'import os, urllib.request; urllib.request.urlopen("http://127.0.0.1:" + os.environ.get("PORT", "8000") + "/health/live", timeout=5)'

# Use gunicorn with uvicorn workers for multi-process production serving.
# All settings (workers, timeouts, bind) are in gunicorn.conf.py.
CMD ["sh", "-c", "uv run gunicorn app.fast_api_app:app --config gunicorn.conf.py"]
