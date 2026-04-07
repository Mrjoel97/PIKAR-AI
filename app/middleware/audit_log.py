# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Centralised audit logging middleware (AUTH-04).

Writes one row to ``governance_audit_log`` for every successful 2xx response
to a POST/PUT/PATCH/DELETE on a user-facing API route.

Reads (GET) and failures (non-2xx) are NOT logged. Health, admin, a2a,
webhooks, and auth routes are explicitly excluded.

The middleware NEVER raises — audit failures are logged at ERROR level and
swallowed so the wrapped request flow is unaffected. The actual insert is
fired via ``asyncio.create_task`` so it does not block the response.

This is the foundation for AUTH-05 (admin audit viewer): the admin viewer
will read from ``governance_audit_log`` filtered by ``user_id``,
``action_type``, and date range. Plan 49-05 derives its filter values from
the same ``AUDITED_ROUTES`` map exported here.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.app_utils.auth import verify_token_fast
from app.services.governance_service import get_governance_service

logger = logging.getLogger(__name__)


# Strong references to in-flight background log tasks.
#
# ``asyncio.create_task`` only holds a weak reference to the task; without a
# strong reference the task can be garbage-collected mid-flight (RUF006).
# Tasks remove themselves from this set on completion via ``add_done_callback``.
_BACKGROUND_AUDIT_TASKS: set[asyncio.Task[None]] = set()


# Mutating HTTP methods that should produce an audit row.
_MUTATING_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Method → action verb mapping for action_type derivation.
_METHOD_VERBS: dict[str, str] = {
    "POST": "created",
    "PUT": "updated",
    "PATCH": "updated",
    "DELETE": "deleted",
}

# Hard exclusions: these prefixes are NEVER audited, even on a mutating verb.
#
# - ``/health``       — health checks (would spam the audit log)
# - ``/a2a``          — agent-to-agent SSE chat (per-message logging too noisy)
# - ``/admin``        — admin actions go to ``admin_audit_log`` instead
#                       (separate table, see ``app/services/admin_audit.py``)
# - ``/webhooks``     — inbound webhooks have no human actor
# - ``/auth``         — auth endpoints (login/logout/refresh)
# - ``/docs``,        — interactive API docs / schema endpoints
#   ``/openapi.json``,
#   ``/redoc``
_EXCLUDED_PREFIXES: tuple[str, ...] = (
    "/health",
    "/a2a",
    "/admin",
    "/webhooks",
    "/auth",
    "/docs",
    "/openapi.json",
    "/redoc",
)

# Inclusion list: prefix → resource_type. Mutations on a path matching one of
# these prefixes (and NOT excluded above) produce an audit row.
#
# IMPORTANT: New routers must be added to this map explicitly. The
# parametrised regression test in
# ``tests/unit/app/middleware/test_audit_log_middleware.py`` iterates this
# map and asserts every entry produces a log_event call — a typo or silent
# drop will be caught by that test.
AUDITED_ROUTES: dict[str, str] = {
    "/initiatives": "initiative",
    "/workflows": "workflow",
    "/content": "content",
    "/campaigns": "campaign",
    "/reports": "report",
    "/vault": "vault_item",
    "/integrations": "integration",
    "/briefing": "briefing",
    "/pages": "page",
    "/community": "community_post",
    "/finance": "finance_item",
    "/sales": "sales_item",
    "/support": "support_ticket",
    "/compliance": "compliance_item",
    "/learning": "learning_item",
    "/api_credentials": "api_credential",
    "/byok": "byok_credential",
    "/journeys": "journey",
    "/ad_approvals": "ad_approval",
    "/email_sequences": "email_sequence",
    "/files": "file",
    "/onboarding": "onboarding",
    "/teams": "workspace",
    "/governance": "governance",
    "/account": "account",
    "/configuration": "configuration",
    "/data_io": "data_io",
    "/departments": "department",
    "/kpis": "kpi",
    "/monitoring_jobs": "monitoring_job",
    "/outbound_webhooks": "outbound_webhook",
    "/self_improvement": "self_improvement",
    "/workflow_triggers": "workflow_trigger",
    "/app_builder": "app_builder",
}


def _resolve_resource_type(path: str) -> str | None:
    """Return the resource_type for an audited path, or None if not audited.

    Excluded prefixes always return None. Otherwise the first matching
    AUDITED_ROUTES prefix wins (longest-prefix is not required because the
    router prefixes are mutually exclusive).
    """
    for prefix in _EXCLUDED_PREFIXES:
        if path.startswith(prefix):
            return None
    for prefix, resource_type in AUDITED_ROUTES.items():
        if path == prefix or path.startswith(f"{prefix}/"):
            return resource_type
    return None


def _matched_prefix(path: str) -> str | None:
    """Return the AUDITED_ROUTES prefix that matches ``path`` or None."""
    for prefix in AUDITED_ROUTES:
        if path == prefix or path.startswith(f"{prefix}/"):
            return prefix
    return None


