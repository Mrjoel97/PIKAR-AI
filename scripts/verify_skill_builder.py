
import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from app.agents.tools.skill_builder import create_operational_skill
from app.skills import skills_registry

def test_skill_builder_manually():
    print("Testing Skill Builder...")
    
    skill_code = """
from app.skills.registry import Skill, AgentID

def calculator_func(a: int, b: int) -> int:
    return a + b

test_math_skill = Skill(
    name="test_math_skill",
    description="A simple math skill for testing builder",
    category="operations",
    agent_ids=[AgentID.OPS],
    implementation=calculator_func
)
"""

    test_code = """
import pytest
from app.skills.custom.test_math_skill import calculator_func

def test_calculator():
    assert calculator_func(5, 10) == 15
    assert calculator_func(-1, 1) == 0
"""

    # 1. Invoke the tool
    result = create_operational_skill(
        name="test_math_skill",
        description="Math Test",
        implementation_code=skill_code,
        test_code=test_code
    )
    
    print("Tool Result:", result)
    
    if not result["success"]:
        print("FAILED: Tool returned failure.")
        sys.exit(1)

    # 2. Verify Registry
    skill = skills_registry.get("test_math_skill")
    if skill:
        print("SUCCESS: Skill found in registry!")
        print(f"Skill Desc: {skill.description}")
        
        # 3. Test Usage
        exec_result = skills_registry.use_skill("test_math_skill", agent_id=None, a=10, b=20)
        print("Execution Result:", exec_result)
        if exec_result.get("output") == 30:
            print("VERIFIED: Skill execution works.")
        else:
            print("FAILED: Skill execution output wrong.")
    else:
        print("FAILED: Skill NOT found in registry after creation.")

if __name__ == "__main__":
    test_skill_builder_manually()
