# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""KPI endpoints — per-persona computed metrics from Supabase data."""


import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.personas.runtime import resolve_request_persona
from app.routers.onboarding import get_current_user_id
from app.services.kpi_service import get_kpi_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kpis", tags=["KPIs"])


@router.get("/persona")
@limiter.limit(get_user_persona_limit)
async def get_persona_kpis(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Return computed KPIs for the requesting user's persona.

    Resolves the persona from the ``x-pikar-persona`` cookie or header.
    Falls back to ``solopreneur`` when no persona is detected.

    Returns:
        ``{ "persona": str, "kpis": [{"label": str, "value": str, "unit": str}] }``
    """
    try:
        persona = resolve_request_persona(request) or "solopreneur"
        return await get_kpi_service().compute_kpis(user_id=user_id, persona=persona)
    except Exception as exc:
        logger.exception(
            "Failed to compute KPIs for user %s persona %s", user_id, persona
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
