# Deferred Items - Phase 63 Marketing Agent Enhancement

Out-of-scope discoveries logged during plan execution. These are NOT fixed
by the current plan because they were not caused by our changes.

## From 63-01 execution

### RUF013 in app/agents/marketing/agent.py line 486

```python
def create_marketing_agent(
    name_suffix: str = "",
    output_key: str = None,   # <-- RUF013: implicit Optional
    persona: str | None = None,
) -> Agent:
```

- **Discovered:** Task 2 ruff run
- **Scope:** Pre-existing signature on `create_marketing_agent`, unrelated to
  CampaignPerformanceSummarizer wiring.
- **Suggested fix:** `output_key: str | None = None`
- **Deferred to:** Next broader ruff cleanup pass or future marketing agent
  plan that touches this signature.
