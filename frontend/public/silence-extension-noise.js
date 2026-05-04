// Synchronous, render-blocking silencer for browser-extension promise noise.
// Loaded via a plain <script src> tag in <head> (not next/script) so it
// executes before any other page script and before extension content
// scripts that fire rejections during initial page load. Handles three
// extension-specific patterns from Grammarly, LastPass, MetaMask, and ad
// blockers that have no functional effect on the app.
//
// We intentionally do NOT wrap console.error here. An earlier version did,
// as a defense-in-depth fallback for paths Chrome uses that bypass the
// unhandledrejection event — but Chrome attributes the source of every
// console.error to the wrapper's call site, which obscures the real
// origin of legitimate app errors (e.g. an "API Error 401" suddenly
// looks like it's coming from `silence-extension-noise.js:52`). The cost
// turned out to outweigh the benefit because the patterns we wanted to
// catch fire from extension isolated worlds that don't reach
// page-level console hooks anyway.
(function () {
  var PATTERNS = [
    'message channel closed before a response was received',
    'A listener indicated an asynchronous response by returning true',
    'Extension context invalidated',
  ];

  function extractMessage(value) {
    if (!value) return '';
    if (typeof value === 'string') return value;
    if (value instanceof Error) return value.message || '';
    if (typeof value === 'object' && typeof value.message === 'string') {
      return value.message;
    }
    try {
      return String(value);
    } catch (_) {
      return '';
    }
  }

  function matchesNoise(message) {
    if (!message) return false;
    for (var i = 0; i < PATTERNS.length; i++) {
      if (message.indexOf(PATTERNS[i]) !== -1) return true;
    }
    return false;
  }

  // Suppress unhandledrejection events for known extension noise.
  window.addEventListener('unhandledrejection', function (event) {
    if (matchesNoise(extractMessage(event.reason))) {
      event.preventDefault();
    }
  });
})();
