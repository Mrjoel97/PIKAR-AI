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

"""Shared utilities for agent modules."""

from google.adk.models import Gemini
from google.genai import types


def get_model(model_name: str = "gemini-2.5-flash") -> Gemini:
    """Get a configured Gemini model instance.
    
    Args:
        model_name: The name of the Gemini model to use.
        
    Returns:
        A configured Gemini model instance with retry options.
    """
    return Gemini(
        model=model_name,
        retry_options=types.HttpRetryOptions(attempts=3),
    )
