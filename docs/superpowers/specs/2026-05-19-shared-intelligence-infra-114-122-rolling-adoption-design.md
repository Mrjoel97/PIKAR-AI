# Shared Intelligence Infrastructure — Rolling Adoption Design (Phases 114–122)

**Date:** 2026-05-19
**Status:** Draft for review
**Phases:** 114–122 (9 specialized agents adopt shared intelligence)
**Predecessor:** `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md` (Phase 112 modules + Research migration; Phase 113 Data Agent pilot)

## Summary

Roll the Phase 112 shared intelligence infrastructure (confidence presets, `kg_findings` claims, two-tier adaptive cache) into every remaining specialized agent. One phase per agent, sequential, committed in `MILESTONES.md`. No agent is excluded. Each phase carries only the sub-plans the agent actually needs (adaptive template, not uniform). Cross-cutting infrastructure from Phase 113 (`search_claims_semantic`, `detect_contradictions`) auto-applies to every new claim emitted.

## Motivation

After Phase 113 (Data Agent adoption), 9 specialized agents still emit confident-sounding text with no calibration and refetch external data on every call: Financial, Sales, Compliance, Marketing, HR, Customer Support, Operations, Strategic, Content. The original Phase 112/113 spec said these would adopt "in later phases, prioritized by user value." This design picks up that commitment and converts it to a concrete, fully-committed rollout: every agent has a phase, ordered by adoption fit and dependency, with claim taxonomies tailored to each agent's actual output shape rather than forced into the analytical-claim pattern from Phase 113.

## Decisions

These were settled during brainstorming on 2026-05-19. Each meaningfully constrains the rollout.

| # | Decision | Alternative considered | Why |
|---|---|---|---|
| 1 | **No agent excluded** — all 9 remaining specialized agents adopt | Exclude orchestrators (Operations, Strategic) + Content (creative) as poor fits | Every agent can emit claims; the *taxonomy* differs. The Phase 112 schema is generic enough to absorb operational, decision, and meta-fidelity claims. |
| 2 | **Rolling adoption — one phase per agent (114–122)** | Big-bang single-phase covering all 6+; bundle light agents | Honors "every agent should be sharp, no discriminating" while preserving Phase 112's pilot-first risk-containment principle (each phase still ships independently). |
| 3 | **Adaptive sub-plan template** — each phase carries only the plans the agent needs (2–4 plans, not a fixed 3) | Uniform 3-plan template per phase | Some agents (HR, CS, Compliance) have no external cache surface — a uniform template would generate hollow "cache integration" plans. Adaptive avoids ceremony. |
| 4 | **Phase order: adoption fit first, novel claim model last** | Alphabetical; risk-pacing (hardest first) | Easiest-first means abstraction polish compounds before tackling the harder agents (Strategic depends on others; Content has the most novel claim shape). |
| 5 | **Strategic depends on prior phases** — runs as Phase 121, not earlier | Run Strategic immediately after Phase 113 | Strategic's most valuable claim type (`cross_domain_risk_consolidation`) synthesizes risks across other agents' findings. Without their claims in the graph, the consolidation is empty. |
| 6 | **Content runs last (Phase 122)** | Run Content earlier as part of the "easy" tier | Content's claim model (`brand_fidelity_score`, `asset_origin_claim`) is the most novel — battle-test the abstraction first. Bonus: its idempotent-render cache is the largest cost-saving surface, worth getting right. |
| 7 | **Roadmap commit in the design doc itself** | Trivial "114-00" sub-plan to edit MILESTONES.md | Committing the roadmap is meta-planning, not a code task. Bundle with this design doc commit. |
| 8 | **Each phase's *first* sub-plan audits self-improvement engine entanglement** | Audit only at end of phase; per-phase ad-hoc audit | `app/services/self_improvement_engine.py` and `skill_experiment_evaluator.py` bind to current agent shapes. Per Phase 112 risk register, audit must happen *before* changes so we know what shapes the engine depends on — not after, when entanglement is already broken. Make it a structural requirement, not optional hygiene. |

## Phase order and structure

