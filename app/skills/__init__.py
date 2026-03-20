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

"""Skills Package - Agent capability enhancement system."""

from app.skills import (
    library,  # Registers all skills on import
    professional_finance_legal,  # 16 finance + legal skills
    professional_marketing_sales,  # 14 marketing + sales skills
    professional_operations_data,  # 16 operations + data skills
    professional_pm_productivity_content,  # 16 PM + productivity + content skills
)
from app.skills.registry import Skill, SkillsRegistry, get_skill_tool, skills_registry

__all__ = [
    "Skill",
    "SkillsRegistry",
    "get_skill_tool",
    "library",
    "professional_finance_legal",
    "professional_marketing_sales",
    "professional_operations_data",
    "professional_pm_productivity_content",
    "skills_registry",
]
