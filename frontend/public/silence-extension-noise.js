// Pre-hydration silencer for browser-extension promise noise.
// Loaded via next/script with strategy="beforeInteractive" so it runs
// before React hydration and can catch rejections fired by extension
// content scripts (Grammarly, LastPass, MetaMask, ad blockers) during
// initial page load. The React-side <AbortErrorSilencer /> handles
// app-originated AbortErrors using the shared isAbortLikeError helper.
(function () {
  var PATTERNS = [
    'message channel closed before a response was received',
    'A listener indicated an asynchronous response by returning true',
    'Extension context invalidated',
  ];
  window.addEventListener('unhandledrejection', function (event) {
    var reason = event.reason;
    var message =
      reason && (reason.message || (typeof reason === 'string' ? reason : ''));
    if (!message) return;
    for (var i = 0; i < PATTERNS.length; i++) {
      if (message.indexOf(PATTERNS[i]) !== -1) {
        event.preventDefault();
        return;
      }
    }
  });
})();