| Phase | Agent | Sub-plans | Claim taxonomy theme | Effort |
|---|---|---|---|---|
| 114 | Financial | 3 (preset + Stripe/Shopify cache + claims) | Analytical (`revenue_trend`, `margin_signal`, `revenue_forecast_h{N}m`) | 2–3w |
| 115 | Sales | 3 (preset + HubSpot cache + claims) | Quantitative (`lead_score`, `deal_stage_signal`, `pipeline_health`) | 2–3w |
| 116 | Compliance | 2 (preset + claims) | Categorical (`risk_assessment`, `audit_finding`) | 1–2w |
| 117 | Marketing | 4 (preset + multi-platform cache + claims + regression guardrails) | Performance (`campaign_lift`, `audience_resonance`) | 3–4w |
| 118 | HR | 2 (preset + claims) | Operational (`candidate_signal`, `hiring_pipeline_state`) | 1–2w |
| 119 | Customer Support | 2 (preset + claims) | Signal (`ticket_sentiment`, `csat_signal`, `churn_risk_indicator`) | 1–2w |
| 120 | Operations | 3 (preset + OpenAPI/health cache + claims) | Outcome (`integration_health_verified`, `workflow_execution_completed`, `sop_generation_completed`) | 2–3w |
| 121 | Strategic | 2 (preset + edges-heavy claims) | Synthesized (`initiative_milestone`, `cross_domain_risk_consolidation`, `priority_assessment`) | 2w |
| 122 | Content | 3 (preset + idempotent render cache + claims) | Meta (`brand_fidelity_score`, `asset_origin_claim`, `content_performance_trend`) | 3–4w |

Total: 9 phases, ~24 sub-plans, ~4–6 months rolling.

## Per-phase summaries

### Phase 114 — Financial Agent adoption (detailed)

**Promise:** Financial Agent uses shared intelligence. Every Financial output carries `confidence` + `band`. Stripe/Shopify call rate reduced ≥40% on repeated load. Cross-agent semantic search returns Financial claims alongside Data/Research claims.

**Plans:**

| Plan | Subject |
|---|---|
| 114-01 | `presets/financial.py` + Financial Agent statistical wiring + self-improvement engine audit |
| 114-02 | Two-tier cache integration around Stripe/Shopify external calls |
| 114-03 | Financial claim emission rules + claim-type vocabulary |

**Confidence preset (`financial_confidence`):**

```python
FINANCIAL_WEIGHTS = {
    "data_completeness":     0.30,  # how much of the period's source rows landed
    "reconciliation_signal": 0.30,  # accounting identity holds (e.g., balance sheet balances)
    "horizon_certainty":     0.25,  # historical vs near-future vs long-range forecast
    "source_authority":      0.15,  # Stripe/Plaid > manual entry > scraped
}
```

`horizon_certainty` is the novel input — Financial's existing instructions already flag low-confidence forecasts qualitatively. The preset formalizes that by binding confidence to forecast horizon length.

**Claim-type vocabulary:**

| Output type | Becomes a Claim? | Storage |
|---|---|---|
| Period revenue total | No (transient) | Redis only (5-min TTL) |
| Revenue trend assertion | Yes | `kg_findings`, claim_type=`revenue_trend` |
| Expense category insight | Yes | claim_type=`expense_pattern` |
| Forecast (per horizon) | Yes, one per horizon | claim_type=`revenue_forecast_h{N}m`, `expires_at = now + N months` |
| Margin signal | Yes | claim_type=`margin_signal` |
| Anomaly detection | Yes | claim_type=`financial_anomaly` |
| Reconciliation result (material only) | Yes if material | claim_type=`reconciliation_finding` |
| Ad-hoc SQL/aggregation answer | No | Response payload only |

**Cache integration:**

| External call | Tier | TTL | Cache key shape |
|---|---|---|---|
| Stripe revenue summary | Redis | 300s | `stripe:revenue_summary:{period}` |
| Stripe disputes/chargebacks | Redis | 600s | `stripe:disputes:{period}` |
| Shopify order summary | Redis | 300s | `shopify:orders:{period}:{shop}` |
| Financial claims | Graph | 24h freshness | `claim_freshness_hours(entity_id, claim_type)` |

