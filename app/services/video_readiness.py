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

"""Video generation readiness check (Veo + Remotion config only, no API calls)."""

import os
from pathlib import Path
from typing import Any, Dict

# Reuse same env logic as vertex_video_service
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_REMOTION_DIR = _REPO_ROOT / "remotion-render"
REMOTION_RENDER_DIR = os.getenv("REMOTION_RENDER_DIR", str(_DEFAULT_REMOTION_DIR))
REMOTION_RENDER_ENABLED = os.getenv("REMOTION_RENDER_ENABLED", "").strip().lower() in (
    "1",
    "true",
    "yes",
)


def get_video_readiness() -> Dict[str, Any]:
    """
    Return a read-only report of video generation configuration.
    Does not call Veo or Remotion APIs; only checks env and paths.
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv(
        "VERTEX_CREDENTIALS_PATH"
    )
    veo_configured = bool(project and credentials)

    # Optional: cheap client init (no network call if we only check env)
    veo_details: Dict[str, Any] = {
        "GOOGLE_CLOUD_PROJECT_set": bool(project),
        "credentials_set": bool(credentials),
    }
    if project:
        veo_details["GOOGLE_CLOUD_PROJECT"] = project

    remotion_enabled = REMOTION_RENDER_ENABLED
    render_dir = Path(REMOTION_RENDER_DIR)
    remotion_dir_exists = render_dir.is_dir()
    remotion_has_entry = False
    if remotion_dir_exists:
        # Expect package.json and src/index.tsx or similar
        remotion_has_entry = (
            (render_dir / "package.json").is_file()
            or (render_dir / "src" / "index.tsx").is_file()
        )
    remotion_configured = remotion_enabled and remotion_dir_exists and remotion_has_entry

    remotion_details: Dict[str, Any] = {
        "REMOTION_RENDER_ENABLED": remotion_enabled,
        "REMOTION_RENDER_DIR": REMOTION_RENDER_DIR,
        "dir_exists": remotion_dir_exists,
        "has_entrypoint": remotion_has_entry,
    }

    return {
        "veo_configured": veo_configured,
        "remotion_configured": remotion_configured,
        "details": {
            "veo": veo_details,
            "remotion": remotion_details,
        },
    }
