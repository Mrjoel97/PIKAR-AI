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

# Lazy import removed to fix ADK Web UI discovery issues
# The Web UI expects 'root_agent' to be present in the module namespace.

from .agent import app, executive_agent

# Expose root_agent directly for ADK Web UI
# We use the raw Agent, not the App wrapper, to avoid path resolution issues
root_agent = executive_agent

def get_app():
    """Getter for the main ADK app."""
    return app

__all__ = ["app", "get_app", "root_agent"]
