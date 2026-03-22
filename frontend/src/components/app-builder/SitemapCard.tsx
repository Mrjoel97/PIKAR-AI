'use client';

import type { SitemapPage } from '@/types/app-builder';

const DEVICE_OPTIONS = ['desktop', 'mobile', 'tablet'] as const;
type Device = (typeof DEVICE_OPTIONS)[number];

interface SitemapCardProps {
  sitemap: SitemapPage[];
  onChange: (updated: SitemapPage[]) => void;
  readOnly?: boolean;
}

export function SitemapCard({ sitemap, onChange, readOnly = false }: SitemapCardProps) {
  function updatePage(index: number, updated: Partial<SitemapPage>) {
    onChange(sitemap.map((p, i) => (i === index ? { ...p, ...updated } : p)));
  }

  function toggleDevice(index: number, device: Device) {
    const page = sitemap[index];
    const has = page.device_targets.includes(device);
    const updated = has
      ? page.device_targets.filter((d) => d !== device)
      : [...page.device_targets, device];
    updatePage(index, { device_targets: updated });
  }

  function addPage() {
    onChange([
      ...sitemap,
      { page: `page-${sitemap.length + 1}`, title: 'New Page', sections: [], device_targets: ['desktop'] },
    ]);
  }

  return (
    <div
      data-testid="sitemap-card"
      className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm"
    >
      <h3 className="text-sm font-semibold text-slate-700 mb-4">Sitemap</h3>

      <div className="space-y-0">
        {sitemap.map((page, i) => (
          <div key={i} className="border-b border-slate-100 py-3 last:border-0">
            {/* Page title */}
            <input
              type="text"
              value={page.title}
              onChange={(e) => updatePage(i, { title: e.target.value })}
              disabled={readOnly}
              aria-label={`Page ${i + 1} title`}
              className="border border-slate-300 rounded-md px-2 py-1 text-sm w-full mb-2 disabled:opacity-60"
            />

            {/* Sections */}
            <div className="mb-2">
              <label className="text-xs text-slate-400 block mb-1">Sections (comma-separated)</label>
              <input
                type="text"
                value={page.sections.join(', ')}
                onChange={(e) =>
                  updatePage(i, {
                    sections: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                  })
                }
                disabled={readOnly}
                aria-label={`Page ${i + 1} sections`}
                className="border border-slate-300 rounded-md px-2 py-1 text-sm w-full disabled:opacity-60"
              />
            </div>

            {/* Device targets */}
            <div className="flex gap-3">
              {DEVICE_OPTIONS.map((device) => (
                <label key={device} className="flex items-center gap-1 text-xs text-slate-500 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={page.device_targets.includes(device)}
                    onChange={() => toggleDevice(i, device)}
                    disabled={readOnly}
                    className="accent-indigo-600"
                  />
                  {device.charAt(0).toUpperCase() + device.slice(1)}
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      {!readOnly && (
        <button
          type="button"
          onClick={addPage}
          className="mt-4 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
        >
          + Add Page
        </button>
      )}
    </div>
  );
}
