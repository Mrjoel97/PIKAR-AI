---
description: Automated Project Management (Conductor)
---

# Automated Project Management

Use the `project_automator` script to manage tasks according to the strict Pikar-Ai Conductor protocol.

## Start a Task (NLP)
This will fuzzy-match your instruction to a task in `plan.md` or create a new one.
```bash
python scripts/project_automator.py start "Fix the database schema"
```

## Complete a Task
This will:
1. Run Tests
2. Commit changes
3. Add Git Note (Summary + Why)
4. Update `plan.md` with SHA
5. **Git Push**

```bash
python scripts/project_automator.py complete "Fixed missing tables in schema" "Required for Service layer"
```
