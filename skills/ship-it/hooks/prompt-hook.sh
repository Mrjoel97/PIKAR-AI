#!/usr/bin/env bash
# Ship-it UserPromptSubmit hook: triggers when user says "commit", "ship it", etc.
# Reads stdin JSON from Claude Code, checks the user's prompt text,
# and injects the ship-it skill as additionalContext if it matches.

INPUT=$(cat)

# Match trigger phrases in the raw JSON (case-insensitive)
if echo "$INPUT" | grep -iqE '(commit changes|ship it|ship-it|deploy everything|push to prod)'; then
  cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "The user wants to ship changes. Read and follow the ship-it CI/CD pipeline in skills/ship-it/SKILL.md. Execute all 14 phases starting with Phase 1: Scan. This pipeline covers: scanning changes, quality gates, Supabase migration validation, committing, PR creation, merging, deploying to Cloud Run + Vercel, and verifying both deployments succeed."
  }
}
EOF
fi
