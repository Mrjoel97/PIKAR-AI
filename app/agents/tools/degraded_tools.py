# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Degraded workflow tools — fully retired as of Phase 70.

All tools have been promoted to real implementations:
- analyze_sentiment -> app/agents/tools/sentiment_analysis.py (Phase 70-01)
- ocr_document      -> app/agents/tools/ocr_tools.py (Phase 70-01)
- All other tools   -> promoted in app/agents/tools/registry.py (Phase 70-02)

This module is kept as an empty placeholder so that any direct imports
from external code fail gracefully with a clear error rather than an
AttributeError. Do not add new degraded tools here.
"""
