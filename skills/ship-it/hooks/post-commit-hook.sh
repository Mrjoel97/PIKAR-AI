#!/usr/bin/env bash
# Ship-it PostToolUse hook: triggers after a successful git commit via Bash tool
# Reads stdin JSON from Claude Code, checks if the command was a git commit
# AND the current branch is `main`, and only then injects the ship-it skill
# as additionalContext. Commits on feature branches are intentionally ignored
# so brainstorming/planning/iteration on feature branches stays unblocked.

INPUT=$(cat)

# Match git commit in the raw JSON (tool_input.command contains the bash command)
if echo "$INPUT" | grep -qE '"command".*git commit' && ! echo "$INPUT" | grep -q 'git commit --amend'; then
  # Branch gate: only fire on commits to main. Empty/error => not main => suppress.
  CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
  if [ "$CURRENT_BRANCH" = "main" ]; then
    cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "A commit was just created on main. You MUST now follow the ship-it CI/CD pipeline. Read skills/ship-it/SKILL.md and execute all 14 phases: scan, timing guard, quality gates (parallel backend+frontend), Supabase migration gate, env var diff, stage/commit, push/PR, merge, post-merge scan, performance baselines, canary deploy, verify + compare, auto-rollback, notification. Do NOT skip any phase."
  }
}
EOF
  fi
fi
