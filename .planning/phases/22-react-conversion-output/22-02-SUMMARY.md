---
phase: 22-react-conversion-output
plan: 02
status: complete
started: 2026-03-23
completed: 2026-03-23
---

## Summary

PWA generator and Capacitor scaffold generator — both template-based services producing in-memory ZIP files with all required configuration for Progressive Web App and native mobile deployment.

## What Was Built

### PWA Generator
- `generate_pwa_zip()` — produces ZIP with manifest.json (3 icon sizes including maskable), hand-written cache-first service worker (no workbox), index.html with Apple iOS meta tags
- Design system theme_color/background_color applied throughout

### Capacitor Generator
- `generate_capacitor_zip()` — produces ZIP with capacitor.config.ts, package.json (resolved npm versions), www/index.html, README.md with setup instructions
- Self-contained `_resolve_npm_version()` — no cross-service imports (avoids wave-1 race condition)
- App ID derived via slugification with `com.pikar.` prefix

## Key Files

### Created
- `app/services/pwa_generator.py` — PWA manifest, service worker, iOS meta tags, ZIP creation
- `app/services/capacitor_generator.py` — Capacitor scaffold with config, package.json, README
- `tests/unit/app_builder/test_pwa_generator.py` — 7 unit tests for PWA generator
- `tests/unit/app_builder/test_capacitor_generator.py` — 7 unit tests for Capacitor generator

## Test Results

14/14 tests passed:
- PWA: valid ZIP, manifest fields, 3 icon sizes, SW with event listeners, iOS meta tags, manifest link, theme_color propagation
- Capacitor: valid ZIP, config with appId/appName, Capacitor packages in package.json, resolved versions, www/index.html, README with npx cap instructions, slugified appId

## Decisions

- npm resolution duplicated locally in capacitor_generator.py rather than importing from react_converter.py — both run in wave 1 and could be committed independently
- Hand-written service worker (no workbox) — keeps exported PWA zero-dependency

## Deviations

None.
