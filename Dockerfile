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

FROM python:3.12-slim-bookworm


# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser


# Install uv (keep as root for installation to system paths)
RUN pip install --no-cache-dir uv==0.8.13

# Install Node.js 20.x LTS (pinned) and system dependencies for Remotion (ffmpeg + chrome libs)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y \
    nodejs \
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
    # weasyprint system dependencies (Pango/Cairo for PDF rendering)
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy dependency files
COPY ./pyproject.toml ./README.md ./uv.lock* ./
COPY ./remotion-render/package.json ./remotion-render/package-lock.json ./remotion-render/

# Install Python dependencies
# Increase timeout for large downloads
ENV UV_HTTP_TIMEOUT=600
RUN uv sync --frozen

RUN cd /code/remotion-render && npm ci

# Start copying application code
COPY ./app ./app
COPY ./remotion-render ./remotion-render
COPY ./gunicorn.conf.py ./gunicorn.conf.py

# Fix permissions for the non-root user
# We need to make sure the user can access what they need
# Also create a cache directory for uv that appuser can write to
RUN mkdir -p /code/.cache && chown -R appuser:appuser /code

# Set UV cache to a writable location
ENV UV_CACHE_DIR=/code/.cache

# Switch to the non-privileged user to run the application.
USER appuser
ENV HOME=/home/appuser

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

# Default port matches docker-compose.yml and local dev.
# Cloud Run deployments override via PORT env var.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get("PORT", "8000")}/health/live', timeout=5)"

# Use gunicorn with uvicorn workers for multi-process production serving.
# All settings (workers, timeouts, bind) are in gunicorn.conf.py.
CMD ["sh", "-c", "uv run gunicorn app.fast_api_app:app --config gunicorn.conf.py"]
