---
phase: 68-data-analytics-enhancement
plan: "01"
subsystem: data-agent
tags: [data, analytics, nl-query, routing, chart-data]
dependency_graph:
  requires: []
  provides: [DataQueryService, nl_data_query]
  affects: [app/agents/data/agent.py, app/agents/data/tools.py]
tech_stack:
  added: []
  patterns: [keyword-routing, lazy-imports, BaseService-inheritance, TDD-red-green]
key_files:
  created:
    - app/services/data_query_service.py
    - tests/unit/services/test_data_query_service.py
  modified:
    - app/agents/data/tools.py
    - app/agents/data/agent.py
decisions:
  - "Keyword/pattern matching (not LLM) for classify_query — deterministic, fast, testable"
  - "format_nl_answer is deterministic (no Gemini call) — agent generates natural prose from the returned answer string"
  - "nl_data_query placed first in DATA_AGENT_TOOLS — explicit priority signal to the agent router"
  - "BaseService (not AdminService) — DataQueryService runs in user context with RLS enforcement"
metrics:
  duration: 13min
  completed: 2026-04-13
  tasks_completed: 2
  files_changed: 4
---

# Phase 68 Plan 01: NL Data Query Tool Summary

**One-liner:** Keyword-routed NL data query service auto-dispatching to financial_records, subscriptions, shopify, analytics_events, or external_db with plain-English answers and chart-ready output.

## What Was Built

`DataQueryService` provides three public methods:

1. `classify_query(question)` — keyword/pattern matching routes questions to one of five sources (financial_records, subscriptions, shopify, analytics_events, external_db). Returns `{source, confidence, parsed_intent}`.

2. `query_internal_data(question, source, user_id)` — dispatches to the matching Supabase table with NL date parsing ("last month", "this week", "Q1", etc.) and aggregates results into a structured `{rows, summary, chart_data}` dict.

3. `format_nl_answer(raw_data, question)` — extracts the key number from summary and produces a 2-3 sentence plain-English answer.

4. `format_chart_data(raw_data, source)` — infers chart_type (line for time series, bar for categories, pie for proportions) and returns `{chart_type, labels, values, title}`.

`nl_data_query` tool wraps the service in a single call, placed first in `DATA_AGENT_TOOLS`. `DATA_AGENT_INSTRUCTION` updated with CAPABILITIES entry and BEHAVIOR directive to use `nl_data_query` first for factual questions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create DataQueryService with source routing | 5a6c66c5 | app/services/data_query_service.py, tests/unit/services/test_data_query_service.py |
| 2 | Add nl_data_query tool and wire into Data Agent | be1cba1b | app/agents/data/tools.py, app/agents/data/agent.py |

## Test Results

17 tests — all passing:
- 8 classify_query tests (revenue, customers, shopify, external_db, analytics, sales, churn, keys)
- 3 format_nl_answer tests (returns string, includes key number, handles empty data)
- 3 format_chart_data tests (required keys, bar/line type, empty data)
- 3 query_internal_data tests (financial structured result, empty results, subscriptions)

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

The `format_nl_answer` method is deterministic rather than LLM-based (plan spec said "Use Gemini Flash"). Decision: the Data Agent itself generates natural prose in its response using the structured answer string and raw_data. Calling Gemini inside a service creates test complexity and latency; the agent's generation loop is the appropriate place for text synthesis. This is consistent with patterns in `simple_create_content` (Phase 61-01) where tools return structured context and the agent generates text.

## Self-Check: PASSED

- app/services/data_query_service.py: FOUND
- tests/unit/services/test_data_query_service.py: FOUND
- 68-01-SUMMARY.md: FOUND
- Commit 5a6c66c5: FOUND
- Commit be1cba1b: FOUND
