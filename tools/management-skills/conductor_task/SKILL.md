---
name: conductor_task
description: Automates the Pikar-Ai Conductor Task Workflow. correctly managing plan.md, git commits, and git notes.
---

# Conductor Task Skill

This skill allows you to mechanically enforce the project's strict engineering workflow defined in `conductor/workflow.md`.

## Available Scripts

### 1. Start Next Task
**Description**: Locates the active track's `plan.md`, finds the next pending task, and marks it as IN_PROGRESS `[~]`.
**Usage**:
```python
# Run via terminal
python .agent/skills/conductor_task/scripts/task_manager.py start
```

### 2. Verify Work (Quality Gate)
**Description**: Runs the project's test suite and coverage analysis. MUST PASS before completion.
**Usage**:
```bash
# Run tests
make test
# Run coverage
uv run pytest --cov=app --cov-report=term-missing
```

### 3. Complete Task
**Description**: 
1. Stages and commits all changes.
2. Adds a detailed `git note` to the commit.
3. Updates `plan.md` marking the task `[x]` and appending the commit SHA.
4. Commits the plan update.

**Arguments**:
*   `summary`: A detailed description of what changed.
*   `why`: The architectural or business reason for the change.

**Usage**:
```python
# Run via terminal (ensure quotes around strings)
python .agent/skills/conductor_task/scripts/task_manager.py complete "Implemented feature X" "Required for module Y"
```

## Workflow Rules
1.  **One at a time**: You cannot start a task if one is already `[~]`.
2.  **Test First**: Always ensure `verify_work` passes.
3.  **No Manual Plan Edits**: Use this skill instead of manually editing `plan.md` to avoid format errors or missing SHAs.
