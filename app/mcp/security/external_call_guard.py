# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared guardrails for outbound MCP tool invocations.

This module centralizes PII-aware handling for external-facing tool calls.
It can either redact values before they leave the platform or inspect them
for audit-only scenarios where the downstream integration legitimately needs
the original payload.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.mcp.security.pii_filter import PIIFilter

_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "auth",
    "code",
    "dob",
    "email",
    "first_name",
    "last_name",
    "name",
    "passcode",
    "password",
    "phone",
    "secret",
    "ssn",
    "token",
}

_SENSITIVE_FIELD_MARKERS = {
    "access_token",
    "anon_key",
    "api_key",
    "authorization",
    "password",
    "secret",
    "secret_key",
    "service_role_key",
    "token",
    "webhook_url",
}

_SECRET_REDACTION = "[SECRET_REDACTED]"
_URL_REDACTION = "[URL_REDACTED]"


@dataclass(frozen=True)
class ExternalCallGuardResult:
    """Result returned by an outbound guardrail operation."""

    outbound_value: str
    audit_value: str
    metadata: dict[str, Any]


def _build_filter(context_names: Iterable[str] | None = None) -> PIIFilter:
    pii_filter = PIIFilter()
    if context_names:
        pii_filter.set_context_names(list(context_names))
    return pii_filter


def _field_name_is_sensitive(field_name: str | None) -> bool:
    if not field_name:
        return False
    lowered = str(field_name).strip().lower()
    return any(marker in lowered for marker in _SENSITIVE_FIELD_MARKERS)


def _merge_metadata(
    *,
    field_name: str,
    redact_for_outbound: bool,
    redacted_value: str,
    original_value: str,
    pii_types: set[str],
    redaction_count: int,
    sensitive_field_detected: bool,
) -> dict[str, Any]:
    return {
        "guarded_field": field_name,
        "guardrail_mode": "redact" if redact_for_outbound else "audit_only",
        "pii_detected": bool(pii_types) or sensitive_field_detected,
        "redaction_count": redaction_count,
        "pii_types": sorted(pii_types),
        "sensitive_field_detected": sensitive_field_detected,
        "outbound_redacted": redact_for_outbound and redacted_value != original_value,
    }


def protect_text_payload(
    value: str,
    *,
    field_name: str = "payload",
    context_names: Iterable[str] | None = None,
    redact_for_outbound: bool = True,
) -> ExternalCallGuardResult:
    """Protect free-form text before an outbound call or audit write."""

    pii_filter = _build_filter(context_names)
    safe_value = pii_filter.sanitize(value)
    matches = pii_filter.find_pii(value)
    pii_types = {match.pii_type for match in matches}
    sensitive_field_detected = _field_name_is_sensitive(field_name)

    if sensitive_field_detected:
        safe_value = _SECRET_REDACTION
        pii_types.add("sensitive_field")

    redaction_count = len(matches)
    if sensitive_field_detected:
        redaction_count = max(1, redaction_count)

    metadata = _merge_metadata(
        field_name=field_name,
        redact_for_outbound=redact_for_outbound,
        redacted_value=safe_value,
        original_value=value,
        pii_types=pii_types,
        redaction_count=redaction_count,
        sensitive_field_detected=sensitive_field_detected,
    )
    return ExternalCallGuardResult(
        outbound_value=safe_value if redact_for_outbound else value,
        audit_value=safe_value,
        metadata=metadata,
    )


