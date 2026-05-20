# Self-Improvement Autonomy Policy

This document defines what the Pikar-AI self-improvement engine is allowed to
modify autonomously, what stays behind human approval, and the invariants
that govern both. It is normative — anything not listed here is **out of
scope** for autonomous change. Future plans that propose to widen this scope
must update this document explicitly.

## 1. What the engine MAY auto-modify

| Surface | Mechanism | Required gate |
|---|---|---|
| `skill_versions` knowledge content | Refinement via A/B harness | `skill_experiments` z-test produces a significant lift AND `(p_treatment − p_control) ≥ min_effect_size` |
| `skill_versions.is_active` flag (promote/revert) | A/B harness decision | Same as above; revert fires on any significant regression |
| `custom_skills.is_active` flag (demote) | `_execute_skill_demoted` | `auto_execute_risk_tiers` includes `skill_demoted` |
| `skill_scores`, `improvement_actions`, `workflow_template_scores` rows (analytics writes) | Engine cron | Always — these are observational |

Workflow template **scoring** is in scope (Pillar 2). Workflow template
**refinement** is explicitly out of scope until an A/B harness analogous to
the skill harness ships.

## 2. What the engine MUST NOT auto-modify

The following surfaces are the system's trust anchor. The engine and any
service it calls must never write to them autonomously:

- **Agent Python code** — `app/agents/**/*.py`, `app/agent.py`
- **Agent instruction strings** — `app/agents/shared_instructions.py`,
  `app/agents/*/instructions.py`, any `INSTRUCTIONS` module-level constant
- **Model + routing config** — `app/agents/shared.py`
  (`get_routing_model`, `get_fallback_model`, retry/backoff parameters)
- **Tool registration** — the `EXEC_*_TOOLS` lists and the registry that
  exposes tools to the runtime
- **Database schema** — `supabase/migrations/`
- **Orchestration kernel** — `app/workflows/engine.py`,
  `app/workflows/step_executor.py`, the workflow runtime
- **Self-improvement settings themselves** — `auto_execute_enabled`,
  `auto_execute_risk_tiers`. Flipping the autonomy switches is a human
  action only.

If the engine ever appears to be writing to one of these surfaces, treat it
as an incident, not a feature.

## 3. Approval gates today

Action types in `improvement_actions.action_type` and their default
treatment:

| Action type | Default | Reason |
|---|---|---|
| `skill_refined` | Auto-creates an A/B experiment | The harness gates promotion behind statistical evidence |
| `skill_promoted` | Auto-issued by evaluator on significant lift | Backed by z-test + min_effect_size |
| `skill_demoted` | Auto-executable when in `auto_execute_risk_tiers` | Reversible by re-promoting; no production risk |
| `pattern_extract` | Auto-executable when in `auto_execute_risk_tiers` | Pure analysis, no state mutation outside `improvement_actions` |
| `skill_created` | Human approval | No control variant — cannot A/B a brand-new skill |
| `skill_merged` | Human approval | Affects skill identity / routing assumptions |
| `instruction_updated` | Human approval | Would mutate agent instructions; see §2 |
| `gap_identified` | No mutation (analysis only) | Surfaces gaps to humans; resolution is a separate action |
| `investigate` | No mutation (analysis only) | Triggers human review of a declining trend |

`auto_execute_enabled` controls whether even the "auto-executable" tiers
run automatically. Default `False` — flip to `True` only after the A/B
harness has demonstrated stable promote/revert decisions on real traffic.

## 4. Rollback contract

Every auto-modification the engine performs MUST be:

1. **Traceable**: written through `improvement_actions` with
   `source_action_id` linking to the originating decision, AND through
   `governance_audit_log` with an `action_type` prefixed
   `self_improvement.`.
2. **Reversible in one statement**:
   - For promotes: flip `is_active` on `skill_versions` back to the
     `previous_version_id` row.
   - For experiment reverts: the candidate row already has
     `metadata.reverted = true` and `is_active = false`; no further action
     needed.
   - For demotes: `UPDATE custom_skills SET is_active = true WHERE id = $`.
3. **Visible**: dashboards must show the change with timestamps, actor
   (`system:self-improvement-engine`), and decision rationale before any
   admin is expected to trust it.

When an auto-decision goes wrong, the recovery path is a human flipping
`is_active` (or running the rollback statement above) — not a re-run of
the engine.

## 5. The eval-before-autonomy invariant

The engine MUST NOT promote any change to a live skill without a
statistically significant z-test on real interactions collected during a
running `skill_experiments` row. Specifically:

- Promotion requires `z > +1.96` AND `(p_treatment − p_control) ≥ min_effect_size`.
- Revert fires on any `z < −1.96`, regardless of effect size (asymmetric
  by design — we want fast rollback on harm but conservative promotion
  on lift).
- When an experiment cannot collect enough samples within
  `max_duration_days`, the default action is **revert**, not promote. The
  "do nothing" branch only exists between the deadline and the sample
  budget — once either is exhausted, we always fall back to the control
  version.

## 6. Reading this document in code

The constants in `app/services/skill_experiment_evaluator.py` and
`app/services/self_improvement_engine.py` are the source of truth for the
exact thresholds. Per-experiment overrides on the `skill_experiments` row
take precedence over module defaults — but no override can disable a
threshold entirely (a `min_effect_size` of 0 is treated as 0, not as
"promote on any lift").

The boundary in §2 is enforced socially, not technically. If you are a
future engineer or future Claude reading this, treat any PR that
broadens §1 without a parallel broadening of §4 and §5 as suspect.
