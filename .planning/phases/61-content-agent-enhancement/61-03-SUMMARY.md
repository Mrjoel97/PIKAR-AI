---
phase: 61-content-agent-enhancement
plan: 03
subsystem: agents/content
tags: [content, brand-voice, tdd, agent-tool, stdlib-nlp]

requires:
  - phase: 61-content-agent-enhancement
    provides: Plan 61-01 simple_create_content fast path (voice learning feeds the brand profile that fast path reads)

provides:
  - BrandVoiceService with 14 unit tests covering analysis, tone extraction,
    vocabulary patterns, voice profile building, persistence, and full pipeline
  - learn_brand_voice() tool exposed to the Content Director
  - BRAND VOICE AUTO-LEARNING section in CONTENT_DIRECTOR_INSTRUCTION

affects: [61-01-fast-path, 61-02-scheduling, content-director, brand-profile]

tech-stack:
  added: []
  patterns:
    - Pure-stdlib NLP (re + collections.Counter only — no NLTK/spaCy)
    - Multi-signal formality scoring (contractions, avg word length,
      exclamation density, emoji density — averaged with neutral signals
      only when data is present)
    - Module-level update_brand_profile import so tests can patch
      app.services.brand_voice_service.update_brand_profile directly
    - TDD RED → GREEN cycle (tests committed first in 8694f364, impl in 25e3e5e0)

key-files:
  created:
    - app/services/brand_voice_service.py
  modified:
    - app/agents/content/tools.py (added learn_brand_voice)
    - app/agents/content/agent.py (import + tools list + instruction section)
    - tests/unit/test_brand_voice_service.py (RED committed in 8694f364)

key-decisions:
  - "Persistence uses module-level update_brand_profile import — REQUIRED by test_persist_calls_update_brand_profile which patches app.services.brand_voice_service.update_brand_profile directly. A lazy/local import would break the patch path."
  - "Formality scoring averages 4 signals (contractions, emoji density, avg word length, exclamation density). Emoji signal is neutral (excluded from average) when no emojis present, preventing it from artificially boosting formality in casual-but-emoji-free text."
  - "MIN_CONTENT_PIECES = 5 is enforced in two places: analyze_content_samples (pure function gate) and analyze_and_learn (pipeline gate that returns success: False with a user-facing reason)."
  - "Distinctive words filter: length > 2 chars, not in STOPWORDS, ranked by document frequency (words appearing in 2+ content pieces rise first), top-20 cap."

patterns-established:
  - "Stdlib-only NLP analysis pattern — any future voice/style analysis in Pikar should follow the BrandVoiceService structure (pure functions for each signal, composable extract_*() helpers, build_*() combiner)"
  - "Voice learning agent-tool wrapper: try/except around service call, logger.info on both ready and not-ready paths, return the service result dict unchanged so agent instructions can pattern-match on fields"

requirements-completed: [CONTENT-03]

duration: ~10min (resumed mid-TDD cycle — impl was the GREEN step)
completed: 2026-04-11
---

# Phase 61 Plan 03: Brand Voice Auto-Learning Summary

**BrandVoiceService analyzes 5+ pieces of user content to extract tone, vocabulary, and sentence patterns, then persists the learned voice to the brand profile so all future content generation reflects the user's natural style without manual configuration.**

## Performance

- **Duration:** ~10 min (resumed mid-TDD cycle; tests committed earlier in 8694f364)
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 edited)

## Accomplishments

### Task 1: BrandVoiceService with passing tests

- **Created `app/services/brand_voice_service.py`** (423 lines) with:
  - `analyze_and_learn(user_id)` — full pipeline: fetch content history → analyze → persist
  - `get_content_history(user_id, limit)` — reads from `ContentService.list_content` with non-trivial filter (content length > 20)
  - `analyze_content_samples(texts)` — pure function entry point, enforces 5-piece minimum
  - `extract_tone_markers(texts)` — exclamation/question/emoji rates + formality score
  - `extract_vocabulary_patterns(texts)` — top-20 distinctive words + avg word length
  - `extract_sentence_patterns(texts)` — avg sentence length, variance, short-sentence ratio
  - `build_voice_profile(tone, vocab, sentences)` — compiles features into tone_summary, personality_traits, example_sentences, formality_score, avg_sentence_length, avg_word_count, common_phrases
  - `persist_voice_to_brand_profile(user_id, voice_profile)` — calls `update_brand_profile` with joined example sentences