**Acceptance criteria:**

- Financial Agent test suite green
- All Financial outputs carry `confidence` + `band` (no hardcoded constants)
- Stripe call rate reduced ≥40% on synthetic load test vs pre-114 baseline
- Graph-tier hit rate ≥60% on repeated `revenue_trend` queries within 24h
- `search_claims_semantic(query="Q1 revenue", top_k=10)` returns Financial + Data + Research claims interleaved
- No regression in `/admin/financial/overview` dashboard

### Phase 115 — Sales Agent adoption

**Plans:** 115-01 (preset + lead-score statistical wiring) · 115-02 (HubSpot cache) · 115-03 (claim emission + lead-score-as-claim with `contradicts=[old_lead_score_id]` pattern for updates) · self-improvement audit folded into 115-01.

**Preset (`sales_confidence`):** `lead_criteria_completeness` (0.30) · `crm_authority` (0.25) · `recency` (0.25) · `signal_consistency` (0.20). LeadQualification schema already exists; preset just formalizes credibility.

**Notable claim types:** `lead_score`, `deal_stage_signal`, `pipeline_health`. Lead scores update via new claim + `contradicts=[old]` — never accumulate history per-lead.

### Phase 116 — Compliance Agent adoption

**Plans:** 116-01 (preset, RiskAssessment integration, audit) · 116-02 (claim emission).

**Preset (`compliance_confidence`):** `regulation_authority` (0.40) · `evidence_traceability` (0.30) · `recency_vs_regulation_version` (0.20) · `peer_review_signal` (0.10).

**Claims:** `risk_assessment`, `audit_finding`. Audit findings reference risk_assessment claims via edges; new assessments create new claim_id rather than mutating prior.

### Phase 117 — Marketing Agent adoption

**Plans:** 117-01 (preset + audit) · 117-02 (Google Ads/Meta Ads/Shopify/social analytics cache) · 117-03 (claim emission) · **117-04 (regression guardrails)** — the only phase with a dedicated regression-prevention plan because Marketing has the most active downstream workflows.

**Preset (`marketing_confidence`):** `attribution_completeness` (0.35) · `statistical_significance` (0.30) · `audience_coverage` (0.20) · `recency` (0.15).

