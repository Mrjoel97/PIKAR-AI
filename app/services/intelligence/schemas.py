"""Shared Pydantic models and type aliases for the intelligence package.

Plan 112-02 ships only ConfidenceBand. Plan 112-03 extends this module
with ClaimSource, Claim, ClaimPayload.
"""

from __future__ import annotations

from typing import Literal

ConfidenceBand = Literal["low", "medium", "high"]
