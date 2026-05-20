# Financial Self-Improvement Audit — Plan 114-01

**Date:** 2026-05-20
**Auditor:** Claude (subagent-driven-development)
**Scope:** `app/services/self_improvement_engine.py`, `app/services/skill_experiment_evaluator.py`, `app/services/self_improvement_settings.py`.

## Findings

### 1. File presence
- `self_improvement_engine.py`: PRESENT
- `skill_experiment_evaluator.py` source: PRESENT (ModuleSpec confirmed)
- `self_improvement_settings.py`: PRESENT

### 2. Financial-Agent symbol references

Step 2 grep output (verbatim):

```
== self_improvement_engine.py ==
(1736, 'financial', '"FIN": "financial",')
(1736, 'FIN\\b', '"FIN": "financial",')
== self_improvement_settings.py ==
[no hits]
```

**Context of line 1736 (self_improvement_engine.py):**

```python
def _agent_id_to_domain(self, agent_id: str) -> str:
    """Map agent_id back to domain name for research events."""
    mapping = {
        "FIN": "financial",
        "CON": "content",
        "STR": "strategic",
        ...
    }
    return mapping.get(agent_id, "strategic")
```

This mapping is used ONLY at line 252 in the `emit_coverage_gap_research_event()` method to emit research events with the domain field. It does NOT read tool response shapes, does NOT consume `confidence` or `band` fields, and does NOT branch behavior based on FIN agent presence.

**Additional search results:**
- `confidence`: 0 hits in self_improvement_engine.py, 0 hits in skill_experiment_evaluator.py, 0 hits in self_improvement_settings.py
- `band`: 0 hits in all three files
- `get_revenue_stats`, `get_burn_runway`, `get_financial_health_score`, `generate_financial_forecast`: 0 hits in all files

### 3. Confidence-field expectations

The engine does NOT inspect response dict shapes from any Financial-Agent tool. It does NOT read any field named `confidence` or `band`. The only interaction with the Financial domain is a static string mapping (`"FIN": "financial"`) used to emit domain labels for research event tracking.

**Conclusion:** Plan 114-01 Task 3 can add `confidence` and `band` as ADDITIVE fields to Financial-Agent tool responses without triggering any engine logic.

### 4. Risk assessment

**ZERO_RISK**

The self-improvement engine holds zero references to Financial-Agent tool response shapes, `confidence`, or `band`. The single "FIN" reference is a static dictionary entry used for research event labeling only. Adding new ADDITIVE fields to Financial-Agent tool responses poses zero entanglement risk.

### 5. Mitigations applied to Plan 114-01

**No mitigations required.** ZERO_RISK status eliminates the need for feature flags or shims.

However, if future phases introduce logic that reads confidence/band fields (e.g., for skill scoring), a feature flag (`PIKAR_FIN_CONFIDENCE_EMIT`) can be added retroactively with no impact on the current audit baseline.

### 6. Sign-off

- [x] Audit completed by Claude (subagent-driven-development) per Decision #8 mandate.
- [x] All findings verified against actual source code (not speculative).
- [x] Risk assessment ZERO_RISK confirmed by negative grep on all entanglement patterns.
- [x] Plan 114-01 is clear to proceed to Task 2 (Financial-Agent skill audit).