**Claims:** `campaign_lift`, `audience_resonance`, `creative_performance` (cross-references Content's `brand_fidelity_score` when both phases shipped). Campaign-level claims carry `expires_at = campaign_end_date + 30d`.

### Phase 118 — HR Agent adoption

**Plans:** 118-01 (preset + schema design) · 118-02 (claim emission).

**Preset (`hr_confidence`):** `candidate_data_completeness` (0.35) · `interviewer_consensus` (0.30) · `recency` (0.20) · `assessment_battery_coverage` (0.15).

**Claims:** `candidate_signal`, `hiring_pipeline_state`. Candidate signals expire at offer-accept or rejection; before that, `freshness_at` updates on each interaction.

### Phase 119 — Customer Support Agent adoption

**Plans:** 119-01 (preset + schema) · 119-02 (claim emission).

**Preset (`customer_support_confidence`):** `ticket_volume_signal` (0.30) · `customer_response_engagement` (0.25) · `resolution_outcome_clarity` (0.25) · `recency` (0.20).

**Claims:** `ticket_sentiment`, `csat_signal`, `churn_risk_indicator`. Churn-risk claims TTL = 7d (must be refreshed weekly).

### Phase 120 — Operations Agent adoption

**Plans:** 120-01 (preset + audit) · 120-02 (OpenAPI spec + integration-health cache) · 120-03 (claim emission).

**Preset (`operations_confidence`):** `integration_verification_signal` (0.40) · `audit_trail_completeness` (0.35) · `execution_idempotency` (0.20) · `test_coverage_signal` (0.05).

**Claims:** `integration_health_verified` (TTL 24h), `workflow_execution_completed`, `api_connector_setup_validated`, `configuration_audit_passed`, `sop_generation_completed`.

**Cache:** OpenAPI spec parses (TTL 24h), integration health checks (TTL 5min), endpoint metadata (TTL 7d).

### Phase 121 — Strategic Agent adoption

**Plans:** 121-01 (preset + edges architecture) · 121-02 (claim emission + cross-domain synthesis).

**Preset (`strategic_confidence`):** `sub_agent_consensus` (0.40) · `evidence_breadth` (0.30) · `recency_of_input` (0.20) · `stakeholder_validation_signal` (0.10).

**Claims:** `initiative_milestone`, `strategic_decision`, `priority_assessment`, `cross_domain_risk_consolidation`, `journey_workflow_readiness`. Strategic writes mostly via `edges` referencing prior-agent claims, not as new claim text. This is what makes Phase 121's order-dependency real: Strategic without prior agents emitting claims has nothing to consolidate.

### Phase 122 — Content Agent adoption

**Plans:** 122-01 (preset + brand-profile embedding audit) · 122-02 (idempotent render cache) · 122-03 (claim emission, per-sub-agent claim types).

**Preset (`content_confidence`):** `brand_alignment_score` (0.30) · `performance_sample_size` (0.25) · `recency` (0.20) · `statistical_significance` (0.15) · `engagement_lift_magnitude` (0.10).

Per-claim-type overrides:
- `asset_origin_claim` → confidence = 1.0 (deterministic provenance)
- `brand_fidelity_score` → use brand_alignment_score weight only
- `seo_performance_cohort` → recency dominates (0.40)
- `hook_performance_comparative` → require sample_size ≥ 15/variant; below, cap at 0.65

**Claims:** Per sub-agent — Video (`video_completion_rate_signal`, `hook_performance_comparative`, `asset_origin_claim`), Graphic (`brand_fidelity_score`, `design_audience_resonance`, `asset_generation_provenance`), Copy (`seo_performance_cohort`, `copy_tone_fidelity`, `content_repurpose_lift`).

**Cache (largest cost-saving surface):** Canva/Veo idempotent render — `render_cache_key = sha256(template_id + brand_profile_version + prompt_text + style_preset + dimensions)`. Cache TTL 30 days. Saves ~$0.08-0.12 per cached design + per Veo render.

**Pre-requisite check during 122-01:** Brand-profile embedding infrastructure must exist. If not, a Phase 121.5 ships it before 122 can land.

## Testing strategy (delta from Phase 112/113)

Phase 112's testing pattern carries forward. Each phase adds:

| Test type | Per-phase scope |
|---|---|
| Unit (preset) | Property-based: `agent_confidence(...)` clamped [0.0, 1.0]; weights sum ≤ 1.0; invalid inputs raise |
| Unit (claim emission) | Mock external calls; verify which output paths produce claims vs. stay in Redis |
| Integration | `write_claim` → `find_claims` round-trip per claim_type; Supabase-down + embedding-failure error paths |
| Regression | Agent's existing test suite green; ADK tool registry unchanged |
| Load (cache phases only) | External call rate reduced ≥40% on synthetic burst |
| Cross-agent (Strategic Phase 121) | `cross_domain_risk_consolidation` claim references ≥3 distinct prior-agent claims via edges |

Plan 113-04/05 cross-cutting infrastructure (semantic search, contradiction detection) auto-applies to every new claim — no per-phase test work needed for those.

## Observability (delta)

Phase 112 metrics generalize. New tag values:

| Metric | New tag values |
|---|---|
| `intelligence.claims.written` | `agent_id` ∈ {financial, sales, compliance, marketing, hr, customer_support, operations, strategic, content} |
| `intelligence.cache.decision` | New `tier=external` cache_key prefixes per agent (`hubspot:*`, `canva_render:*`, etc.) |
| `intelligence.contradictions.detected` | Cross-agent pairs become meaningful at Phase 121 (Strategic) onwards |
| `intelligence.confidence.computed` | `preset_name` ∈ {financial, sales, compliance, marketing, hr, customer_support, operations, strategic, content} |

`/admin/research/overview` extends to show all-agent claim counts after Phase 114; one new bar per agent as they come online.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Abstraction debt accumulates by Phase 119 | Medium | High | Phases 116/118/119 are simple (preset+claims only) — they exercise the spine. If it creaks there, fix before tackling 120/122. |
| Cross-agent claim collisions (semantic-equivalent claim_types) | Medium | Medium | Each phase publishes claim_type vocabulary at design time; spec-level review catches overlap (e.g., Sales `pipeline_health` vs Operations `workflow_execution_completed`). |
| Strategic Phase 121 blocked by missing prior-agent claims | Medium | Medium | Phase order enforces prior-agent prerequisites; verified by Phase 121 acceptance criterion (must reference ≥3 distinct agents). |
| Content `brand_fidelity_score` needs brand-profile embedding infrastructure not yet built | Medium | Medium | Audit during Phase 122-01; if missing, ship Phase 121.5 before 122 lands. |
| 6-month rolling commitment slips | High | Low | Each phase is independently shippable; slippage delays *finish* but not *value* of phases already shipped. |
| Self-improvement engine entangles with old per-agent code paths | Medium | High | Each phase's first sub-plan audits `app/services/self_improvement_engine.py` + `skill_experiment_evaluator.py` per `docs/self-improvement-policy.md`. |
| Vertex billing block re-emerges and breaks embedding-dependent claim emission | Medium | High | Inherited from Plan 113-05 post-migration revalidation memory; new Cloud Run project migration spec is on the path. |
| User priority shifts mid-rollout (e.g., business needs Sales results before Compliance) | Medium | Low | Roadmap is committed in MILESTONES.md but phases are independent — reordering doesn't cost much beyond updating MILESTONES.md. |

## Out of scope

- Per-agent UI/UX changes (dashboards extend automatically via `/admin/research/overview`)
- Multi-track decomposition for any agent (research-specific, not generalized)
- Persona-aware formatting per agent (deferred from Phase 112, still deferred)
- ADK tool wrappers for individual claim emission per agent (Phase 112 decision: library-first)
- Consolidating `graph_service.py` / `intelligence_scheduler.py` / `intelligence_worker.py` into the new package (separate cleanup phase)
- Per-agent budget tracking analogous to `kg_domain_budgets` (only Research has metered external calls)
- Cross-Cloud-Run-project migration (separate spec at `docs/superpowers/specs/2026-05-19-cloud-run-new-project-migration-design.md`)
- Brand-profile embedding infrastructure for Phase 122 *unless* the audit during Phase 122-01 finds it missing (then Phase 121.5)
- Weights calibration tooling for any preset (each preset ships with educated-guess weights; calibration from telemetry is a separate phase once labeled data exists)

## MILESTONES.md update

This design's commit also updates `MILESTONES.md` with the 114–122 rolling commitment so the roadmap is binding:

```markdown
- Phase 114: Financial Agent adoption (shared intelligence) — 2–3 weeks
- Phase 115: Sales Agent adoption — 2–3 weeks
- Phase 116: Compliance Agent adoption — 1–2 weeks
- Phase 117: Marketing Agent adoption — 3–4 weeks
- Phase 118: HR Agent adoption — 1–2 weeks
- Phase 119: Customer Support Agent adoption — 1–2 weeks
- Phase 120: Operations Agent adoption — 2–3 weeks
- Phase 121: Strategic Agent adoption — 2 weeks
- Phase 122: Content Agent adoption — 3–4 weeks
```

## References

- Predecessor design: `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md` (Phase 112 modules + Phase 113 Data adoption)
- Shared infrastructure package: `app/services/intelligence/`
- Knowledge-graph schema migration: `supabase/migrations/20260518000000_broaden_kg_findings_for_shared_claims.sql`
- pgvector ivfflat index: `supabase/migrations/20260519000000_kg_findings_embedding_ivfflat_index.sql`
- Self-improvement policy (load-bearing for per-phase audits): `docs/self-improvement-policy.md`
- Vertex billing context: memory `project_phase_113_05_post_migration_revalidation`, `project_agent_operating_model_w1`
- Cloud Run new-project migration: `docs/superpowers/specs/2026-05-19-cloud-run-new-project-migration-design.md`
