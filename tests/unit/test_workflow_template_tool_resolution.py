from scripts.verify.validate_workflow_templates import validate_templates


def test_workflow_templates_resolve_tools():
    total, errors = validate_templates()
    assert total >= 68
    assert not errors, f"Unresolved workflow template tools detected: {errors[:10]}"
