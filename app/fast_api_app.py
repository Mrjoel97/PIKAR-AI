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

import sys

if sys.platform == "win32":
    import asyncio as _asyncio

    _asyncio.set_event_loop_policy(_asyncio.WindowsProactorEventLoopPolicy())

import concurrent.futures
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

# Load env: project root .env first (Docker mounts it at /code/.env), then app/.env
_app_dir = Path(__file__).resolve().parent
_project_root = _app_dir.parent
_root_env = _project_root / ".env"
if _root_env.exists():
    load_dotenv(_root_env)
load_dotenv(_app_dir / ".env")
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

# =============================================================================
# Google AI Authentication Configuration
# =============================================================================
# Priority order:
# 1. Vertex AI via explicit service account JSON (GOOGLE_APPLICATION_CREDENTIALS + GOOGLE_CLOUD_PROJECT)
# 2. Vertex AI via Cloud Run / GCE Application Default Credentials (GOOGLE_CLOUD_PROJECT only)
# 3. Gemini API Key (GOOGLE_API_KEY) - Fallback mode for local dev
# =============================================================================

_app_dir = Path(__file__).resolve().parent
_project_root = _app_dir.parent

_credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if _credentials_path and not os.path.isabs(_credentials_path):
    _resolved = (
        _project_root / _credentials_path.replace("\\", "/").lstrip("./")
    ).resolve()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(_resolved)

has_vertex_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
has_api_key = os.environ.get("GOOGLE_API_KEY")
has_cloud_project = os.environ.get("GOOGLE_CLOUD_PROJECT")

# Detect Cloud Run / GCE environment (ADC is available without explicit credentials file)
_on_gcp = bool(os.environ.get("K_SERVICE") or os.environ.get("GOOGLE_CLOUD_RUN"))

if has_cloud_project and has_vertex_credentials:
    # Explicit service account JSON — local dev or mounted secret
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
    logging.info(
        f"Vertex AI mode enabled using service account credentials. Project: {has_cloud_project}"
    )
elif has_cloud_project and _on_gcp:
    # Cloud Run / GCE: ADC is provided by the metadata server automatically
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
    logging.info(
        f"Vertex AI mode enabled via Cloud Run ADC. Project: {has_cloud_project}"
    )
elif has_api_key:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"
    logging.info("Gemini API Key mode enabled.")
else:
    logging.error("No Google AI credentials found!")
    logging.error(
        "Set GOOGLE_APPLICATION_CREDENTIALS + GOOGLE_CLOUD_PROJECT or GOOGLE_API_KEY."
    )

# Configure logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# Environment Validation (Critical for Production Security)
# =============================================================================
# Validate required environment variables at startup.
# This ensures the application fails fast with clear error messages
# when critical configuration is missing.
# =============================================================================
BYPASS_IMPORT = os.environ.get("LOCAL_DEV_BYPASS") == "1"
SKIP_VALIDATION = os.environ.get("SKIP_ENV_VALIDATION") == "1"

# Never allow validation bypass in production
_IS_PRODUCTION = os.environ.get("ENVIRONMENT", "development").lower() in ("production", "prod")
if _IS_PRODUCTION and (SKIP_VALIDATION or BYPASS_IMPORT):
    logger.warning(
        "SKIP_ENV_VALIDATION or LOCAL_DEV_BYPASS set in production — ignoring bypass flags"
    )
    SKIP_VALIDATION = False
    BYPASS_IMPORT = False

if not SKIP_VALIDATION and not BYPASS_IMPORT:
    try:
        from app.config.validation import validate_startup

        validate_startup()
    except ImportError:
        logger.warning("Environment validation module not found, skipping validation")
    except Exception as e:
        # Log but don't fail in development - let the error be clear
        logger.error(f"Environment validation failed: {e}")
        # In production, we want to fail fast
        if os.environ.get("ENVIRONMENT", "development").lower() in (
            "production",
            "prod",
        ):
            raise
if not BYPASS_IMPORT:
    try:
        from a2a.server.apps import A2AFastAPIApplication
        from a2a.server.request_handlers import DefaultRequestHandler
        from a2a.types import AgentCapabilities, AgentCard
        from a2a.utils.constants import (
            AGENT_CARD_WELL_KNOWN_PATH,
            EXTENDED_AGENT_CARD_PATH,
        )

        A2A_AVAILABLE = True
    except Exception as e:
        logger.warning(f"A2A components not available: {e}")
        A2A_AVAILABLE = False
else:
    A2A_AVAILABLE = False

if not BYPASS_IMPORT:
    from app.persistence.supabase_task_store import SupabaseTaskStore
else:

    class SupabaseTaskStore:
        pass


from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.services.sse_connection_limits import (
    SSERejectReason,
    get_sse_connection_limit,
    get_total_active_sse_count,
    release_sse_connection,
    try_acquire_sse_connection,
)

if not BYPASS_IMPORT:
    try:
        from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
        from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder

        A2A_COMPONENTS_AVAILABLE = True
    except Exception as e:
        logger.warning(f"A2A executor components not available: {e}")
        A2A_COMPONENTS_AVAILABLE = False

    try:
        from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        ADK_CORE_AVAILABLE = True
    except Exception as e:
        logger.warning(f"ADK core components not available: {e}")
        ADK_CORE_AVAILABLE = False
else:
    A2A_COMPONENTS_AVAILABLE = False
    ADK_CORE_AVAILABLE = False

if not BYPASS_IMPORT:
    try:
        from google.cloud import logging as google_cloud_logging
    except Exception:  # pragma: no cover - optional runtime dependency.
        google_cloud_logging = None
else:
    google_cloud_logging = None

if not BYPASS_IMPORT:
    from app.agent import app as adk_app
    from app.agent import app_fallback as adk_app_fallback
else:

    class MockAdkApp:
        name = "pikar-ai"
        root_agent = None

    adk_app = MockAdkApp()
    adk_app_fallback = None

from app.app_utils.auth import verify_token
from app.app_utils.typing import Feedback

