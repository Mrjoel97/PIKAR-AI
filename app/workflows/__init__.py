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

"""Pikar AI Workflow Agents - ADK-compliant orchestration patterns.

This package contains workflow agents using ADK patterns:
- SequentialAgent: Linear multi-step execution
- ParallelAgent: Concurrent execution
- LoopAgent: Iterative refinement with conditions

All workflows are composed of specialized agents from app.agents.
"""

# Workflow registry for catalog alignment
from app.workflows.registry import workflow_registry, get_workflow, list_workflows

# Category imports will be added as workflows are implemented
from app.workflows.initiative import *
from app.workflows.product import *
from app.workflows.sales import *
from app.workflows.marketing import *
from app.workflows.goals import *
from app.workflows.evaluation import *
from app.workflows.compliance import *
from app.workflows.hr import *
from app.workflows.documentation import *
from app.workflows.knowledge import *
from app.workflows.dynamic import *

__all__ = ["workflow_registry", "get_workflow", "list_workflows"]