def protect_url_payload(
    url: str,
    *,
    field_name: str = "url",
    context_names: Iterable[str] | None = None,
    redact_for_outbound: bool = True,
) -> ExternalCallGuardResult:
    """Protect URLs by redacting PII-looking path and query values."""

    pii_filter = _build_filter(context_names)
    sensitive_field_detected = _field_name_is_sensitive(field_name)
    if sensitive_field_detected:
        metadata = _merge_metadata(
            field_name=field_name,
            redact_for_outbound=redact_for_outbound,
            redacted_value=_URL_REDACTION,
            original_value=url,
            pii_types={"sensitive_field"},
            redaction_count=1,
            sensitive_field_detected=True,
        )
        return ExternalCallGuardResult(
            outbound_value=url if not redact_for_outbound else _URL_REDACTION,
            audit_value=_URL_REDACTION,
            metadata=metadata,
        )

    parsed = urlsplit(url)
    safe_path = pii_filter.sanitize(parsed.path)
    safe_fragment = pii_filter.sanitize(parsed.fragment)

    redacted_query_keys: list[str] = []
    pii_types = {match.pii_type for match in pii_filter.find_pii(url)}
    redaction_count = 0
    sanitized_pairs: list[tuple[str, str]] = []

    for raw_key, raw_value in parse_qsl(parsed.query, keep_blank_values=True):
        safe_key = pii_filter.sanitize(raw_key)
        value_matches = pii_filter.find_pii(raw_value)
        key_sensitive = raw_key.strip().lower() in _SENSITIVE_QUERY_KEYS
        if key_sensitive:
            pii_types.add("sensitive_query_param")
            redacted_query_keys.append(raw_key)
            safe_value = "[QUERY_VALUE_REDACTED]" if raw_value else ""
            redaction_count += max(1, len(value_matches))
        elif value_matches:
            safe_value = pii_filter.sanitize(raw_value)
            redaction_count += len(value_matches)
        else:
            safe_value = raw_value
        sanitized_pairs.append((safe_key, safe_value))

    audit_value = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            safe_path,
            urlencode(sanitized_pairs, doseq=True),
            safe_fragment,
        )
    )

    metadata = _merge_metadata(
        field_name=field_name,
        redact_for_outbound=redact_for_outbound,
        redacted_value=audit_value,
        original_value=url,
        pii_types=pii_types,
        redaction_count=redaction_count,
        sensitive_field_detected=False,
    )
    metadata["redacted_query_keys"] = sorted(set(redacted_query_keys))
    return ExternalCallGuardResult(
        outbound_value=audit_value if redact_for_outbound else url,
        audit_value=audit_value,
        metadata=metadata,
    )


def summarize_payload_for_audit(
    payload: Mapping[str, Any],
    *,
    field_name: str = "payload",
    context_names: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Inspect a structured payload and return sanitized audit metadata."""

    pii_filter = _build_filter(context_names)
    fields_with_pii: list[str] = []
    redaction_count = 0
    pii_types: set[str] = set()

    def _visit(value: Any, path: str) -> Any:
        nonlocal redaction_count
        leaf_name = path.split(".")[-1].split("[")[0] if path else field_name
        if _field_name_is_sensitive(leaf_name):
            fields_with_pii.append(path or leaf_name)
            pii_types.add("sensitive_field")
            redaction_count += 1
            return _SECRET_REDACTION
        if isinstance(value, str):
            matches = pii_filter.find_pii(value)
            if matches:
                fields_with_pii.append(path or field_name)
                redaction_count += len(matches)
                pii_types.update(match.pii_type for match in matches)
                return pii_filter.sanitize(value)
            return value
        if isinstance(value, Mapping):
            return {
                str(key): _visit(item, f"{path}.{key}" if path else str(key))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [
                _visit(item, f"{path}[{index}]")
                for index, item in enumerate(value[:20])
            ]
        return value

    sanitized_payload = _visit(dict(payload), "")
    audit_preview = json.dumps(sanitized_payload, default=str, sort_keys=True)

    return {
        "guarded_field": field_name,
        "guardrail_mode": "audit_only",
        "pii_detected": bool(fields_with_pii),
        "redaction_count": redaction_count,
        "pii_types": sorted(pii_types),
        "fields_with_pii": fields_with_pii[:20],
        "audit_preview": audit_preview[:500],
    }
