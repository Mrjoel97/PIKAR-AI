---
name: conductor_phase
description: Automates Pikar-Ai Phase Verification and Checkpointing protocol.
---

# Conductor Phase Skill

Automates the rigorous audit and checkpointing process required at the end of every project phase.

## Available Scripts

### 1. Audit Changes
**Description**: Lists all files changed since the *last checkpoint* (or initial commit). Use this to verify that every changed code file has a corresponding test.
**Usage**:
```python
python .agent/skills/conductor_phase/scripts/phase_manager.py audit
```

### 2. Create Checkpoint
**Description**: 
1. Generates an **empty commit** to mark the phase end.
2. Attaches an audit report (list of changed files) as a `git note`.
3. Appends `[checkpoint: <sha>]` to `plan.md`.

**Arguments**:
*   `summary`: A description of the completed phase.

**Usage**:
```python
python .agent/skills/conductor_phase/scripts/phase_manager.py checkpoint "Completed Phase 1 integration"
```
