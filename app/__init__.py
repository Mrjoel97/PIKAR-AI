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

"""Application package entrypoint.

Use lazy attribute loading so importing `app` for API modules does not eagerly
import heavy ADK/GenAI dependencies.
"""

from typing import Any


def get_app():
    """Getter for the main ADK app."""
    from .agent import app as _app

    return _app


def __getattr__(name: str) -> Any:
    if name in {"app", "executive_agent", "root_agent"}:
        from .agent import app as _app
        from .agent import executive_agent as _executive_agent

        if name == "app":
            return _app
        if name == "executive_agent":
            return _executive_agent
        return _executive_agent
    raise AttributeError(name)


__all__ = ["app", "executive_agent", "get_app", "root_agent"]
