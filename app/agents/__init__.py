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

"""Agents module - Contains all AI agent definitions."""

from app.agents.specialized_agents import (
    financial_agent,
    content_agent,
    strategic_agent,
    sales_agent,
    marketing_agent,
    operations_agent,
    hr_agent,
    compliance_agent,
    customer_support_agent,
    data_agent,
    SPECIALIZED_AGENTS,
)

__all__ = [
    "financial_agent",
    "content_agent",
    "strategic_agent",
    "sales_agent",
    "marketing_agent",
    "operations_agent",
    "hr_agent",
    "compliance_agent",
    "customer_support_agent",
    "data_agent",
    "SPECIALIZED_AGENTS",
]
