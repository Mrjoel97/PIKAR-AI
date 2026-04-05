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
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared utilities for agent modules."""

import logging
import os

from google.adk.models import Gemini, LiteLlm
from google.genai import types

from app.services.model_failover import model_failover

logger = logging.getLogger(__name__)

# Agent LLM: Gemini 2.5 Pro primary, Gemini 2.5 Flash fallback (env overridable)
GEMINI_AGENT_MODEL_PRIMARY = os.getenv("GEMINI_AGENT_MODEL_PRIMARY", "gemini-2.5-pro")
GEMINI_AGENT_MODEL_FALLBACK = os.getenv(
    "GEMINI_AGENT_MODEL_FALLBACK", "gemini-2.5-flash"
)

# Token budget per session (default: 1,000,000 tokens; 0 = unlimited)
SESSION_TOKEN_BUDGET = int(os.getenv("SESSION_TOKEN_BUDGET", "1000000"))


def _make_retry_options() -> types.HttpRetryOptions:
    return types.HttpRetryOptions(
        attempts=5,
        initial_delay=2.0,
        exp_base=2.0,
        max_delay=60.0,
    )


# =============================================================================
# Performance-tuned GenerateContentConfig profiles
# =============================================================================

# Fast: For routing, delegation, tool-calling agents (Executive, Operations, HR, Support)
FAST_AGENT_CONFIG = types.GenerateContentConfig(
    temperature=0.3,
    max_output_tokens=2048,
    top_p=0.9,
)

# Routing: For delegation-heavy agents that don't need long outputs
ROUTING_AGENT_CONFIG = types.GenerateContentConfig(
    temperature=0.2,
    max_output_tokens=1024,
    top_p=0.85,
)

# Deep: For analysis agents that need precision (Financial, Data, Strategic, Compliance)
DEEP_AGENT_CONFIG = types.GenerateContentConfig(
    temperature=0.5,
    max_output_tokens=4096,
    top_p=0.95,
)

# Creative: For content generation agents (Content, Marketing)
CREATIVE_AGENT_CONFIG = types.GenerateContentConfig(
    temperature=0.7,
    max_output_tokens=4096,
    top_p=0.95,
)


def get_model(model_name: str | None = None) -> Gemini:
    """Get a configured Gemini model instance with automatic failover.

    When no explicit model name is provided the circuit-breaker-managed
    selection is used: primary (gemini-2.5-pro) while healthy, fallback
    (gemini-2.5-flash) while the primary circuit is open.  Passing an
    explicit ``model_name`` bypasses failover and always uses that model.

    Args:
        model_name: Optional model name override.  If None, uses the
            failover-managed model selection.

    Returns:
        A configured Gemini model instance with retry options.
    """
    if model_name:
        # Explicit model requested — bypass failover
        return Gemini(model=model_name, retry_options=_make_retry_options())
    # Use failover-managed model selection
    return model_failover.get_active_model(retry_options=_make_retry_options())


def get_fallback_model() -> Gemini:
    """Get the fallback Gemini model (used when primary is unavailable)."""
    return Gemini(
        model=GEMINI_AGENT_MODEL_FALLBACK, retry_options=_make_retry_options()
    )


def get_fast_model() -> Gemini:
    """Get Flash model for lightweight sub-tasks (HR, Ops, Support)."""
    return Gemini(
        model=GEMINI_AGENT_MODEL_FALLBACK, retry_options=_make_retry_options()
    )


def get_routing_model() -> Gemini:
    """Get the model for the executive orchestrator routing, with failover.

    Uses the same circuit-breaker-managed selection as ``get_model()`` so
    that routing decisions also benefit from automatic failover when the
    primary model is unavailable.
    """
    return model_failover.get_active_model(retry_options=_make_retry_options())


async def get_model_for_user(
    user_id: str, model_name: str | None = None
) -> Gemini | LiteLlm:
    """Get a model instance, using the user's BYOK config if available.

    If the user has an active BYOK configuration (e.g. OpenAI or Anthropic key),
    returns a LiteLlm-backed model. Otherwise falls back to the default Gemini
    model with failover.

    Args:
        user_id: The authenticated user's ID.
        model_name: Optional explicit model override (bypasses both BYOK and failover).

    Returns:
        A Gemini or LiteLlm model instance.
    """
    if model_name:
        return Gemini(model=model_name, retry_options=_make_retry_options())

    try:
        from app.services.byok_service import get_byok_service

        cfg = await get_byok_service().get_config(user_id)
        if cfg and cfg.is_active:
            logger.info(
                "BYOK active for user %s: provider=%s model=%s",
                user_id,
                cfg.provider,
                cfg.model,
            )
            return LiteLlm(model=cfg.litellm_model, api_key=cfg.api_key)
    except Exception as e:
        logger.warning(
            "BYOK resolution failed for user %s, falling back to Gemini: %s",
            user_id,
            e,
        )

    return model_failover.get_active_model(retry_options=_make_retry_options())
