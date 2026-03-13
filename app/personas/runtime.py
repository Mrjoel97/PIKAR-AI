from __future__ import annotations

from typing import Any, Iterable

from starlette.requests import Request

from app.personas.policy_registry import normalize_persona


_PERSONA_HEADER_NAME = "x-pikar-persona"


def resolve_request_persona(
    request: Request | None,
    *,
    explicit_persona: str | None = None,
) -> str | None:
    """Resolve persona from explicit input first, then request cookie/header."""
    normalized = normalize_persona(explicit_persona)
    if normalized:
        return normalized
    if request is None:
        return None

    try:
        cookie_persona = normalize_persona(request.cookies.get(_PERSONA_HEADER_NAME))
        if cookie_persona:
            return cookie_persona
    except Exception:
        pass

    try:
        header_persona = normalize_persona(request.headers.get(_PERSONA_HEADER_NAME))
        if header_persona:
            return header_persona
    except Exception:
        pass

    return None


async def resolve_effective_persona(
    *,
    persona: str | None = None,
    user_id: str | None = None,
    request: Request | None = None,
) -> str | None:
    """Resolve persona from explicit input, request metadata, or active user profile."""
    resolved = resolve_request_persona(request, explicit_persona=persona)
    if resolved:
        return resolved

    effective_user_id = user_id
    if not effective_user_id:
        try:
            from app.services.request_context import get_current_user_id

            effective_user_id = get_current_user_id()
        except Exception:
            effective_user_id = None

    if not effective_user_id:
        return None

    try:
        from app.services.user_onboarding_service import get_user_onboarding_service

        profile_persona = await get_user_onboarding_service().get_user_persona(effective_user_id)
        return normalize_persona(profile_persona)
    except Exception:
        return None


def normalize_allowed_personas(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set)):
        raw_values = value
    else:
        raw_values = [value]

    normalized_values: list[str] = []
    for raw in raw_values:
        if raw is None:
            continue
        candidate = str(raw).strip().lower()
        if not candidate:
            continue
        if candidate == "all":
            normalized_values.append("all")
            continue
        persona = normalize_persona(candidate)
        if persona:
            normalized_values.append(persona)
    return tuple(dict.fromkeys(normalized_values))


def workflow_template_matches_persona(personas_allowed: Any, persona: str | None) -> bool:
    normalized_persona = normalize_persona(persona)
    allowed = normalize_allowed_personas(personas_allowed)
    if not normalized_persona:
        return True
    if not allowed or "all" in allowed:
        return True
    return normalized_persona in allowed


def workflow_template_persona_rank(personas_allowed: Any, persona: str | None) -> int:
    normalized_persona = normalize_persona(persona)
    if not normalized_persona:
        return 0

    allowed = normalize_allowed_personas(personas_allowed)
    if not allowed or "all" in allowed:
        return 1
    if normalized_persona in allowed:
        return 0
    return 2


def workflow_template_has_explicit_persona_scope(personas_allowed: Any) -> bool:
    return bool(normalize_allowed_personas(personas_allowed))


def filter_workflow_templates_for_persona(
    templates: Iterable[dict[str, Any]],
    persona: str | None,
) -> list[dict[str, Any]]:
    normalized_persona = normalize_persona(persona)
    filtered = [
        template
        for template in templates
        if workflow_template_matches_persona(template.get("personas_allowed"), normalized_persona)
    ]
    if not normalized_persona:
        return list(filtered)
    return sorted(
        filtered,
        key=lambda template: (
            workflow_template_persona_rank(template.get("personas_allowed"), normalized_persona),
            str(template.get("name") or "").lower(),
        ),
    )


def initiative_template_matches_persona(template_persona: Any, persona: str | None) -> bool:
    normalized_persona = normalize_persona(persona)
    if not normalized_persona:
        return True

    normalized_template_persona = normalize_persona(template_persona)
    if not normalized_template_persona:
        return True
    return normalized_template_persona == normalized_persona


def initiative_template_persona_rank(template_persona: Any, persona: str | None) -> int:
    normalized_persona = normalize_persona(persona)
    if not normalized_persona:
        return 0

    normalized_template_persona = normalize_persona(template_persona)
    if not normalized_template_persona:
        return 1
    if normalized_template_persona == normalized_persona:
        return 0
    return 2


def filter_initiative_templates_for_persona(
    templates: Iterable[dict[str, Any]],
    persona: str | None,
) -> list[dict[str, Any]]:
    normalized_persona = normalize_persona(persona)
    filtered = [
        template
        for template in templates
        if initiative_template_matches_persona(template.get("persona"), normalized_persona)
    ]
    if not normalized_persona:
        return list(filtered)
    return sorted(
        filtered,
        key=lambda template: (
            initiative_template_persona_rank(template.get("persona"), normalized_persona),
            str(template.get("title") or template.get("name") or "").lower(),
        ),
    )
