/**
 * Build print-friendly HTML for a report (used for Export PDF / print).
 * In a .ts file so string literals containing < and </ don't confuse JSX parser.
 */
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export function buildReportPrintHtml(params: {
  title: string;
  summary: string;
  content: string;
  category: string;
  date: string;
}): string {
  const { title, summary, content, category, date } = params;
  return [
    '<!DOCTYPE html><html><head><meta charset="utf-8"/><title>',
    escapeHtml(title),
    '</title><style>body{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#1e293b;}h1{font-size:1.5rem;} .meta{color:#64748b;font-size:0.875rem;margin-bottom:1rem;} .summary{line-height:1.6;margin-bottom:1.5rem;} .content{background:#f8fafc;padding:1rem;border-radius:0.5rem;white-space:pre-wrap;}</style></head><body><h1>',
    escapeHtml(title),
    '</h1><div class="meta">',
    escapeHtml(category),
    ' · ',
    escapeHtml(date),
    '</div><div class="summary"><strong>Summary</strong><p>',
    escapeHtml(summary || '—'),
    '</p></div><div class="content">',
    escapeHtml(content || '—'),
    '</div></body></html>',
  ].join('');
}
