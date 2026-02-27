# Workflow Defect Register

Last Updated: 2026-02-19
Owner: Platform Engineering

| ID | Severity | Status | Summary | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| WF-001 | P2 | closed | Initial readiness-gate regression during HTTP error serialization | Platform | Fixed in `app/fast_api_app.py` detail serialization |

## Policy
- Open `P0` or `P1` defects block canary/wave promotion.
- Verification command: `uv run python scripts/verify/verify_no_blocking_workflow_defects.py`
