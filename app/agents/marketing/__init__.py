# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Marketing Automation Agent Module."""

from app.agents.marketing.agent import create_marketing_agent, marketing_agent
from app.agents.marketing.tools import (
    create_campaign,
    get_campaign,
    list_campaigns,
    record_campaign_metrics,
    update_campaign,
)

__all__ = [
    "create_campaign",
    "create_marketing_agent",
    "get_campaign",
    "list_campaigns",
    "marketing_agent",
    "record_campaign_metrics",
    "update_campaign",
]
