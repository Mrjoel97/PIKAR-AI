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

"""Shared utilities for agent modules."""

import os

from google.adk.models import Gemini
from google.genai import types

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
    """Get a configured Gemini model instance with retry options (primary agent model).

    Uses GEMINI_AGENT_MODEL_PRIMARY when model_name is not provided.
    Configures automatic retries for transient errors including rate limits.

    Args:
        model_name: Optional model name. If None, uses primary from env.

    Returns:
        A configured Gemini model instance with retry options.
    """
    name = model_name if model_name else GEMINI_AGENT_MODEL_PRIMARY
    return Gemini(model=name, retry_options=_make_retry_options())


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
    """Get the primary model for the executive orchestrator routing."""
    return Gemini(
        model=GEMINI_AGENT_MODEL_PRIMARY, retry_options=_make_retry_options()
    )
