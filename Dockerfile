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

FROM python:3.11-slim


# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Install uv (keep as root for installation to system paths)
RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

# Copy dependency files
COPY ./pyproject.toml ./README.md ./uv.lock* ./

# Install dependencies using cache mount
# Leveraging a cache mount to /root/.cache/uv to speed up subsequent builds
# Increase timeout for large downloads
ENV UV_HTTP_TIMEOUT=600
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Start copying application code
COPY ./app ./app

# Fix permissions for the non-root user
# We need to make sure the user can access what they need
# Also create a cache directory for uv that appuser can write to
RUN mkdir -p /code/.cache && chown -R appuser:appuser /code

# Set UV cache to a writable location
ENV UV_CACHE_DIR=/code/.cache

# Switch to the non-privileged user to run the application.
USER appuser

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

EXPOSE 8080

# Use array syntax for CMD
CMD ["uv", "run", "uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]