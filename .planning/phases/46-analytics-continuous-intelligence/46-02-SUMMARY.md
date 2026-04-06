---
phase: 46-analytics-continuous-intelligence
plan: "02"
subsystem: calendar-intelligence
tags: [calendar, freebusy, meeting-context, follow-up, pattern-detection, google-calendar]
dependency_graph:
  requires:
    - app/integrations/google/calendar.py (GoogleCalendarService base)
    - app/agents/tools/calendar_tool.py (existing 4 tools)
    - app/rag/knowledge_vault.py (search_knowledge function)
    - app/services/supabase.py (get_service_client)
  provides:
    - GoogleCalendarService.get_freebusy() and find_free_slots() methods
    - 4 new agent tools: find_free_slots, get_meeting_context, suggest_followup_meeting, detect_calendar_patterns
    - CALENDAR_TOOLS list extended from 4 to 8 functions
  affects:
    - Any agent that imports CALENDAR_TOOLS (sales agent chief-of-staff flows)
tech_stack:
  added: []
  patterns:
    - asyncio.gather for parallel CRM + vault enrichment
    - asyncio.to_thread for sync supabase calls inside async tool
    - lazy imports inside function bodies (avoid circular deps, defer heavy module load)
    - "majority-raw-title" heuristic for false-positive-proof pattern detection
key_files:
  created:
    - tests/unit/test_calendar_tools.py
  modified:
    - app/integrations/google/calendar.py
    - app/agents/tools/calendar_tool.py
decisions:
  - "search_knowledge module-level function used instead of KnowledgeVault class (class does not exist in the RAG module)"
  - "Pattern detection requires dominant raw title to account for >50% of occurrences — prevents false positives when different-numbered events normalise to same key"
  - "find_free_slots slots capped at 10; business hours 09:00-18:00 UTC; external attendee caveat in every response"
  - "suggest_followup_meeting never calls create_event — preference for morning slots (before noon UTC)"
metrics:
  duration: 14min
  completed_date: "2026-04-05"
  tasks_completed: 1
  files_changed: 3
---

# Phase 46 Plan 02: Calendar Intelligence Summary

Calendar intelligence tools — free/busy slot finding, meeting prep context (CRM + knowledge vault), follow-up suggestions (never auto-books), and recurring pattern detection.

## What Was Built

Extended `GoogleCalendarService` with two new service methods and added 4 new agent tools, bringing `CALENDAR_TOOLS` from 4 to 8 functions.

### GoogleCalendarService extensions (`app/integrations/google/calendar.py`)

- `get_freebusy(start, end, calendar_ids)` — calls `freebusy().query()` API, returns dict keyed by calendar_id with busy interval lists. Defaults to `["primary"]`.
- `find_free_slots(start, end, duration_minutes, calendar_ids)` — merges busy intervals, walks each day restricted to business hours (09:00-18:00 UTC), returns up to 10 available slots with ISO start/end and duration.

### New agent tools (`app/agents/tools/calendar_tool.py`)

- `find_free_slots` — calls service method for a date range, always includes "YOUR calendar only" caveat note about external attendees.
- `get_meeting_context` (async) — fetches upcoming events within `hours_ahead`, enriches each with CRM contacts (Supabase `contacts` table via `asyncio.to_thread`), open action items (`tasks` table), and knowledge vault snippets (`search_knowledge`). Uses `asyncio.gather` for parallel enrichment per event.
- `suggest_followup_meeting` — finds free slots, prefers morning (before noon UTC), returns suggestion dict with `proposed_time`, `title`, `attendees`. Never calls `create_event`.
- `detect_calendar_patterns` — groups events by normalised title (strips date tokens and standalone numbers), requires 3+ occurrences and dominant raw title >50% of group to avoid false positives, infers weekly/biweekly/monthly from median gap between events.

### Tests (`tests/unit/test_calendar_tools.py`)

20 unit tests covering all tools and edge cases: busy intervals, all-free day, fully-booked day, 10-slot cap, CRM enrichment, vault search, no upcoming meetings, suggest with/without free slots, weekly pattern detection, no patterns (unique events), auth errors, CALENDAR_TOOLS list membership.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] KnowledgeVault class does not exist — used search_knowledge function**
- **Found during:** Task 1 (GREEN phase — test patching failure)
- **Issue:** Plan referenced `KnowledgeVault` class with `.search()` method but the RAG module exposes only module-level functions including `search_knowledge(query, top_k, user_id)`
- **Fix:** Changed implementation to lazy-import and call `search_knowledge` directly; updated test to patch `app.rag.knowledge_vault.search_knowledge`
- **Files modified:** `app/agents/tools/calendar_tool.py`, `tests/unit/test_calendar_tools.py`
- **Commit:** 43bb700

**2. [Rule 1 - Bug] Pattern detection false positive on unique-numbered events**
- **Found during:** Task 1 (GREEN phase — test failure)
- **Issue:** Normaliser stripping standalone digits caused "Unique Event 0/1/2" to all map to "unique event", triggering a false pattern
- **Fix:** Added dominance check — the most-common raw title must account for >50% of the group; unique-numbered events fail this check
- **Files modified:** `app/agents/tools/calendar_tool.py`
- **Commit:** 43bb700

## Self-Check: PASSED

- app/agents/tools/calendar_tool.py — FOUND
- app/integrations/google/calendar.py — FOUND (get_freebusy: 1, find_free_slots: 1)
- tests/unit/test_calendar_tools.py — FOUND (20 tests, all passing)
- commit 43bb700 — FOUND
- suggest_followup_meeting does not call create_event — VERIFIED
