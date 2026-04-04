# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Webhook event catalog and type definitions.

Defines the canonical set of webhook event types that Pikar emits for
outbound delivery, along with JSON Schema payload definitions for each.
"""

from __future__ import annotations

import enum


class WebhookEventType(str, enum.Enum):
    """Canonical webhook event types emitted by Pikar."""

    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    APPROVAL_PENDING = "approval.pending"
    APPROVAL_DECIDED = "approval.decided"
    INITIATIVE_PHASE_CHANGED = "initiative.phase_changed"
    CONTACT_SYNCED = "contact.synced"
    INVOICE_CREATED = "invoice.created"


EVENT_CATALOG: dict[str, dict] = {
    "task.created": {
        "description": "A new task has been created.",
        "payload_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "format": "uuid"},
                "title": {"type": "string"},
                "status": {"type": "string"},
                "created_by": {"type": "string", "format": "uuid"},
                "created_at": {"type": "string", "format": "date-time"},
            },
            "required": ["task_id", "title", "status", "created_by", "created_at"],
        },
    },
    "task.updated": {
        "description": "An existing task has been updated.",
        "payload_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "format": "uuid"},
                "title": {"type": "string"},
                "status": {"type": "string"},
                "updated_by": {"type": "string", "format": "uuid"},
                "updated_at": {"type": "string", "format": "date-time"},
                "changes": {
                    "type": "object",
                    "description": "Key-value map of changed fields with old/new values.",
                },
            },
            "required": ["task_id", "status", "updated_at"],
        },
    },
    "workflow.started": {
        "description": "A workflow execution has started.",
        "payload_schema": {
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "format": "uuid"},
                "template_id": {"type": "string", "format": "uuid"},
                "template_name": {"type": "string"},
                "started_by": {"type": "string", "format": "uuid"},
                "started_at": {"type": "string", "format": "date-time"},
            },
            "required": ["execution_id", "template_id", "started_at"],
        },
    },
    "workflow.completed": {
        "description": "A workflow execution has completed.",
        "payload_schema": {
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "format": "uuid"},
                "template_id": {"type": "string", "format": "uuid"},
                "template_name": {"type": "string"},
                "status": {"type": "string", "enum": ["completed", "failed", "cancelled"]},
                "completed_at": {"type": "string", "format": "date-time"},
                "duration_seconds": {"type": "number"},
            },
            "required": ["execution_id", "template_id", "status", "completed_at"],
        },
    },
    "approval.pending": {
        "description": "A new approval request is awaiting a decision.",
        "payload_schema": {
            "type": "object",
            "properties": {
                "approval_id": {"type": "string", "format": "uuid"},
                "request_type": {"type": "string"},
                "title": {"type": "string"},
                "requested_by": {"type": "string", "format": "uuid"},
                "created_at": {"type": "string", "format": "date-time"},
            },
            "required": ["approval_id", "request_type", "title", "created_at"],
        },
    },
    "approval.decided": {
        "description": "An approval request has been decided (approved or rejected).",
        "payload_schema": {
            "type": "object",
            "properties": {
                "approval_id": {"type": "string", "format": "uuid"},
                "decision": {"type": "string", "enum": ["approved", "rejected"]},
                "decided_by": {"type": "string", "format": "uuid"},
                "decided_at": {"type": "string", "format": "date-time"},
                "reason": {"type": "string"},
            },
            "required": ["approval_id", "decision", "decided_at"],
        },
    },
    "initiative.phase_changed": {
        "description": "An initiative has moved to a new phase.",
        "payload_schema": {
            "type": "object",
            "properties": {
                "initiative_id": {"type": "string", "format": "uuid"},
                "initiative_name": {"type": "string"},
                "previous_phase": {"type": "string"},
                "new_phase": {"type": "string"},
                "changed_at": {"type": "string", "format": "date-time"},
            },
            "required": ["initiative_id", "previous_phase", "new_phase", "changed_at"],
        },
    },
    "contact.synced": {
        "description": "A contact has been synced from an external CRM.",
        "payload_schema": {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string", "format": "uuid"},
                "provider": {"type": "string"},
                "external_id": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "name": {"type": "string"},
                "synced_at": {"type": "string", "format": "date-time"},
            },
            "required": ["contact_id", "provider", "synced_at"],
        },
    },
    "invoice.created": {
        "description": "A new invoice has been created.",
        "payload_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string", "format": "uuid"},
                "amount": {"type": "number"},
                "currency": {"type": "string"},
                "customer_id": {"type": "string"},
                "due_date": {"type": "string", "format": "date"},
                "created_at": {"type": "string", "format": "date-time"},
            },
            "required": ["invoice_id", "amount", "currency", "created_at"],
        },
    },
}


def get_event_schema(event_type: str) -> dict | None:
    """Return the JSON Schema for a given event type, or None if unknown.

    Args:
        event_type: Dotted event name (e.g. ``"task.created"``).

    Returns:
        The payload JSON Schema dict, or ``None`` for unrecognised types.
    """
    entry = EVENT_CATALOG.get(event_type)
    if entry is None:
        return None
    return entry["payload_schema"]
