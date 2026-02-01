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
from the 'app/skills/custom' directory. It allows agents to generate new
skill files that are automatically picked up by the system without restart.
"""

import os
import importlib
import logging
import inspect
import sys
from pathlib import Path
from typing import List

from app.skills.registry import Skill, skills_registry

logger = logging.getLogger(__name__)

CUSTOM_SKILLS_DIR = Path("app/skills/custom")


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
            
    return loaded_skills
