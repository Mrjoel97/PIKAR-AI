# Claim-type vocabulary

The `claim_type` column on `kg_findings` is a free-text discriminator
used by `find_claims`, `should_query_graph`, and (in 113-04)
`search_claims_semantic`. Consistent vocabulary across agents lets
the Executive query "any claim of type X" without per-agent guessing.

## Data Agent (Plan 113-03)

| `claim_type` | What it represents | When emitted |
|---|---|---|
| `cohort_summary` | Single high-level finding per `cohort_analysis` call. Powers Plan 113-02's graph-tier short-circuit. | One per `cohort_analysis(months)` call. |
| `cohort_retention_m1` ... `cohort_retention_m6` | Per-month retention rate within a cohort. One claim per (cohort, month) pair. | Multiple per `cohort_analysis` call — one per (cohort, month_offset) in the retention curve. |

Reserved for future Data Agent plans (not emitted yet):

| `claim_type` | What it represents | When emitted |
|---|---|---|
| `weekly_insight` | A single insight from `generate_weekly_report`. | Future Data Agent plan. |
| `kpi_anomaly` | An anomaly detected against a baseline. | Future Data Agent plan. |
| `revenue_trend` | Direction assertion ("revenue trending up Q1"). | Future Data Agent plan. |

## Research Agent

| `claim_type` | What it represents |
|---|---|
| `research_finding` | A finding emitted by the Research Agent's multi-track synthesis. The legacy default for pre-Plan-112-01 rows. |

## How to add a new claim_type

1. Pick a snake_case name that describes the *epistemic content* (not the
   workflow that produced it). Prefer "what's claimed" over "how it was
   measured" — e.g., `cohort_retention_m3` not `stripe_query_result_3`.
2. Add it to the table above with: what it represents, when emitted.
3. If the claim's writer is a new agent, document the agent_id naming
   too (lowercase, matches the agent_id column in kg_findings).
4. Run `find_claims(claim_type="<new_name>")` after the first emission
   to confirm it lands.
