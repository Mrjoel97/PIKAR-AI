# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Health and readiness endpoints."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.sse_connection_limits import (
    get_sse_connection_limit,
    get_total_active_sse_count,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health/startup")
async def health_startup():
    """Startup probe for Cloud Run."""
    checks: dict[str, str] = {}
    all_ok = True

    try:
        from app.services.supabase import get_service_client

        client = get_service_client()
        client.table("sessions").select("session_id").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as e:
        checks["supabase"] = f"error: {e}"
        all_ok = False

    has_gemini_credentials = bool(
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or (
            os.getenv("GOOGLE_CLOUD_PROJECT")
            and (os.getenv("K_SERVICE") or os.getenv("GOOGLE_CLOUD_RUN"))
        )
    )
    checks["gemini_credentials"] = "ok" if has_gemini_credentials else "missing"
    if not has_gemini_credentials:
        all_ok = False

    try:
        from app.services.cache import get_cache_service

        cache = get_cache_service()
        checks["redis"] = "ok" if cache._connected else "not connected (non-critical)"
    except Exception:
        checks["redis"] = "not available (non-critical)"

    status_code = 200 if all_ok else 503
    return JSONResponse(
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
        status_code=status_code,
    )


def _health_response(
    *,
    status: str,
    service: str,
    latency_ms: int | None = None,
    details: dict | None = None,
    integrations: dict | None = None,
) -> dict:
    """Build canonical health response envelope."""
    resp: dict = {
        "status": status,
        "version": "1",
        "service": service,
        "latency_ms": latency_ms,
        "details": details or {},
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if integrations is not None:
        resp["integrations"] = integrations
    return resp


@router.get("/health/live")
async def get_liveness():
    """Fast liveness probe for container healthchecks."""
    return _health_response(status="ok", service="live", latency_ms=0)


@router.get("/health/connections")
async def get_connection_pool_health():
    """Monitor Supabase connection pool stats and cache health."""
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
    conn_start = time.monotonic()
    try:
        from app.rag.knowledge_vault import get_rag_client_stats, get_supabase_client
        from app.services.cache import get_cache_service
        from app.services.supabase import get_client_stats, get_service_client
        from app.services.supabase_async import execute_async
        from app.services.supabase_resilience import supabase_circuit_breaker

        service_stats = get_client_stats()
        rag_stats = get_rag_client_stats()

        service_client = get_service_client()
        if not service_client:
            raise ValueError("Service client failed to initialize")
        await execute_async(
            service_client.table("skills").select("count", count="exact").limit(0),
            timeout=3.0,
            op_name="health.connections.service_client",
        )

        rag_client = await get_supabase_client()
        if not rag_client:
            raise ValueError("RAG client failed to initialize")
        await (
            rag_client.table("agent_knowledge")
            .select("count", count="exact")
            .limit(0)
            .execute()
        )

        conn_latency_ms = int((time.monotonic() - conn_start) * 1000)

        cache = get_cache_service()
        cache_stats = await cache.get_stats()
        cache_healthy = await cache.is_healthy()
        cache_detail = {
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

        supabase_cb = await supabase_circuit_breaker.get_status()

        canary_raw = os.getenv("WORKFLOW_CANARY_USER_IDS", "")
        canary_users = [u.strip() for u in canary_raw.split(",") if u.strip()]
        workflow_rollout = {
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
        config_readiness = {
            "status": "ready" if not missing_required_env else "not_ready",
            "missing_required": missing_required_env,
            "missing_recommended": missing_critical_env,
        }
        if missing_required_env or missing_critical_env:
            logger.warning(
                "Configuration readiness issues detected. Missing required=%s missing_recommended=%s",
                missing_required_env,
                missing_critical_env,
            )

        try:
            total_sse = await get_total_active_sse_count()
        except Exception:
            total_sse = None
        sse_connections = {
            "total_active": total_sse,
            "per_user_limit": get_sse_connection_limit(),
            "max_total": int(os.getenv("SSE_MAX_TOTAL_CONNECTIONS", "500")),
        }

        integrations: dict = {}
        try:
            sc = get_service_client()
            integrations_result = await execute_async(
                sc.table("integration_sync_state").select(
                    "provider, last_sync_status, last_sync_at, last_error_message"
                ),
                op_name="health.connections.integrations",
            )
            for row in integrations_result.data or []:
                raw_status: str | None = row.get("last_sync_status")
                if raw_status is None:
                    int_status = "unknown"
                elif any(kw in str(raw_status).lower() for kw in ("error", "failed")):
                    int_status = "degraded"
                else:
                    int_status = "ok"
                integrations[row["provider"]] = {
                    "status": int_status,
                    "last_sync_at": row.get("last_sync_at"),
                }
        except Exception as int_exc:
            logger.warning(
                "health.connections: could not load integration_sync_state: %s",
                int_exc,
            )

        details = {
            "pools": {"service_client": service_stats, "rag_client": rag_stats},
            "efficiency_note": (
                "Creation counts should remain stable (1) after initialization."
            ),
            "cache": cache_detail,
            "supabase_circuit_breaker": supabase_cb,
            "config_readiness": config_readiness,
            "workflow_rollout": workflow_rollout,
            "sse_connections": sse_connections,
        }

        return _health_response(
            status="ok",
            service="supabase",
            latency_ms=conn_latency_ms,
            details=details,
            integrations=integrations if integrations else None,
        )
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return _health_response(
            status="down",
            service="supabase",
            latency_ms=int((time.monotonic() - conn_start) * 1000),
            details={"error": str(e)},
        )


@router.get("/health/workflows/readiness")
async def get_workflow_readiness_health():
    """Workflow preflight report for tool/integration readiness."""
    try:
        from app.workflows.readiness import build_workflow_readiness_report

        report = build_workflow_readiness_report()
        report["timestamp"] = datetime.now(timezone.utc).isoformat()
        return report
    except Exception as e:
        logger.error("Workflow readiness health check failed: %s", e)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/health/cache")
async def get_cache_health():
    """Monitor Redis cache health and performance with detailed diagnostics."""
    cache_start = time.monotonic()
    try:
        from app.services.cache import get_cache_service

        cache = get_cache_service()
        stats = await cache.get_stats()
        is_healthy = await cache.is_healthy()
        circuit_breaker = cache.get_circuit_breaker_state()
        cache_latency_ms = int((time.monotonic() - cache_start) * 1000)
        cb_open = (
            isinstance(circuit_breaker, dict) and circuit_breaker.get("state") == "open"
        )
        if is_healthy and not cb_open:
            cache_status = "ok"
        elif not is_healthy and cb_open:
            cache_status = "degraded"
        else:
            cache_status = "ok" if is_healthy else "degraded"

        details: dict = {
            "connected": is_healthy,
            "circuit_breaker": circuit_breaker,
            "cache_stats": {
                "hits": stats.get("hits", 0),
                "misses": stats.get("misses", 0),
                "hit_rate": stats.get("hit_rate", 0),
            },
        }
        if "redis_version" in stats:
            details["connection"] = {
                "redis_version": stats.get("redis_version"),
                "used_memory": stats.get("used_memory_human"),
                "connected_clients": stats.get("connected_clients"),
            }
        if "error" in stats:
            details["error"] = stats.get("error")
        if "reason" in stats:
            details["reason"] = stats.get("reason")

        return _health_response(
            status=cache_status,
            service="redis",
            latency_ms=cache_latency_ms,
            details=details,
        )
    except Exception as exc:
        return _health_response(
            status="down",
            service="redis",
            latency_ms=int((time.monotonic() - cache_start) * 1000),
            details={"error": str(exc)},
        )


@router.get("/health/embeddings")
async def get_embedding_health():
    """Check Gemini embedding availability and latency."""
    emb_start = time.monotonic()
    try:
        from app.rag.embedding_service import get_embedding_health

        health = get_embedding_health()
        raw_status = health.get("status", "unhealthy")
        service_latency = health.get("latency_ms")
        return _health_response(
            status="ok" if raw_status == "healthy" else "down",
            service="gemini",
            latency_ms=(
                int(service_latency)
                if service_latency is not None
                else int((time.monotonic() - emb_start) * 1000)
            ),
            details={
                k: v for k, v in health.items() if k not in ("status", "latency_ms")
            },
        )
    except Exception as exc:
        return _health_response(
            status="down",
            service="gemini",
            latency_ms=int((time.monotonic() - emb_start) * 1000),
            details={"error": str(exc)},
        )


@router.get("/health/summarizer")
async def get_summarizer_health() -> dict:
    """Report conversation-summarizer rollout state."""
    from app.persistence import supabase_session_service

    enabled = bool(supabase_session_service.ENABLE_CONVERSATION_SUMMARIZER)
    max_events = int(supabase_session_service.SESSION_MAX_EVENTS)
    payload = _health_response(
        status="ok",
        service="summarizer",
        latency_ms=0,
        details={
            "enabled": enabled,
            "session_max_events": max_events,
        },
    )
    payload["enabled"] = enabled
    payload["session_max_events"] = max_events
    return payload


@router.get("/health/video")
async def get_video_readiness():
    """Check video generation configuration. Read-only; no API calls."""
    from app.services.video_readiness import get_video_readiness as get_readiness

    report = get_readiness()
    veo_ok = report.get("veo_configured", False)
    remotion_ok = report.get("remotion_configured", False)

    if veo_ok and remotion_ok:
        vid_status = "ok"
    elif veo_ok or remotion_ok:
        vid_status = "degraded"
    else:
        vid_status = "degraded"

    return _health_response(
        status=vid_status,
        service="video",
        latency_ms=0,
        details=report.get("details", {}),
    )