- **Formality scoring** uses four weighted signals (contractions, emoji, avg word length, exclamation density). Test casual content (CASUAL_SAMPLES with contractions + exclamations) reliably scores < 0.4; formal content (FORMAL_SAMPLES with long words + no exclamations) reliably scores > 0.6.

- **Pure stdlib** — re, collections.Counter. No NLTK/spaCy dependency to install in the Docker image.

### Task 2: Content Director tool wiring

- **`app/agents/content/tools.py`** — added `learn_brand_voice()` async tool that resolves `get_current_user_id()`, instantiates `BrandVoiceService`, calls `analyze_and_learn`, logs the result, and returns the dict unchanged.

- **`app/agents/content/agent.py`**:
  - Imported `learn_brand_voice` from tools module
  - Added to `create_content_agent()` tools list (right after the 61-01 and 61-02 tools)
  - Appended **BRAND VOICE AUTO-LEARNING** section to `CONTENT_DIRECTOR_INSTRUCTION` with:
    - When-to-trigger rules (explicit user ask, 5th piece threshold, missing voice_tone)
    - What-to-say guidance after learning ("I've analyzed your writing style. You tend to...")
    - Graceful fallback for insufficient content

- **Tool exposure verified** — Python import smoke test (`from app.agents.content.agent import create_content_agent`) succeeds.

## Task Commits

1. **Task 1 TDD RED (earlier):** `8694f364` — `test(61-03): add failing tests for BrandVoiceService` (307 lines, 13 tests; pytest collected 14 — one extra from parametrization)
2. **Task 1 TDD GREEN:** `25e3e5e0` — `feat(61-03): implement BrandVoiceService with 14 passing tests`
3. **Task 2:** `c08ea308` — `feat(61-03): wire learn_brand_voice into Content Director agent`

## Test Results

```
tests/unit/test_brand_voice_service.py — 14 passed in 7.24s
```

- 2 tests for minimum-content gate (3 items, 0 items)
- 3 tests for content analysis (basic metrics, casual formality, formal formality)
- 2 tests for tone marker extraction (presence, formal-low-exclamation)
- 3 tests for vocabulary patterns (distinctive words, stopword exclusion, avg word length)
- 1 test for voice profile building
- 1 test for persistence (exact keyword args to update_brand_profile)
- 2 tests for full pipeline (with enough content, insufficient content)

## Decisions Made

- **Module-level `update_brand_profile` import** because the RED test at line 239 patches `app.services.brand_voice_service.update_brand_profile` — a lazy import would never be called through that patch path.
- **Neutral signal handling** — when emoji_count is 0, the emoji formality signal is skipped (not counted as "formal because no emojis") so casual-but-emoji-free content is correctly scored < 0.4.
- **Distinctive word filter at 3+ characters** — excludes split contraction artifacts (`i`, `ve`, `don`, `t`) without needing a separate preprocessing pass.
- **`MIN_CONTENT_PIECES = 5`** class constant — matches the 5-piece threshold referenced in plan `must_haves.truths[0]` and both test classes (`TestAnalyzeContentHistoryMinimum`).
- **TDD GREEN commit strategy** — implementation landed as a separate feat commit (not squashed with RED) so git history preserves the clean RED → GREEN cycle.

## Deviations from Plan

None. Task 1's implementation matches the plan's class signature exactly. Task 2's tool wrapper mirrors the plan's suggested shape with one addition: logger.info on the ready/not-ready branches so operator telemetry shows why voice learning did or didn't trigger.

## Issues Encountered

- **Pre-existing RUF013 warnings** in `app/agents/content/tools.py` (lines 247, 274) and `app/agents/content/agent.py:509` from `str = None` (should be `str | None = None`). Out of scope for Plan 61-03 — existed before this plan.
- **Docker backend image stale** for the earlier UAT session (Phase 51) — `sentry_sdk` wasn't installed. Worked around at the time by making the import conditional (commit `ae42f4b7`). Unrelated to 61-03 but noted in case a future UAT hits a similar stale-image issue.

## User Setup Required

None. `learn_brand_voice` is a backend-only agent tool — users invoke it by asking the Content Director "learn my writing style" or it triggers automatically after their 5th content piece.

## Next Phase Readiness

- **CONTENT-03 complete** — brand voice auto-learning is functional.
- **Plan 61-04 (performance feedback loop)** is unblocked — Plan 03 doesn't modify files that 04 needs.
- **Phase 61 progress:** 3 of 4 plans complete (61-01, 61-02, 61-03). Plan 61-04 remaining.

---

*Phase: 61-content-agent-enhancement*
*Completed: 2026-04-11*