def _extract_resource_id(path: str, prefix: str) -> str | None:
    """Extract the first path segment after ``prefix``, or None.

    Examples:
        ``/initiatives``                          → None
        ``/initiatives/abc-123``                  → ``"abc-123"``
        ``/initiatives/abc-123/checklist/item-1`` → ``"abc-123"``
    """
    remainder = path[len(prefix) :].strip("/")
    if not remainder:
        return None
    first = remainder.split("/")[0]
    return first or None


def _resolve_actor(request: Request) -> str | None:
    """Best-effort actor resolution from the Authorization header.

    Returns the JWT ``sub`` claim (user_id) or None if no valid token is
    present. NEVER raises — token verification errors are logged at DEBUG
    level and swallowed.
    """
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(None, 1)[1].strip()
    if not token:
        return None
    try:
        claims = verify_token_fast(token)
    except Exception as exc:
        logger.debug("audit_log: token verify failed: %s", exc)
        return None
    if not claims:
        return None
    sub = claims.get("sub")
    if not sub:
        return None
    return str(sub)


async def _fire_log_event(
    user_id: str,
    action_type: str,
    resource_type: str,
    resource_id: str | None,
    method: str,
    path: str,
    status_code: int,
    ip_address: str | None,
) -> None:
    """Background task: call ``GovernanceService.log_event`` swallowing all errors.

    ``GovernanceService.log_event`` already swallows exceptions internally
    but this wrapper provides defence-in-depth so a regression in the
    service layer cannot crash the event loop via an unhandled task error.
    """
    try:
        governance = get_governance_service()
        await governance.log_event(
            user_id=user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "method": method,
                "path": path,
                "status_code": status_code,
            },
            ip_address=ip_address,
        )
    except Exception as exc:
        logger.error("audit_log: background log_event failed: %s", exc)


async def log_mutation(
    *,
    user_id: str,
    method: str,
    path: str,
    status_code: int,
    ip_address: str | None = None,
) -> None:
    """Manually log a mutation event.

    Helper for code paths that bypass HTTP entirely (background workers,
    scheduled jobs, internal scripts) and need to record an audit row using
    the same derivation logic as the middleware.

    The function infers ``resource_type``, ``action_type`` and ``resource_id``
    from the supplied ``method`` + ``path``. It is a no-op for read methods,
    excluded prefixes, or non-2xx status codes.
    """
    if method.upper() not in _MUTATING_METHODS:
        return
    if status_code < 200 or status_code >= 300:
        return
    resource_type = _resolve_resource_type(path)
    if resource_type is None:
        return
    prefix = _matched_prefix(path)
    resource_id = _extract_resource_id(path, prefix) if prefix else None
    verb = _METHOD_VERBS.get(method.upper(), "modified")
    action_type = f"{resource_type}.{verb}"
    await _fire_log_event(
        user_id=user_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        method=method.upper(),
        path=path,
        status_code=status_code,
        ip_address=ip_address,
    )


class AuditLogMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that audits successful mutating requests.

    Placed AFTER request logging and onboarding guards in the middleware
    stack so it sees the final response status code. Registered via
    ``app.add_middleware(AuditLogMiddleware)`` in ``app/fast_api_app.py``.

    Behaviour summary:
    - Only mutating verbs (POST/PUT/PATCH/DELETE) are considered.
    - Only 2xx responses produce a row (failed requests are not audited).
    - Excluded prefixes (/health, /a2a, /admin, /webhooks, /auth, /docs,
      /openapi.json, /redoc) are silently skipped.
    - Anonymous requests (no/invalid Authorization header) are silently
      skipped — there is no actor to record.
    - The actual insert is fired via ``asyncio.create_task`` AFTER the
      response is returned, so audit logging never blocks the request.
    - The middleware NEVER raises. Any exception in the audit path is
      logged at ERROR and swallowed.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Wrap the inner request handler and best-effort log the mutation."""
        response = await call_next(request)

        try:
            if request.method not in _MUTATING_METHODS:
                return response
            if response.status_code < 200 or response.status_code >= 300:
                return response

            path = request.url.path
            resource_type = _resolve_resource_type(path)
            if resource_type is None:
                return response

            user_id = _resolve_actor(request)
            if not user_id:
                return response

            prefix = _matched_prefix(path)
            resource_id = _extract_resource_id(path, prefix) if prefix else None

            verb = _METHOD_VERBS.get(request.method, "modified")
            action_type = f"{resource_type}.{verb}"

            ip_address = request.client.host if request.client else None

            # Fire-and-forget so the audit insert does not block the response.
            # Hold a strong reference in _BACKGROUND_AUDIT_TASKS so the task
            # is not garbage-collected mid-flight; the done-callback removes
            # the reference once the insert completes.
            task = asyncio.create_task(
                _fire_log_event(
                    user_id=user_id,
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    method=request.method,
                    path=path,
                    status_code=response.status_code,
                    ip_address=ip_address,
                )
            )
            _BACKGROUND_AUDIT_TASKS.add(task)
            task.add_done_callback(_BACKGROUND_AUDIT_TASKS.discard)
        except Exception as exc:
            logger.error("audit_log: middleware dispatch error: %s", exc)

        return response


__all__ = [
    "AUDITED_ROUTES",
    "AuditLogMiddleware",
    "log_mutation",
]
