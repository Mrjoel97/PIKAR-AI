#!/usr/bin/env bash
# Ship-it PostToolUse hook: triggers after a successful git commit via Bash tool
# Reads stdin JSON from Claude Code, checks if the command was a git commit
# AND the current branch is `main`, and only then injects the ship-it skill
# as additionalContext. Commits on feature branches are intentionally ignored
# so brainstorming/planning/iteration on feature branches stays unblocked.
#
# Docs-only filter: if every file in the most recent commit is under a
# non-deployable path (.planning/, skills/, docs/, root *.md, .github/, etc.),
# the hook stays silent. Running the 14-phase deploy pipeline for a planning
# or docs commit is wasted CI/CD time and produces a no-op revision on Cloud
# Run + Vercel. Code changes in app/, frontend/src/, supabase/migrations/, or
# top-level config files still trigger ship-it as before.

INPUT=$(cat)

# Match git commit in the raw JSON (tool_input.command contains the bash command)
if echo "$INPUT" | grep -qE '"command".*git commit' && ! echo "$INPUT" | grep -q 'git commit --amend'; then
  # Branch gate: only fire on commits to main. Empty/error => not main => suppress.
  CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
  if [ "$CURRENT_BRANCH" = "main" ]; then
    # Docs-only gate: list files in HEAD commit; suppress if every file matches
    # the docs/planning/tooling allow-list. If git fails, fall through to fire
    # (safer to over-trigger than miss a real code commit).
    CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null)
    if [ -n "$CHANGED_FILES" ]; then
      # Anchored allow-list: anything matching these paths is non-deployable.
      # Code paths (app/, frontend/src/, supabase/migrations/, tests/, root
      # configs like Dockerfile/pyproject.toml/package.json/vercel.json/Makefile)
      # do NOT match this regex and so will fail the all-match check below.
      DOCS_ONLY_REGEX='^(\.planning/|skills/|docs/|README\.md$|CHANGELOG\.md$|LICENSE$|CONTRIBUTING\.md$|\.github/|\.gitignore$|\.gitattributes$|\.editorconfig$)'
      CODE_FILES=$(echo "$CHANGED_FILES" | grep -vE "$DOCS_ONLY_REGEX" || true)
      if [ -z "$CODE_FILES" ]; then
        # All files match the docs-only allow-list -> no deployable surface.
        exit 0
      fi
    fi
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
