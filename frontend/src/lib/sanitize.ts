import DOMPurify from 'dompurify';

/**
 * Sanitize HTML content using DOMPurify.
 * Strips all dangerous elements (scripts, event handlers, javascript: URIs,
 * data: URIs, SVG-based XSS, CSS injection, and mutation XSS vectors).
 */
export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['style'],
    FORBID_ATTR: ['style'],
  });
}
