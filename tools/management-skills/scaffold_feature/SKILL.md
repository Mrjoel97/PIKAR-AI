---
name: scaffold_feature
description: Enforces Test-Driven Development (TDD) by scaffolding test files before implementation.
---

# Scaffold Feature Skill

Enforces **Test-Driven Development (TDD)** by automatically generating the necessary test infrastructure before the implementation file is created.

## Available Scripts

### 1. New Feature
**Description**: Creates a corresponding unit test file and a basic implementation stub for a new feature.
**Usage**:
```python
python .agent/skills/scaffold_feature/scripts/scaffolder.py <feature_name> [layer]
```
*   `feature_name`: Snake_case name of the feature (e.g., `user_profile`).
*   `layer`: (Optional) Directory for implementation, default `app` (e.g., `app`, `core`, `conductor`).

**Example**:
```bash
# Creates tests/unit/test_payment_processor.py and app/payment_processor.py
python .agent/skills/scaffold_feature/scripts/scaffolder.py payment_processor
```
