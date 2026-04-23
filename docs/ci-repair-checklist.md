# Main CI Repair Checklist

Repair branch: `codex/fix-main-ci-and-repo-hygiene`

## Preserved Dirty Work

- [x] Saved nested `antigravity-awesome-skills` dirty state to stash: `codex/save-antigravity-dirty-before-ci-repair-2026-04-23`
- [x] Saved root repo dirty state to stash: `codex/save-root-dirty-before-ci-repair-2026-04-23`
- [x] Confirmed the repair branch started from clean `main`

## Local CI Gates

- [x] Remove duplicate Supabase migration prefixes while preserving one valid migration per logical change
- [x] Update frontend auth/persona contract test mock for `getAccessToken()`
- [x] Add admin app production build to CI coverage
- [x] Run migration integrity verifier
- [x] Run workflow template verifier
- [x] Run journey workflow reference verifier
- [x] Run backend trust tests
- [x] Run frontend auth/persona contract test
- [x] Run frontend production build
- [x] Run admin production build

## GitHub Actions

- [x] Confirm current GitHub Actions failures happen before checkout with `runner_id=0` and no recorded steps
- [x] Confirm the latest run reports: "The job was not started because your account is locked due to a billing issue."
- [ ] Resolve the GitHub account billing lock
- [ ] Re-check latest GitHub Actions run after local fixes are pushed
- [ ] If jobs still fail before checkout with `runner_id=0`, fix repository/account Actions settings with admin access

## Merge Readiness

- [x] Confirm `git status` only contains intentional repair changes
- [x] Commit repair changes on the branch
- [ ] Push branch and open/merge after CI is genuinely green
