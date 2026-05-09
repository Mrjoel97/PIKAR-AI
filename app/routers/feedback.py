# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Feedback collection endpoint."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter

from app.app_utils.typing import Feedback

logger = logging.getLogger(__name__)
router = APIRouter()


def _log_feedback_payload(payload: dict) -> None:
    """Log feedback payload with compatibility across logger backends."""
    if hasattr(logger, "log_struct"):
        logger.log_struct(payload, severity="INFO")
        return

    logger.info("feedback=%s", json.dumps(payload, default=str))


@router.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback."""
    _log_feedback_payload(feedback.model_dump())
    return {"status": "success"}
