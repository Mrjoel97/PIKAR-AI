// Synchronous, render-blocking silencer for browser-extension promise noise.
// Loaded via a plain <script src> tag in <head> (not next/script) so it
// executes before any other page script and before extension content
// scripts that fire rejections during initial page load. Handles three
// extension-specific patterns from Grammarly, LastPass, MetaMask, and ad
// blockers that have no functional effect on the app.
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

  // 1. Suppress unhandledrejection events for known extension noise.
  window.addEventListener('unhandledrejection', function (event) {
    if (matchesNoise(extractMessage(event.reason))) {
      event.preventDefault();
    }
  });

  // 2. Wrap console.error so any noise that bypasses the rejection event
  //    (Chrome's "Uncaught (in promise)" emitter, extension isolated worlds)
  //    is filtered at the console layer. Patterns are extension-specific
  //    strings — zero risk of swallowing app-originated errors.
  var originalError = console.error.bind(console);
  console.error = function () {
    for (var i = 0; i < arguments.length; i++) {
      if (matchesNoise(extractMessage(arguments[i]))) return;
    }
    return originalError.apply(console, arguments);
  };
})();
