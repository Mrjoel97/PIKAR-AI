# Deferred Items - Phase 104

## Out-of-Scope Discoveries (Logged, NOT Fixed)

### app/social/connector.py corrupted with null bytes (2026-05-09)

**Discovered during:** Plan 104-02 regression run (`pytest tests/unit/test_social_connector_security.py`).

**Symptom:**
```
SyntaxError: source code string cannot contain null bytes
```

**Diagnosis:**
- `app/social/connector.py` has 36,076 null bytes out of 72,154 total bytes (50% nulled).
- `git diff` reports it as a binary file diff against the parent commit.
- `app/social/publisher.py` (this plan's target) has 0 null bytes — clean.

**Owner:** Plan 107-02 (Facebook Page token in connector.py callback) is running concurrently and is the documented owner of changes to `app/social/connector.py`. The prompt for Plan 104-02 explicitly told this executor: "DO NOT touch app/social/connector.py PLATFORM_CONFIGS or callback logic".

**Action:** NOT fixed by Plan 104-02 — out of scope. The 107-02 executor must restore `app/social/connector.py` from `HEAD` (or re-author its edits with UTF-8 encoding) before its work can land.

**Impact on 104-02:** None for the unit tests under `tests/unit/test_twitter_publisher.py` (those passed 9/9). The regression sweep `pytest tests/unit -x --ignore=tests/unit/admin` cannot run cleanly until 107-02 fixes connector.py — the import chain `app/social/__init__.py → app/social/analytics.py → app/social/connector.py` blocks collection of any test that imports from `app.social`.
