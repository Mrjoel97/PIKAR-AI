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

"""Dynamic Skill Loader.

This module provides functionality to dynamically discover and load skills
from the 'app/skills/custom' directory and from 'skills/*/SKILL.md' markdown
files. It allows agents to generate new skill files that are automatically
picked up by the system without restart.
"""

import os
import importlib
import logging
import inspect
import re
import sys
from pathlib import Path
from typing import List

from app.skills.registry import Skill, skills_registry

logger = logging.getLogger(__name__)

CUSTOM_SKILLS_DIR = Path("app/skills/custom")
SKILLMD_DIR = Path("skills")


def load_custom_skills() -> List[str]:
    """Scan custom skills directory and register all found skills.
    
    Returns:
        List of names of successfully loaded skills.
    """
    loaded_skills = []
    
    # Ensure directory exists
    if not CUSTOM_SKILLS_DIR.exists():
        logger.warning(f"Custom skills directory {CUSTOM_SKILLS_DIR} does not exist.")
        return []

    # Add project root to path so imports work correctly
    project_root = Path.cwd()
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))

    logger.info(f"Scanning for custom skills in {CUSTOM_SKILLS_DIR}...")

    for file_path in CUSTOM_SKILLS_DIR.glob("**/*.py"):
        if file_path.name == "__init__.py":
            continue
            
        # Convert path to module name (e.g., app.skills.custom.my_skill)
        # We need relative path from project root
        try:
            rel_path = file_path.relative_to(project_root)
        except ValueError:
            # If not relative to root (e.g. absolute path provided), try typical structure
            rel_path = file_path
            
        module_name = str(rel_path).replace(os.path.sep, ".").replace(".py", "")
        
        try:
            # Force reload if already imported (to support updates)
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)
                
            # Inspect module for Skill instances
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, Skill):
                    # Register the skill
                    skills_registry.register(obj)
                    loaded_skills.append(obj.name)
                    logger.info(f"Loaded custom skill: {obj.name} from {module_name}")
                    
        except Exception as e:
            logger.error(f"Failed to load custom skill from {file_path}: {e}")
            continue

    # Also load SKILL.md files from the skills/ directory
    loaded_skills.extend(load_skillmd_files())

    return loaded_skills


def _parse_skillmd_frontmatter(content: str) -> dict:
    """Parse YAML-style frontmatter from a SKILL.md file.

    Returns a dict with 'name', 'description', and 'body' keys.
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return {}

    frontmatter_text = match.group(1)
    body = match.group(2).strip()

    meta: dict = {}
    for line in frontmatter_text.splitlines():
        key_val = line.split(":", 1)
        if len(key_val) == 2:
            key = key_val[0].strip()
            val = key_val[1].strip().strip('"').strip("'")
            meta[key] = val

    meta["body"] = body
    return meta


def _build_knowledge_summary(body: str, max_lines: int = 5) -> str:
    """Extract the first few meaningful lines as a knowledge summary."""
    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
        if len(lines) >= max_lines:
            break
    return " ".join(lines)


# Map SKILL.md folder names to agent categories / agent IDs
_SKILLMD_AGENT_MAP: dict[str, list] = {
    "marketing": ["MKT", "CONT", "STRAT"],
    "google-cloud-run-ops": ["OPS", "EXEC"],
}

_SKILLMD_CATEGORY_MAP: dict[str, str] = {
    "marketing": "marketing",
    "google-cloud-run-ops": "operations",
}


def load_skillmd_files() -> List[str]:
    """Scan skills/*/SKILL.md and register each as a Skill in the registry.

    Returns:
        List of names of successfully loaded skills.
    """
    from app.skills.registry import AgentID

    loaded: list[str] = []

    if not SKILLMD_DIR.exists():
        return loaded

    for skill_file in SKILLMD_DIR.glob("*/SKILL.md"):
        try:
            content = skill_file.read_text(encoding="utf-8")
            meta = _parse_skillmd_frontmatter(content)
            if not meta.get("name"):
                logger.warning("SKILL.md at %s missing 'name' in frontmatter, skipping", skill_file)
                continue

            name = meta["name"]
            folder_name = skill_file.parent.name
            description = meta.get("description", f"Skill loaded from {folder_name}/SKILL.md")
            body = meta.get("body", "")
            category = _SKILLMD_CATEGORY_MAP.get(folder_name, "general")

            # Resolve agent IDs
            agent_id_strings = _SKILLMD_AGENT_MAP.get(folder_name, [])
            agent_ids = []
            for aid_str in agent_id_strings:
                try:
                    agent_ids.append(AgentID(aid_str))
                except ValueError:
                    logger.warning("Unknown AgentID '%s' for SKILL.md '%s'", aid_str, name)

            skill = Skill(
                name=name,
                description=description,
                category=category,
                agent_ids=agent_ids,
                knowledge=body,
                knowledge_summary=_build_knowledge_summary(body),
                version="1.0.0",
            )
            skills_registry.register(skill)
            loaded.append(name)
            logger.info("Loaded SKILL.md skill: %s from %s", name, skill_file)

        except Exception as e:
            logger.error("Failed to load SKILL.md from %s: %s", skill_file, e)

    return loaded
