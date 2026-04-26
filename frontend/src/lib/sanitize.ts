/**
 * Sanitize HTML content using DOMPurify.
 * Strips all dangerous elements (scripts, event handlers, javascript: URIs,
 * data: URIs, SVG-based XSS, CSS injection, and mutation XSS vectors).
 *
 * SSR-safe: returns empty string on the server (no window/DOM available).
 * Content is sanitized on the client during hydration.
 */

let _purify: typeof import('dompurify').default | null = null;

function getPurify(): typeof import('dompurify').default | null {
  if (!_purify && typeof window !== 'undefined') {
    // Only load DOMPurify on the client where window/DOM is available
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    _purify = require('dompurify') as typeof import('dompurify').default;
  }
  return _purify;
}

export function sanitizeHtml(dirty: string): string {
  const purify = getPurify();
  if (!purify) {
    // Server-side: return empty string to avoid rendering unsanitized HTML
    return '';
  }
  return purify.sanitize(dirty, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['style'],
    FORBID_ATTR: ['style'],
  });
}
