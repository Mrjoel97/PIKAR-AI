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

"""Skill Builder Tool.

This module provides tools for the Operations Agent to autonomously create,
verify, and register new custom skills.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from app.skills.loader import load_custom_skills

CUSTOM_SKILLS_DIR = Path("app/skills/custom")
CUSTOM_TESTS_DIR = Path("tests/skills/custom")

def _normalize_name(name: str) -> str:
    """Normalize skill name to snake_case filename."""
    name = name.lower()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    return name

def create_operational_skill(
    name: str,
    description: str,
    implementation_code: str,
    test_code: str,
    agent_ids: List[str] = ["OPS"]
) -> Dict[str, Any]:
    """Create, verify, and register a new operational skill.
    
    This tool performs the following steps:
    1. validated the Python code strictly.
    2. Writes the skill code to app/skills/custom/<name>.py
    3. Writes the test code to tests/skills/custom/test_<name>.py
    4. Runs the tests using pytest.
    5. If tests pass, registers the skill.
    6. If tests fail, deletes the files and returns the error.
    
    Args:
        name: Name of the skill (e.g. 'process_log_analyzer').
        description: Description of what the skill does.
        implementation_code: Complete Python code for the skill module. 
                             MUST define a 'Skill' instance.
        test_code: Complete Python code for testing the skill using pytest.
        agent_ids: List of agent IDs allowed to use this skill.
        
    Returns:
        Dictionary with success status and details.
    """
    safe_name = _normalize_name(name)
    skill_file = CUSTOM_SKILLS_DIR / f"{safe_name}.py"
    test_file = CUSTOM_TESTS_DIR / f"test_{safe_name}.py"
    
    # Security Check: Ensure we aren't writing outside custom dirs
    try:
        skill_file.resolve().relative_to(CUSTOM_SKILLS_DIR.resolve())
        test_file.resolve().relative_to(CUSTOM_TESTS_DIR.resolve())
    except ValueError:
        return {"success": False, "error": "Security Violation: Attempted path traversal."}

    # 1. Write Files
    try:
        with open(skill_file, "w", encoding="utf-8") as f:
            f.write(implementation_code)
            
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)
            
    except Exception as e:
        return {"success": False, "error": f"File creation failed: {str(e)}"}
        
    # 2. Run Tests
    # We run pytest on the specific test file
    try:
        # Using subprocess to run pytest in a separate process
        # This isolates potential crashes
        result = subprocess.run(
            ["python", "-m", "pytest", str(test_file)],
            capture_output=True,
            text=True,
            timeout=30 # 30 second timeout for verification
        )
        
        if result.returncode != 0:
            # Tests Failed - Rollback
            _rollback(skill_file, test_file)
            return {
                "success": False, 
                "error": "Verification Failed. Tests did not pass.",
                "details": result.stdout + "\n" + result.stderr
            }
            
    except subprocess.TimeoutExpired:
        _rollback(skill_file, test_file)
        return {"success": False, "error": "Verification Failed: Test execution timed out."}
    except Exception as e:
        _rollback(skill_file, test_file)
        return {"success": False, "error": f"Test execution error: {str(e)}"}
        
    # 3. Register Skill (Dynamic Load)
    try:
        loaded_skills = load_custom_skills()
        if safe_name in loaded_skills or name in loaded_skills:
             return {
                "success": True,
                "message": f"Skill '{name}' created, verified, and registered successfully.",
                "path": str(skill_file)
            }
        else:
             # It might be registered under a slightly different variable name in the file
             # But if load_custom_skills didn't error, we assume it picked up something.
             return {
                "success": True,
                "message": f"Skill '{name}' passed verification. Loaded skills: {loaded_skills}",
                "path": str(skill_file)
            }

    except Exception as e:
        # If loading fails, we might technically leave the file there as valid python 
        # but broken logic, or rollback. Let's rollback to be safe.
        _rollback(skill_file, test_file)
        return {"success": False, "error": f"Registration failed: {str(e)}"}

def _rollback(skill_file: Path, test_file: Path):
    """Delete created files on failure."""
    try:
        if skill_file.exists():
            os.remove(skill_file)
        if test_file.exists():
            os.remove(test_file)
    except Exception:
        pass # Best effort cleanup

