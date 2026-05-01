---
phase: 87
slug: mic-dictation-via-web-speech-api
type: manual_uat
created: 2026-05-01
---

# Phase 87 Manual UAT

Real-browser UAT is required because jsdom does not implement `SpeechRecognition`.

## Browser Matrix

| Browser | UAT Steps | Pass Criteria | Result | Tester | Date |
|---------|-----------|---------------|--------|--------|------|
| Chrome desktop | Open `/dashboard/chat`, click mic, say "Hello world this is a test", pause | Words appear in input live; input remains editable; clicking send delivers the message | [ ] pending |  |  |
| Edge desktop | Open `/dashboard/chat`, click mic, say "Hello world this is a test", pause | Words appear in input live; input remains editable; clicking send delivers the message | [ ] pending |  |  |
| Safari macOS 17+ | Open `/dashboard/chat`, click mic, say "Hello world this is a test", pause | Words appear in input live; input remains editable; clicking send delivers the message, with possible 200-500ms delay vs Chrome | [ ] pending |  |  |
| Firefox desktop | Open `/dashboard/chat`, click mic | Disabled mic with "Voice input not supported in this browser" tooltip, or support-detect goes false with no spontaneous error toast | [ ] pending |  |  |
| iOS Safari 14.5+ | Open `/dashboard/chat`, click mic, say "Hello world this is a test", pause | Words appear in input live; input remains editable; clicking send delivers the message | [ ] pending |  |  |
| Boundary smoke (brain-dump) | Click the Brain icon, confirm voice session connects, agent greets, and the user can speak | No regression in Phase 84 behavior; brain-dump path unchanged | [ ] pending |  |  |

## Notes

- Chrome may auto-stop recognition after extended silence even with `continuous=true`; that is acceptable if the current words were already flushed into the input.
- iOS Safari requires `recognition.start()` to run inside a user gesture. The existing mic button click satisfies that requirement.
- If microphone permission is denied, the fallback should instruct the user to allow mic access in browser settings.

## Boundary Clause

If brain-dump regresses and the Brain icon no longer connects, or the agent goes silent mid-conversation, STOP and escalate. Chat-input mic changes must NOT affect this. Phase 84 behavior is the load-bearing invariant per `project_voice_brain_dump_architecture.md`.

## Sign-off

- [ ] SC1 — Mic button starts/stops browser dictation
- [ ] SC2 — Interim words appear live in the chat input
- [ ] SC3 — User can edit dictated text and send it normally
- [ ] SC4 — Unsupported browsers fall back cleanly
- [ ] SC5 — Brain-dump voice path remains unaffected
