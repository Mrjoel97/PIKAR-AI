# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Marketing Automation Agent Module."""

from app.agents.marketing.agent import marketing_agent, create_marketing_agent
from app.agents.marketing.tools import (
    create_campaign,
    get_campaign,
    update_campaign,
    list_campaigns,
    record_campaign_metrics,
)

__all__ = [
    "marketing_agent",
    "create_marketing_agent",
    "create_campaign",
    "get_campaign",
    "update_campaign",
    "list_campaigns",
    "record_campaign_metrics",
]
