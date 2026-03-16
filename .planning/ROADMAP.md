# Roadmap: pikar-ai

## Milestones

- ✅ **v1.0 Core Reliability** - Phase 1 (shipped 2026-03-04)
- ✅ **v1.1 Production Readiness** - Phases 2-6 (shipped 2026-03-13, archive: [v1.1 roadmap](milestones/v1.1-ROADMAP.md), [v1.1 requirements](milestones/v1.1-REQUIREMENTS.md))
- 📋 **v2.0 Strategic Nurturing** - Not yet decomposed into phases

## Archived Milestone Detail

<details>
<summary>✅ v1.0 Core Reliability (Phase 1) - SHIPPED 2026-03-04</summary>

### Phase 1: Core Reliability
**Goal**: Workflow execution is deterministic and Redis caching is resilient
**Plans**: 2 plans

Plans:
- [x] 01-01: Standardize workflow execution and argument mapping
- [x] 01-02: Implement Redis circuit breakers for cache lookups

</details>

## Active Planning

- v2.0 Strategic Nurturing has not been broken into phases yet. Run `$gsd-new-milestone` to create the next milestone's requirements and roadmap slice.
- v1.1 closeout used completed phase summaries plus fully checked requirements, but there was no `.planning/v1.1-MILESTONE-AUDIT.md` artifact at archival time.
- Local tooling follow-up from v1.1: run `supabase link` later to clear the lingering `gotrue` and `storage-api` local version mismatch warning.
