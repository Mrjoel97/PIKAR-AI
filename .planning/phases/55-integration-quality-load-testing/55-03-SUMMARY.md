---
phase: 55-integration-quality-load-testing
plan: "03"
subsystem: canonical-load-harness-threshold-contract
tags: [testing, load-testing, locust, staging, documentation]

requires: [55-02]

provides:
  - `tests/load_test/locustfile.py` is now the canonical Phase 55 load-test harness with explicit request-name and threshold conventions
  - `tests/load_test/report_assertions.py` evaluates Locust `*_stats.csv` artifacts against a machine-checkable pass/fail contract
  - `tests/load_test/README.md` documents the local smoke path, the 100-user staging runbook, artifact outputs, and pool-health observation flow

affects:
  - tests/load_test/locustfile.py
  - tests/load_test/report_assertions.py
  - tests/load_test/README.md
  - tests/load_test/.results/sample.csv

tech-stack:
  added: []
  patterns:
    - "load-test evaluation runs against Locust *_stats.csv artifacts instead of ad hoc manual interpretation"
    - "the canonical harness keeps heavy SSE users as a minority cohort in the default mix rather than an accidental 50/50 split"
    - "staging operators can pair CSV threshold evaluation with optional /health/connections captures for pool-health observation"

requirements-completed: [LOAD-04]

completed: 2026-04-11
---

# Phase 55 Plan 03: Canonical Load Harness & Threshold Contract Summary

Completed the final implementation slice of Phase 55 by turning the existing load-test groundwork into one canonical, staging-ready harness with an explicit pass/fail contract.

## Accomplishments

- Updated `tests/load_test/locustfile.py` so the Phase 55 harness now exposes:
  - canonical request names for chat, quick chat, rapid chat, and health endpoints
  - explicit threshold/documentation constants for the recommended staging run
  - an accurate default user mix where `ChatHeavyUser` is truly a minority cohort instead of being weighted equally with `PikarUser`
  - optional `PIKAR_HOST` support so the harness can be pointed at a target host without repeating the URL in every command
- Added `tests/load_test/report_assertions.py`, a machine-checkable threshold evaluator that:
  - reads a Locust stats CSV or `--csv` prefix
  - verifies chat p95 latency, aggregate failure ratio, aggregate failure count, and required request rows
  - optionally evaluates captured `/health/connections` output for non-`ok` statuses or pool-exhaustion keywords
  - exits non-zero on failure so it can be used in CI or operator workflows
- Rewrote `tests/load_test/README.md` around the canonical `locustfile.py` path, including:
  - local smoke instructions
  - the 100-user staging runbook
  - artifact naming and interpretation
  - explicit pass/fail rules
  - optional pool-health capture instructions
- Added `tests/load_test/.results/sample.csv` so the assertion helper has a stable self-check artifact in-repo

## Verification

- `uv run python tests/load_test/report_assertions.py --help` passed
- `uv run python tests/load_test/report_assertions.py --input tests/load_test/.results/sample.csv --max-p95-ms 3000` passed
- `uv run python -m py_compile tests/load_test/report_assertions.py tests/load_test/locustfile.py` passed
- `cd frontend && .\node_modules\.bin\tsc.cmd --noEmit` passed

## Deviations From Plan

- No new load harness was needed from scratch. The right move was to formalize the richer existing `locustfile.py`, not replace it.
- While canonicalizing the harness, one accuracy issue surfaced: `ChatHeavyUser` was commented as a lower-weight stress cohort but had the same effective class weight as the standard user. Phase 55 now makes that default mix truthful.
- The live 100-user staging run itself is still a manual runtime verification. This plan ships the governed harness and threshold contract, but it does not claim that staging evidence has already been collected.

## Next Phase Readiness

- `55-03` is complete
- Phase 55 implementation is complete inside GSD
- Phase 56 (GDPR & RAG Hardening) is the next roadmap phase
- Manual runtime UAT remains pending for the live 100-user staging load run and pool-health observation

## Self-Check: PASSED

The repo now has one clear staging-ready load-test path, the results can be judged by a repeatable pass/fail script, and the remaining gap is the explicit live staging run rather than missing harness code or missing documentation.
