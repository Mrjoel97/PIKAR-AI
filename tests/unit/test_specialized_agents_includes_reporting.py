# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Regression test: DataReportingAgent must be wired into SPECIALIZED_AGENTS.

The Executive Agent delegates to the agents listed in SPECIALIZED_AGENTS.
DataReportingAgent was previously missing from this list, which silently
prevented delegation for scheduled reports / Google Docs / weekly executive
report flows.
"""

from app.agents.specialized_agents import SPECIALIZED_AGENTS, data_reporting_agent


def test_data_reporting_agent_in_specialized_agents() -> None:
    """data_reporting_agent must be present in the SPECIALIZED_AGENTS list."""
    assert data_reporting_agent in SPECIALIZED_AGENTS, (
        "DataReportingAgent is missing from SPECIALIZED_AGENTS — Executive cannot "
        "delegate scheduled reports / Google Docs / Forms / Gmail delivery work."
    )