# Import persistent session service (with fallback to InMemory for local dev)
if not BYPASS_IMPORT:
    try:
        from app.persistence.supabase_session_service import SupabaseSessionService

        session_service = SupabaseSessionService()
    except Exception as e:
        logger.warning(
            f"Failed to initialize SupabaseSessionService, falling back to InMemory: {e}"
        )
        session_service = InMemorySessionService()
else:

    class MockSessionService:
        pass

    session_service = MockSessionService()

# setup_telemetry()
# _, project_id = google.auth.default()
# logging_client = google_cloud_logging.Client()
# logger = logging_client.logger(__name__)

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
if ADK_CORE_AVAILABLE:
    artifact_service = (
        GcsArtifactService(bucket_name=logs_bucket_name)
        if logs_bucket_name
        else InMemoryArtifactService()
    )
else:
    artifact_service = None

if ADK_CORE_AVAILABLE:
    runner = Runner(
        app=adk_app,
        artifact_service=artifact_service,
        session_service=session_service,  # Now uses Supabase-backed sessions
    )
    if adk_app_fallback is not None:
        try:
            runner_fallback = Runner(
                app=adk_app_fallback,
                artifact_service=artifact_service,
                session_service=session_service,
            )
        except Exception as e:
            logger.warning(f"Fallback runner not available: {e}")
            runner_fallback = None
    else:
        runner_fallback = None
else:
    runner = None
    runner_fallback = None

if A2A_AVAILABLE and A2A_COMPONENTS_AVAILABLE and ADK_CORE_AVAILABLE:
    try:
        _task_store = SupabaseTaskStore()
    except Exception as e:
        logger.warning(
            f"Failed to initialize SupabaseTaskStore, using InMemoryTaskStore: {e}"
        )
        try:
            from a2a.server.tasks import InMemoryTaskStore

            _task_store = InMemoryTaskStore()
        except ImportError:
            # a2a library version on this deployment does not export InMemoryTaskStore;
            # disable A2A rather than crashing the server.
            logger.warning(
                "InMemoryTaskStore not available in installed a2a version — disabling A2A features"
            )
            _task_store = None
    if _task_store is not None:
        try:
            request_handler = DefaultRequestHandler(
                agent_executor=A2aAgentExecutor(runner=runner),
                task_store=_task_store,
            )
            A2A_RPC_PATH = f"/a2a/{adk_app.name}"
        except Exception as e:
            logger.warning(f"A2A request handler init failed: {e}")
            request_handler = None
            A2A_RPC_PATH = None
    else:
        request_handler = None
        A2A_RPC_PATH = None
else:
    request_handler = None
    A2A_RPC_PATH = None

from datetime import datetime, timezone

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.middleware.rate_limiter import (
    _parse_limit_int,
    build_rate_limit_headers,
    get_user_persona_limit,
    limiter,
    redis_sliding_window_check,
)
from app.middleware.security_headers import SecurityHeadersMiddleware
from starlette.middleware.base import BaseHTTPMiddleware as _BaseHTTPMiddleware
from starlette.requests import Request as _StarletteRequest
from starlette.responses import JSONResponse as _JSONResponse
from starlette.responses import Response as _Response


