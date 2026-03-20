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
import os
import uuid
from typing import (
    Any,
    Literal,
)

BYPASS_IMPORT = os.environ.get("LOCAL_DEV_BYPASS") == "1"

if not BYPASS_IMPORT:
    from google.adk.events.event import Event
    from google.genai.types import Content
else:
    Event = Any
    Content = Any
from pydantic import (
    BaseModel,
    Field,
)


class Request(BaseModel):
    """Represents the input for a chat request with optional configuration."""

    message: Content
    events: list[Event]
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    model_config = {"extra": "allow"}


class Feedback(BaseModel):
    """Represents feedback for a conversation."""

    score: int | float
    text: str | None = ""
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal["pikar-ai"] = "pikar-ai"
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
