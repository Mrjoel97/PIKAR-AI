from app.skills.registry import AgentID, Skill


def calculator_func(a: int, b: int) -> int:
    return a + b


test_math_skill = Skill(
    name="test_math_skill",
    description="A simple math skill for testing builder",
    category="operations",
    agent_ids=[AgentID.OPS],
    implementation=calculator_func,
)