class RateLimitHeaderMiddleware(_BaseHTTPMiddleware):
    """Primary distributed rate limit enforcer + header injector.

    Enforces per-user rate limits using Redis sliding window as the
    authoritative check across all replicas (RATE-01, RATE-04).
    Also injects X-RateLimit-* headers into any 429 response.
    """

    # Paths that bypass rate limiting (health checks, auth, static)
    BYPASS_PREFIXES = ("/health", "/docs", "/openapi", "/auth/", "/static/")

    async def dispatch(self, request: _StarletteRequest, call_next) -> _Response:
        """Enforce distributed rate limit before forwarding the request."""
        import time as _time

        path = request.url.path

        # Skip bypass paths
        if any(path.startswith(pfx) for pfx in self.BYPASS_PREFIXES):
            return await call_next(request)

        # Extract user identity from request state (set by auth middleware upstream)
        # Fall back to IP if no authenticated user
        user_id: str | None = getattr(request.state, "user_id", None)
        if user_id is None:
            # Not authenticated — let auth middleware handle 401; skip rate check
            response = await call_next(request)
            return self._inject_headers(response)

        # Determine persona limit for this user
        limit_str = get_user_persona_limit(request)  # returns e.g. "10/minute"
        limit_int = _parse_limit_int(limit_str)

        # PRIMARY DISTRIBUTED ENFORCEMENT: Redis sliding window
        allowed, limit_val, remaining, reset_at = await redis_sliding_window_check(
            user_id, limit=limit_int, window_seconds=60
        )

        if not allowed:
            headers = build_rate_limit_headers(limit_val, 0, reset_at)
            return _JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Limit: {limit_val}/minute."},
                headers=headers,
            )

        # Proceed with request; inject rate-limit headers into response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit_val)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return self._inject_headers(response, limit_val, remaining, reset_at)

    @staticmethod
    def _inject_headers(
        response: _Response,
        limit: int = 10,
        remaining: int = 0,
        reset_at: int | None = None,
    ) -> _Response:
        """Add X-RateLimit-* headers to 429 responses that lack them."""
        import time as _time

        if response.status_code == 429:
            if "X-RateLimit-Limit" not in response.headers:
                now = int(_time.time())
                rt = reset_at if reset_at else ((now // 60) + 1) * 60
                retry_after = max(1, rt - now)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["Retry-After"] = str(retry_after)
        return response


async def build_dynamic_agent_card() -> Optional["AgentCard"]:
    """Builds the Agent Card dynamically from the root_agent."""
    if not A2A_AVAILABLE or not A2A_COMPONENTS_AVAILABLE or not ADK_CORE_AVAILABLE:
        return None
    agent_card_builder = AgentCardBuilder(
        agent=adk_app.root_agent,
        capabilities=AgentCapabilities(streaming=True),
        rpc_url=f"{os.getenv('APP_URL', 'http://0.0.0.0:8000')}{A2A_RPC_PATH}",
        agent_version=os.getenv("AGENT_VERSION", "0.1.0"),
    )
    agent_card = await agent_card_builder.build()
    return agent_card


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    # DBSC-01: Size the asyncio default thread pool for high-concurrency Supabase calls.
    # Python's default is min(32, cpu_count + 4), which is ~8-12 on Cloud Run instances.
    # At 1000+ concurrent users, asyncio.to_thread() calls queue behind each other.
    _thread_pool_size = int(os.environ.get("THREAD_POOL_SIZE", "200"))
    _thread_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=_thread_pool_size,
        thread_name_prefix="pikar-worker",
    )
    import asyncio as _asyncio_thread

    _loop = _asyncio_thread.get_event_loop()
    _loop.set_default_executor(_thread_executor)
    logger.info("Thread pool executor set to %s workers", _thread_pool_size)
    app_instance.state.thread_pool_size = _thread_pool_size

    # Pre-warm Redis connection pool at startup
    if not BYPASS_IMPORT:
        try:
            from app.services.cache import get_cache_service

            cache = get_cache_service()
            await cache.prewarm()
        except Exception as e:
            logger.warning(f"Redis pre-warm failed (non-fatal): {e}")
    else:
        logger.info("Skipping Redis pre-warm in LOCAL_DEV_BYPASS mode")

    if A2A_AVAILABLE and A2A_COMPONENTS_AVAILABLE and ADK_CORE_AVAILABLE:
        try:
            agent_card = await build_dynamic_agent_card()
            a2a_app = A2AFastAPIApplication(
                agent_card=agent_card, http_handler=request_handler
            )
            a2a_app.add_routes_to_app(
                app_instance,
                agent_card_url=f"{A2A_RPC_PATH}{AGENT_CARD_WELL_KNOWN_PATH}",
                rpc_url=A2A_RPC_PATH,
                extended_agent_card_url=f"{A2A_RPC_PATH}{EXTENDED_AGENT_CARD_PATH}",
            )
            logger.info("A2A routes initialized successfully")
        except Exception as e:
            logger.warning(
                f"A2A initialization failed (non-fatal): {e}. App will continue without A2A features."
            )

    # --- Stitch MCP singleton startup ---
    import asyncio as _asyncio_lifespan

    import app.services.stitch_mcp as _stitch_module

    _stitch_task = None
    if not BYPASS_IMPORT and os.environ.get("STITCH_API_KEY"):
        _stitch_module._stitch_service = _stitch_module.StitchMCPService()
        _stitch_task = _asyncio_lifespan.create_task(
            _stitch_module._stitch_service._run(),
            name="stitch-mcp-singleton",
        )
        try:
            await _asyncio_lifespan.wait_for(
                _asyncio_lifespan.shield(_stitch_module._stitch_service._ready.wait()),
                timeout=30.0,
            )
            logger.info("StitchMCPService initialized successfully")
        except _asyncio_lifespan.TimeoutError:
            logger.warning(
                "StitchMCPService did not become ready within 30s — Stitch features disabled"
            )
    else:
        logger.info("STITCH_API_KEY not set — StitchMCPService not started")

    yield

    # Shutdown thread executor cleanly
    _thread_executor.shutdown(wait=False, cancel_futures=False)
    logger.info("Thread pool executor shutdown initiated")

    # --- Stitch MCP singleton shutdown ---
    if _stitch_task and not _stitch_task.done():
        _stitch_task.cancel()
        try:
            await _stitch_task
        except _asyncio_lifespan.CancelledError:
            pass
        logger.info("StitchMCPService stopped cleanly")


app = FastAPI(
    title="pikar-ai",
    description="API for interacting with the Agent pikar-ai",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
from app.middleware.onboarding_guard import OnboardingGuardMiddleware

app.add_middleware(OnboardingGuardMiddleware)
# RateLimitHeaderMiddleware added AFTER SlowAPIMiddleware so it runs FIRST (LIFO order).
# It is the authoritative distributed Redis enforcer for all authenticated requests.
app.add_middleware(RateLimitHeaderMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> _JSONResponse:
    """Return 429 with standard rate-limit headers for slowapi-triggered limits.

    This fires for the per-process slowapi check (inner layer). The Redis
    middleware (outer layer) handles the distributed cross-replica enforcement.
    """
    import time as _exc_time

    limit_str = str(getattr(exc, "detail", "rate limit exceeded"))
    limit_val = 10
    try:
        parts = limit_str.split()
        if parts:
            limit_val = int(parts[0])
    except (ValueError, IndexError):
        pass
    now = int(_exc_time.time())
    window_reset = ((now // 60) + 1) * 60
    retry_after = max(1, window_reset - now)
    return _JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {limit_str}"},
        headers={
            "X-RateLimit-Limit": str(limit_val),
            "X-RateLimit-Remaining": "0",
            "Retry-After": str(retry_after),
        },
    )

# =============================================================================
# Global Exception Handlers
# =============================================================================
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import (
    ErrorCode,
    ErrorResponse,
    PikarError,
)


def _add_cors_headers(request: Request, response: JSONResponse) -> JSONResponse:
    """Inject CORS headers into exception-handler responses.

    Starlette's CORSMiddleware may not stamp responses created by
    ``add_exception_handler`` callbacks, leaving the browser to block
    error bodies on cross-origin requests.  This helper mirrors the
    allowed-origin logic so every error response is readable by the
    frontend.
    """
    origin = request.headers.get("origin")
    if origin and origin in _cors_allowed_origins:
        response.headers["access-control-allow-origin"] = origin
        if _cors_allow_credentials:
            response.headers["access-control-allow-credentials"] = "true"
        response.headers.setdefault("vary", "Origin")
    return response


async def pikar_error_handler(request: Request, exc: PikarError) -> JSONResponse:
    """Handle PikarError exceptions with structured error responses."""
    error_response = ErrorResponse.from_exception(
        exc, request_id=getattr(request.state, "request_id", None)
    )
    return _add_cors_headers(
        request,
        JSONResponse(
            status_code=exc.status_code,
            content=error_response.to_dict(),
        ),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTPException with structured error responses."""
    detail_payload = exc.detail
    message: str
    details: dict | None = None

    if isinstance(detail_payload, dict):
        detail_message = detail_payload.get("message")
        message = (
            detail_message
            if isinstance(detail_message, str) and detail_message.strip()
            else "Request failed"
        )
        details = {k: v for k, v in detail_payload.items() if k != "message"} or None
    elif detail_payload is None:
        message = "Request failed"
    else:
        message = str(detail_payload)

    error_response = ErrorResponse(
        code=ErrorCode.UNKNOWN_ERROR.value,
        message=message,
        details=details,
        request_id=getattr(request.state, "request_id", None),
    )
    return _add_cors_headers(
        request,
        JSONResponse(
            status_code=exc.status_code,
            content=error_response.to_dict(),
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors with structured error responses."""
    errors = []
    for error in exc.errors():
        loc = error.get("loc", [])
        errors.append(
            {
                "field": ".".join(str(l) for l in loc[1:]) if loc else None,
                "reason": error.get("msg", "validation error"),
                "type": error.get("type"),
            }
        )

    error_response = ErrorResponse(
        code=ErrorCode.VALIDATION_ERROR.value,
        message="Request validation failed",
        details={"validation_errors": errors},
        request_id=getattr(request.state, "request_id", None),
    )
    return _add_cors_headers(
        request,
        JSONResponse(
            status_code=400,
            content=error_response.to_dict(),
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle generic exceptions with sanitized error responses.

    This handler catches any unhandled exceptions and returns a sanitized
    response to avoid leaking internal details in production.
    """
    # Log the full exception for debugging
    logger.exception(f"Unhandled exception in {request.method} {request.url.path}")

    # Determine if we're in debug mode
    debug_mode = os.environ.get("DEBUG", "false").lower() == "true"

    if debug_mode:
        # In debug mode, include more details
        error_response = ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR.value,
            message=str(exc),
            details={"exception_type": type(exc).__name__},
            request_id=getattr(request.state, "request_id", None),
        )
    else:
        # In production, sanitize the response
        error_response = ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR.value,
            message="An internal error occurred. Please try again later.",
            request_id=getattr(request.state, "request_id", None),
        )

    return _add_cors_headers(
        request,
        JSONResponse(
            status_code=500,
            content=error_response.to_dict(),
        ),
    )


# Register the exception handlers
app.add_exception_handler(PikarError, pikar_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# NOTE: Middleware execution order is LIFO (last added = outermost = runs first).
# CORS must be outermost so preflight requests are handled before anything else.

# #region agent log - Request logging middleware
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging with context tracking.

    Adds request_id, user_id, and session_id to all logs for debugging.
    """

    async def dispatch(self, request: StarletteRequest, call_next):
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract user_id from headers or auth if available
        user_id = request.headers.get("x-user-id") or request.headers.get("user-id")
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id
        request.state.user_id = user_id

        # Extract session_id if available
        session_id = request.headers.get("x-session-id") or request.headers.get(
            "session-id"
        )
        if hasattr(request.state, "session_id"):
            session_id = request.state.session_id
        request.state.session_id = session_id

        # Skip verbose logging for health checks to reduce log noise
        if request.url.path.startswith("/health"):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Log request with context
        logger.info(
            f"[REQ] {request.method} {request.url.path} "
            f"RequestID: {request_id} "
            f"UserID: {user_id or 'anonymous'} "
            f"SessionID: {session_id or 'N/A'} "
            f"Origin: {request.headers.get('origin', 'N/A')}"
        )

        response = await call_next(request)

        # Log response with context
        logger.info(
            f"[RES] {response.status_code} {request.method} {request.url.path} "
            f"RequestID: {request_id}"
        )

        # Add request ID to response headers for client correlation
        response.headers["X-Request-ID"] = request_id

        return response


app.add_middleware(RequestLoggingMiddleware)
# #endregion


# CORS configuration from env (comma-separated origins).
# Example: ALLOWED_ORIGINS=http://localhost:3000,https://app.example.com
def _parse_allowed_origins() -> list[str]:
    raw = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["http://localhost:3000"]


def _is_production_environment() -> bool:
    env = (
        (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "development").strip().lower()
    )
    return env in {"production", "prod"}


_cors_allowed_origins = _parse_allowed_origins()
_cors_allow_credentials = True
if "*" in _cors_allowed_origins:
    if _is_production_environment():
        raise RuntimeError(
            "ALLOWED_ORIGINS cannot contain '*' in production. Configure explicit browser origins instead."
        )
    # Wildcard origins are incompatible with credentialed browser requests.
    # If wildcard is explicitly configured outside production, disable credentials to avoid unsafe/invalid behavior.
    logger.warning(
        "ALLOWED_ORIGINS contains '*'; disabling CORS credentials for browser safety."
    )
    _cors_allow_credentials = False
    _cors_allowed_origins = ["*"]

# CORS remains outside the application stack so preflight requests are handled before routers.
_cors_allowed_methods = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]
_cors_allowed_headers = [
    "Authorization",
    "Content-Type",
    "X-Requested-With",
    "Accept",
    "Origin",
    "X-Request-ID",
    "X-Session-ID",
    "Cache-Control",
    "x-pikar-persona",
    "x-user-id",
    "user-id",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=_cors_allowed_methods,
    allow_headers=_cors_allowed_headers,
)
# Security headers wrap CORS so every response, including preflight responses, is stamped.
app.add_middleware(SecurityHeadersMiddleware)

# Register scheduled endpoints router for Cloud Scheduler
from app.routers.a2a import router as a2a_router
from app.routers.account import router as account_router
from app.routers.admin import admin_router
from app.routers.api_credentials import router as api_credentials_router
from app.routers.app_builder import router as app_builder_router
from app.routers.approvals import router as approvals_router
from app.routers.briefing import router as briefing_router
from app.routers.community import router as community_router
from app.routers.compliance import router as compliance_router
from app.routers.configuration import router as configuration_router
from app.routers.content import router as content_router
from app.routers.departments import router as departments_router
from app.routers.files import router as files_router
from app.routers.finance import router as finance_router
from app.routers.initiatives import router as initiatives_router
from app.routers.learning import router as learning_router
from app.routers.onboarding import router as onboarding_router
from app.routers.org import router as org_router
from app.routers.pages import router as pages_router
from app.routers.reports import router as reports_router
from app.routers.sales import router as sales_router
from app.routers.self_improvement import router as self_improvement_router
from app.routers.support import router as support_router
from app.routers.vault import router as vault_router
from app.routers.voice_session import router as voice_router
from app.routers.webhooks import router as webhooks_router
from app.routers.workflow_triggers import router as workflow_triggers_router
from app.routers.workflows import router as workflows_router
from app.services.scheduled_endpoints import router as scheduled_router

app.include_router(scheduled_router)
app.include_router(files_router, tags=["Files"])
app.include_router(approvals_router, tags=["Approvals"])
app.include_router(org_router, tags=["Organization"])
app.include_router(briefing_router, tags=["Briefing"])
app.include_router(departments_router, tags=["Departments"])
app.include_router(pages_router, tags=["Pages"])
app.include_router(app_builder_router, tags=["App Builder"])
app.include_router(onboarding_router)
app.include_router(workflows_router, tags=["Workflows"])
app.include_router(workflow_triggers_router, tags=["Workflow Triggers"])
app.include_router(vault_router, tags=["Vault"])
app.include_router(configuration_router, tags=["Configuration"])
app.include_router(self_improvement_router, tags=["Self-Improvement"])
app.include_router(initiatives_router, tags=["Initiatives"])
app.include_router(reports_router, tags=["Reports"])
app.include_router(voice_router, tags=["Voice"])
app.include_router(support_router, tags=["Support"])
app.include_router(learning_router, tags=["Learning"])
app.include_router(community_router, tags=["Community"])
app.include_router(account_router, tags=["Account"])
app.include_router(a2a_router, tags=["A2A Protocol"])
app.include_router(webhooks_router, tags=["Webhooks"])
app.include_router(finance_router)
app.include_router(sales_router)
app.include_router(compliance_router)
app.include_router(content_router)
app.include_router(api_credentials_router)
app.include_router(admin_router)


def _log_feedback_payload(payload: dict) -> None:
    """Log feedback payload with compatibility across logger backends."""
    if hasattr(logger, "log_struct"):
        logger.log_struct(payload, severity="INFO")
        return

    import json as _json

    logger.info("feedback=%s", _json.dumps(payload, default=str))


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    _log_feedback_payload(feedback.model_dump())
    return {"status": "success"}


@app.get("/health/startup", tags=["Health"])
async def health_startup():
    """Startup probe for Cloud Run.

    Checks that critical dependencies are reachable:
    - Supabase connection
    - Redis connection (if configured)
    - Gemini API key present

    Returns 200 only when the app is ready to serve traffic.
    Returns 503 if any critical dependency is unavailable.
    """
    checks: dict[str, str] = {}
    all_ok = True

    # Check Supabase
    try:
        from app.services.supabase import get_service_client

        client = get_service_client()
        # Simple query to verify connection
        client.table("sessions").select("session_id").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as e:
        checks["supabase"] = f"error: {e}"
        all_ok = False

    # Check Gemini API key
    has_api_key = bool(
        os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )
    checks["gemini_credentials"] = "ok" if has_api_key else "missing"
    if not has_api_key:
        all_ok = False

    # Check Redis (non-critical — app degrades gracefully via circuit breaker)
    try:
        from app.services.cache import get_cache_service

        cache = get_cache_service()
        if cache._connected:
            checks["redis"] = "ok"
        else:
            checks["redis"] = "not connected (non-critical)"
    except Exception:
        checks["redis"] = "not available (non-critical)"

    status_code = 200 if all_ok else 503
    return JSONResponse(
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
        status_code=status_code,
    )


@app.get("/health/live", tags=["Health"])
async def get_liveness():
    """Fast liveness probe for container healthchecks.

    Keep this endpoint dependency-free so Docker can quickly mark the
    container healthy after restart even when downstream services are warming up.
    """
    from datetime import datetime, timezone

    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health/connections", tags=["Health"])
async def get_connection_pool_health():
    """Monitor Supabase connection pool stats and cache health."""
    from datetime import datetime, timezone

    required_env = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    optional_critical_env = [
        "WORKFLOW_STRICT_TOOL_RESOLUTION",
        "WORKFLOW_ENFORCE_READINESS_GATE",
        "BACKEND_API_URL",
        "WORKFLOW_ALLOW_FALLBACK_SIMULATION",
        "WORKFLOW_SERVICE_SECRET",
    ]
    missing_required_env = [k for k in required_env if not os.getenv(k)]
    missing_critical_env = [k for k in optional_critical_env if not os.getenv(k)]
    try:
        from app.rag.knowledge_vault import get_rag_client_stats, get_supabase_client
        from app.services.supabase import get_client_stats, get_service_client
        from app.services.supabase_async import execute_async

        service_stats = get_client_stats()
        rag_stats = get_rag_client_stats()

        # Verify Service Client Connectivity
        try:
            service_client = get_service_client()
            if not service_client:
                raise ValueError("Service client failed to initialize")
            # Lightweight connectivity check
            await execute_async(
                service_client.table("skills").select("count", count="exact").limit(0),
                timeout=3.0,
                op_name="health.connections.service_client",
            )
        except Exception as e:
            raise ValueError(f"Service client connectivity check failed: {e}")

        # Verify RAG Client Connectivity
        try:
            rag_client = get_supabase_client()
            if not rag_client:
                raise ValueError("RAG client failed to initialize")
            # Lightweight connectivity check
            await execute_async(
                rag_client.table("agent_knowledge")
                .select("count", count="exact")
                .limit(0),
                timeout=3.0,
                op_name="health.connections.rag_client",
            )
        except Exception as e:
            raise ValueError(f"RAG client connectivity check failed: {e}")

        # Build base response
        response = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pools": {"service_client": service_stats, "rag_client": rag_stats},
            "efficiency_note": "Creation counts should remain stable (1) after initialization.",
        }

        # Add Cache Health
        from app.services.cache import get_cache_service

        cache = get_cache_service()
        cache_stats = await cache.get_stats()
        cache_healthy = await cache.is_healthy()

        response["cache"] = {
            "status": "healthy" if cache_healthy else "unhealthy",
            "pool_max_connections": cache_stats.get("pool_max_connections"),
            "latency_ms": cache_stats.get("latency_stats", {}),
            "memory": cache_stats.get("memory_stats", {}),
            "memory_alert": cache_stats.get("memory_stats", {}).get(
                "memory_alert", False
            ),
            "circuit_breaker": cache_stats.get("circuit_breaker"),
            "transport": "async_redis",
        }
        from app.services.supabase_resilience import supabase_circuit_breaker

        response["supabase_circuit_breaker"] = await supabase_circuit_breaker.get_status()
        response["config_readiness"] = {
            "status": "ready" if not missing_required_env else "not_ready",
            "missing_required": missing_required_env,
            "missing_recommended": missing_critical_env,
        }
        canary_raw = os.getenv("WORKFLOW_CANARY_USER_IDS", "")
        canary_users = [u.strip() for u in canary_raw.split(",") if u.strip()]
        response["workflow_rollout"] = {
            "kill_switch_enabled": os.getenv("WORKFLOW_KILL_SWITCH", "false")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"},
            "canary_enabled": os.getenv("WORKFLOW_CANARY_ENABLED", "false")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"},
            "canary_user_count": len(canary_users),
        }
        if missing_required_env or missing_critical_env:
            logger.warning(
                "Configuration readiness issues detected. Missing required=%s missing_recommended=%s",
                missing_required_env,
                missing_critical_env,
            )

        # SSE connection stats (SSES-04 — observable from health endpoint)
        try:
            total_sse = await get_total_active_sse_count()
        except Exception:
            total_sse = None
        response["sse_connections"] = {
            "total_active": total_sse,
            "per_user_limit": get_sse_connection_limit(),
            "max_total": int(os.getenv("SSE_MAX_TOTAL_CONNECTIONS", "500")),
        }

        return response
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@app.get("/health/workflows/readiness", tags=["Health"])
async def get_workflow_readiness_health():
    """Workflow preflight report for tool/integration readiness."""
    from datetime import datetime, timezone

    try:
        from app.workflows.readiness import build_workflow_readiness_report

        report = build_workflow_readiness_report()
        report["timestamp"] = datetime.now(timezone.utc).isoformat()
        return report
    except Exception as e:
        logger.error(f"Workflow readiness health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@app.get("/health/cache", tags=["Health"])
async def get_cache_health():
    """Monitor Redis cache health and performance with detailed diagnostics.

    Returns:
        - Connection status
        - Circuit breaker state
        - Connection pool statistics
        - Cache hit/miss rates
    """
    from app.services.cache import get_cache_service

    cache = get_cache_service()

    # Get basic stats
    stats = await cache.get_stats()
    is_healthy = await cache.is_healthy()
    circuit_breaker = cache.get_circuit_breaker_state()

    # Build detailed response
    response = {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "circuit_breaker": circuit_breaker,
        "cache_stats": {
            "hits": stats.get("hits", 0),
            "misses": stats.get("misses", 0),
            "hit_rate": stats.get("hit_rate", 0),
        },
    }

    # Add connection info if available
    if "redis_version" in stats:
        response["connection"] = {
            "redis_version": stats.get("redis_version"),
            "used_memory": stats.get("used_memory_human"),
            "connected_clients": stats.get("connected_clients"),
        }

    # Add error info if any
    if "error" in stats:
        response["error"] = stats.get("error")

    return response


@app.get("/health/embeddings", tags=["Health"])
async def get_embedding_health():
    """Check Gemini embedding availability and latency."""
    from datetime import datetime, timezone

    from app.rag.embedding_service import get_embedding_health

    health = get_embedding_health()
    health["timestamp"] = datetime.now(timezone.utc).isoformat()
    return health


@app.get("/health/video", tags=["Health"])
async def get_video_readiness():
    """Check video generation configuration (Veo + Remotion). Read-only; no API calls."""
    from app.services.video_readiness import get_video_readiness as get_readiness

    report = get_readiness()
    report["timestamp"] = datetime.now(timezone.utc).isoformat()
    return report


def _csv_env(name: str) -> set[str]:
    return {v.strip().lower() for v in os.getenv(name, "").split(",") if v.strip()}


def _is_cache_admin(user: dict) -> bool:
    """Authorizes access to admin cache invalidation endpoint.

    Priority:
    1) Explicit allow-any flag for controlled environments.
    2) Explicit user allowlists (IDs/emails).
    3) Role-based checks (default: admin, service_role).
    """
    if os.getenv("ALLOW_ANY_AUTH_ADMIN_ENDPOINT") == "1":
        return True

    user_id = str(user.get("id", "")).lower()
    email = str(user.get("email", "")).lower()
    allow_ids = _csv_env("ADMIN_USER_IDS")
    allow_emails = _csv_env("ADMIN_USER_EMAILS")
    allowed_roles = _csv_env("ADMIN_ROLES") or {"admin", "service_role"}

    if user_id and user_id in allow_ids:
        return True
    if email and email in allow_emails:
        return True

    role_candidates = {str(user.get("role", "")).lower()}
    metadata = user.get("metadata") or {}
    if isinstance(metadata, dict):
        app_meta = metadata.get("app_metadata") or {}
        if isinstance(app_meta, dict):
            app_role = app_meta.get("role")
            if isinstance(app_role, str):
                role_candidates.add(app_role.lower())
            app_roles = app_meta.get("roles")
            if isinstance(app_roles, list):
                role_candidates.update(
                    str(role).lower() for role in app_roles if isinstance(role, str)
                )

    return any(role in allowed_roles for role in role_candidates if role)


@app.post("/admin/cache/invalidate", tags=["Admin"])
async def invalidate_cache(
    user_id: str | None = None,
    confirm_flush_all: bool = False,
    current_user: dict = Depends(verify_token),
):
    """Invalidate cache for a specific user or all users."""
    if not _is_cache_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from app.services.cache import get_cache_service

    cache = get_cache_service()

    if user_id:
        await cache.invalidate_user_all(user_id)
        return {"status": "success", "message": f"Cache invalidated for user {user_id}"}
    else:
        if not confirm_flush_all:
            raise HTTPException(
                status_code=400,
                detail="confirm_flush_all=true is required for global cache invalidation",
            )
        # Invalidate all caches (use with caution)
        await cache.flush_all()
        return {"status": "success", "message": "All caches invalidated"}


import asyncio
import json

from fastapi.responses import StreamingResponse
from google.genai import types as genai_types
from pydantic import BaseModel

# Import SSE utilities from extracted module
from app.sse_utils import (
    extract_traces_from_event,
    extract_widget_from_event,
    inject_synthetic_text_for_tool_message,
    inject_synthetic_text_for_widget,
    is_model_unavailable_error,
    serialize_progress_event,
)

# Backward compatibility aliases (for existing imports from this module)
_is_model_unavailable_error = is_model_unavailable_error
_extract_widget_from_event = extract_widget_from_event
_extract_traces_from_event = extract_traces_from_event
_serialize_progress_event = serialize_progress_event
_inject_synthetic_text_for_widget = inject_synthetic_text_for_widget
_inject_synthetic_text_for_tool_message = inject_synthetic_text_for_tool_message


# SSE Request Models
class TextPart(BaseModel):
    text: str


class NewMessage(BaseModel):
    parts: list[TextPart]


class ChatRequest(BaseModel):
    session_id: str
    user_id: str | None = None
    new_message: NewMessage
    agent_mode: str | None = "auto"  # 'auto' | 'collab' | 'ask'


@app.post("/a2a/app/run_sse")
async def run_sse(raw_request: Request, request: ChatRequest):
    """Custom SSE endpoint for agent chat with widget extraction.

    Streams ADK events via SSE. Post-processes events to detect widget
    definitions from tool results and inject them as top-level 'widget'
    fields for the frontend WidgetRegistry to render.
    If the body omits user_id, the user is resolved from Authorization: Bearer.
    """
    logger.info(
        f"Starting SSE chat for session {request.session_id} with mode: {request.agent_mode}"
    )
    allow_anonymous_chat = os.getenv("ALLOW_ANONYMOUS_CHAT", "0") == "1"
    auth_header = raw_request.headers.get("Authorization")
    token = (
        (auth_header[7:].strip())
        if (auth_header and auth_header.startswith("Bearer "))
        else None
    )

    effective_user_id = None
    if token:
        from app.app_utils.auth import get_user_id_from_bearer_token

        effective_user_id = get_user_id_from_bearer_token(token)
        if not effective_user_id and not allow_anonymous_chat:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )
    elif not allow_anonymous_chat:
        raise HTTPException(status_code=401, detail="Authentication required for chat")

    if not effective_user_id:
        # Anonymous mode only when explicitly enabled by env flag.
        effective_user_id = "anonymous"

    if not runner:
        logger.error("ADK Runner not initialized")
        return {"error": "Runner not initialized"}

    _sse_result = await try_acquire_sse_connection(
        effective_user_id,
        stream_name="chat",
    )
    acquired_connection, _active_connections, connection_limit = _sse_result
    if not acquired_connection:
        if _sse_result.reason == SSERejectReason.SERVER_BACKPRESSURE:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Server at capacity. Too many active SSE connections globally. "
                    "Please retry shortly."
                ),
            )
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many active SSE connections for this user. "
                f"Limit: {connection_limit}."
            ),
        )

    try:
        # Extract text from message parts
        user_text = " ".join([p.text for p in request.new_message.parts])

        # Inject agent mode context into the message
        agent_mode = request.agent_mode or "auto"
        mode_context = ""
        if agent_mode == "collab":
            mode_context = "[COLLAB MODE: Ask the user for approval and insights before proceeding with major decisions or actions. Check in with the user as you work.]\n\n"
        elif agent_mode == "ask":
            mode_context = "[ASK MODE: The user is asking questions about their progress, past conversations, initiatives, or reports. Focus on providing information and answering queries.]\n\n"
        # For 'auto' mode, no special context needed - agent works independently

        if mode_context:
            user_text = mode_context + user_text

        # Create ADK Content object for the new message
        adk_message = genai_types.Content(
            role="user", parts=[genai_types.Part(text=user_text)]
        )

        # Ensure session exists before running agent and preload personalization state
        try:
            state_updates: dict[str, object] = {"user_id": effective_user_id}
            if effective_user_id != "anonymous":
                try:
                    from app.services.user_agent_factory import (
                        USER_AGENT_PERSONALIZATION_STATE_KEY,
                        get_user_agent_factory,
                    )

                    personalization = (
                        await get_user_agent_factory().get_runtime_personalization(
                            effective_user_id
                        )
                    )
                    state_updates[USER_AGENT_PERSONALIZATION_STATE_KEY] = (
                        personalization
                    )
                except Exception as personalization_error:
                    logger.warning(
                        "User personalization preload failed for %s: %s",
                        effective_user_id,
                        personalization_error,
                    )

            existing_session = await session_service.get_session(
                app_name=adk_app.name,
                user_id=effective_user_id,
                session_id=request.session_id,
            )
            if not existing_session:
                logger.info(
                    f"Creating new session {request.session_id} for user {effective_user_id}"
                )
                await session_service.create_session(
                    app_name=adk_app.name,
                    user_id=effective_user_id,
                    session_id=request.session_id,
                    state=state_updates,
                )
            else:
                current_state = getattr(existing_session, "state", {}) or {}
                needs_update = any(
                    current_state.get(key) != value
                    for key, value in state_updates.items()
                )
                if needs_update:
                    if hasattr(session_service, "update_state"):
                        await session_service.update_state(
                            app_name=adk_app.name,
                            user_id=effective_user_id,
                            session_id=request.session_id,
                            state_updates=state_updates,
                        )
                    elif isinstance(current_state, dict):
                        current_state.update(state_updates)
        except Exception as e:
            logger.warning(f"Session check/creation failed: {e}")
            # Continue anyway - the runner might handle this

        # Load user's custom skills into the in-memory registry for this session
        try:
            from app.skills.custom_skills_service import get_custom_skills_service

            skill_svc = get_custom_skills_service()
            loaded_count = await skill_svc.load_user_skills_to_registry(
                effective_user_id
            )
            if loaded_count:
                logger.info(
                    f"Loaded {loaded_count} custom skills for user {effective_user_id}"
                )
        except Exception as e:
            logger.warning(f"Custom skill loading failed (non-fatal): {e}")

        async def event_generator():
            from app.services.request_context import (
                set_current_agent_mode,
                set_current_progress_queue,
                set_current_session_id,
                set_current_user_id,
                set_current_workflow_execution_id,
            )

            # Set request-scoped user_id so tools can access it
            set_current_user_id(effective_user_id)
            set_current_session_id(request.session_id)
            set_current_workflow_execution_id(None)
            # Set request-scoped agent_mode so agent can adjust behavior
            set_current_agent_mode(request.agent_mode or "auto")
            progress_queue: asyncio.Queue[dict] = asyncio.Queue()
            set_current_progress_queue(progress_queue)

            adk_event_queue: asyncio.Queue[str] = asyncio.Queue()
            stream_done = asyncio.Event()
            runner_task: asyncio.Task | None = None
            last_keepalive = time.monotonic()
            stream_start_time = time.monotonic()

            # Accumulate response metadata for interaction logging
            _response_texts: list[str] = []
            _responding_agent: str = "EXEC"

            async def _runner_to_queue() -> None:
                nonlocal _responding_agent
                try:
                    logger.info(
                        f"Calling runner.run_async for session {request.session_id} user {effective_user_id}"
                    )
                    try:
                        response_stream = runner.run_async(
                            session_id=request.session_id,
                            new_message=adk_message,
                            user_id=effective_user_id,
                        )
                    except Exception as e:
                        if runner_fallback and _is_model_unavailable_error(e):
                            logger.info(
                                f"Primary model unavailable ({e}), retrying with fallback model"
                            )
                            response_stream = runner_fallback.run_async(
                                session_id=request.session_id,
                                new_message=adk_message,
                                user_id=effective_user_id,
                            )
                        else:
                            raise

                    logger.info("Runner started, iterating stream...")
                    async for event in response_stream:
                        if hasattr(event, "model_dump_json"):
                            data = event.model_dump_json()
                        elif hasattr(event, "to_json"):
                            data = event.to_json()
                        else:
                            data = json.dumps(event, default=lambda o: str(o))
                        data = _extract_widget_from_event(data)
                        data = _extract_traces_from_event(data)

                        # Extract response text and author for interaction logging
                        try:
                            evt = json.loads(data)
                            author = evt.get("author")
                            if author and author != "user":
                                _responding_agent = author
                            content = evt.get("content")
                            if isinstance(content, dict):
                                for part in content.get("parts") or []:
                                    if isinstance(part, dict) and part.get("text"):
                                        _response_texts.append(part["text"])
                        except (json.JSONDecodeError, TypeError):
                            pass

                        await adk_event_queue.put(data)
                    logger.info("Stream finished normally")
                except Exception as e:
                    logger.error(f"Error in SSE stream: {e}", exc_info=True)
                    await adk_event_queue.put(json.dumps({"error": str(e)}))
                finally:
                    stream_done.set()

            SSE_MAX_DURATION_S = int(
                os.getenv("SSE_MAX_DURATION_S", "300")
            )  # 5 min default

            try:
                yield ": connected\n\n"
                runner_task = asyncio.create_task(_runner_to_queue())
                stream_deadline = time.monotonic() + SSE_MAX_DURATION_S

                while True:
                    if await raw_request.is_disconnected():
                        break
                    if (
                        stream_done.is_set()
                        and adk_event_queue.empty()
                        and progress_queue.empty()
                    ):
                        break
                    if time.monotonic() >= stream_deadline:
                        logger.warning(
                            "SSE stream hit max duration (%ds), closing",
                            SSE_MAX_DURATION_S,
                        )
                        yield f"data: {json.dumps({'error': 'Stream timeout — please retry your request.'})}\n\n"
                        break

                    adk_get = asyncio.create_task(adk_event_queue.get())
                    progress_get = asyncio.create_task(progress_queue.get())
                    done, pending = await asyncio.wait(
                        {adk_get, progress_get},
                        timeout=0.5,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()

                    if not done:
                        now = time.monotonic()
                        if now - last_keepalive >= 10:
                            last_keepalive = now
                            yield ": keepalive\n\n"
                        continue

                    for task in done:
                        try:
                            item = task.result()
                        except asyncio.CancelledError:
                            continue
                        if task is adk_get:
                            yield f"data: {item}\n\n"
                        else:
                            yield f"data: {_serialize_progress_event(item)}\n\n"
                        last_keepalive = time.monotonic()

                if runner_task is not None:
                    await runner_task
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                # Fire-and-forget interaction logging
                try:
                    from app.services.interaction_logger import interaction_logger

                    response_summary = (
                        " ".join(_response_texts)[:500] if _response_texts else None
                    )
                    elapsed_ms = int((time.monotonic() - stream_start_time) * 1000)
                    asyncio.create_task(
                        interaction_logger.log_interaction(
                            agent_id=_responding_agent,
                            user_query=user_text[:500],
                            agent_response_summary=response_summary,
                            session_id=request.session_id,
                            response_time_ms=elapsed_ms,
                            response_tokens=len(response_summary) // 4
                            if response_summary
                            else None,
                            metadata={"agent_mode": agent_mode},
                        )
                    )
                except Exception:
                    logger.warning(
                        "Failed to schedule interaction logging", exc_info=True
                    )

                set_current_progress_queue(None)
                set_current_session_id(None)
                set_current_workflow_execution_id(None)
                if runner_task and not runner_task.done():
                    logger.info(
                        "SSE Stream disconnected. Cancelling agent runner_task."
                    )
                    runner_task.cancel()
                await release_sse_connection(effective_user_id, stream_name="chat")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception:
        await release_sse_connection(effective_user_id, stream_name="chat")
        raise


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
