# Phase 63 Deferred Items

## Pre-existing issues discovered but NOT fixed (out of scope)

### 63-01
- `app/agents/marketing/agent.py:486` — `RUF013 PEP 484 prohibits implicit Optional` on `output_key: str = None` in `create_marketing_agent`. Same finding as 63-02 entry below; first surfaced during 63-01 ruff check on the modified agent file. Should be fixed as `output_key: str | None = None` in a general cleanup pass.

### 63-02
- `app/agents/marketing/agent.py:490` — `RUF013 PEP 484 prohibits implicit Optional` on `output_key: str = None` in `create_marketing_agent`. Pre-existing in the codebase; not caused by 63-02 edits. Should be fixed as `output_key: str | None = None` in a general cleanup pass.
