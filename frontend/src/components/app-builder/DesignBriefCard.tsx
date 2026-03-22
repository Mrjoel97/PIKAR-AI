'use client';

import type { DesignBrief } from '@/types/app-builder';

interface DesignBriefCardProps {
  brief: DesignBrief;
  onChange: (updated: DesignBrief) => void;
  readOnly?: boolean;
}

export function DesignBriefCard({ brief, onChange, readOnly = false }: DesignBriefCardProps) {
  function updateColor(index: number, field: 'hex' | 'name', value: string) {
    const updated = brief.colors.map((c, i) =>
      i === index ? { ...c, [field]: value } : c,
    );
    onChange({ ...brief, colors: updated });
  }

  function updateTypography(field: 'heading' | 'body' | 'scale', value: string) {
    onChange({ ...brief, typography: { ...brief.typography, [field]: value } });
  }

  function updateSpacing(field: 'base_unit' | 'section_padding' | 'card_padding', value: string) {
    onChange({ ...brief, spacing: { ...brief.spacing, [field]: value } });
  }

  return (
    <div
      data-testid="design-brief-card"
      className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6"
    >
      {/* Color Palette */}
      <section>
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Color Palette</h3>
        <div className="space-y-2">
          {brief.colors.map((color, i) => (
            <div key={i} className="flex items-center gap-3">
              <div
                data-testid="color-swatch"
                className="w-8 h-8 rounded-full border border-slate-200 shrink-0"
                style={{ backgroundColor: color.hex }}
                aria-label={`${color.name} color swatch`}
              />
              <input
                type="text"
                value={color.hex}
                onChange={(e) => updateColor(i, 'hex', e.target.value)}
                disabled={readOnly}
                aria-label={`Color ${i + 1} hex`}
                className="border border-slate-300 rounded-md px-2 py-1 text-sm w-24 font-mono disabled:opacity-60"
              />
              <input
                type="text"
                value={color.name}
                onChange={(e) => updateColor(i, 'name', e.target.value)}
                disabled={readOnly}
                aria-label={`Color ${i + 1} name`}
                className="border border-slate-300 rounded-md px-2 py-1 text-sm flex-1 disabled:opacity-60"
              />
            </div>
          ))}
        </div>
      </section>

      {/* Typography */}
      <section>
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Typography</h3>
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-500 w-24 shrink-0">Heading Font</label>
            <input
              type="text"
              value={brief.typography.heading}
              onChange={(e) => updateTypography('heading', e.target.value)}
              disabled={readOnly}
              className="border border-slate-300 rounded-md px-2 py-1 text-sm flex-1 disabled:opacity-60"
            />
          </div>
          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-500 w-24 shrink-0">Body Font</label>
            <input
              type="text"
              value={brief.typography.body}
              onChange={(e) => updateTypography('body', e.target.value)}
              disabled={readOnly}
              className="border border-slate-300 rounded-md px-2 py-1 text-sm flex-1 disabled:opacity-60"
            />
          </div>
          {brief.typography.scale !== undefined && (
            <div className="flex items-center gap-3">
              <label className="text-xs text-slate-500 w-24 shrink-0">Type Scale</label>
              <input
                type="text"
                value={brief.typography.scale}
                onChange={(e) => updateTypography('scale', e.target.value)}
                disabled={readOnly}
                className="border border-slate-300 rounded-md px-2 py-1 text-sm flex-1 disabled:opacity-60"
              />
            </div>
          )}
        </div>
      </section>

      {/* Spacing */}
      <section>
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Spacing</h3>
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-500 w-24 shrink-0">Base Unit</label>
            <input
              type="text"
              value={brief.spacing.base_unit}
              onChange={(e) => updateSpacing('base_unit', e.target.value)}
              disabled={readOnly}
              className="border border-slate-300 rounded-md px-2 py-1 text-sm flex-1 disabled:opacity-60"
            />
          </div>
        </div>
      </section>

      {/* DESIGN.md Preview */}
      <section>
        <h3 className="text-sm font-semibold text-slate-700 mb-3">DESIGN.md Preview</h3>
        <textarea
          value={brief.raw_markdown}
          onChange={(e) => onChange({ ...brief, raw_markdown: e.target.value })}
          disabled={readOnly}
          rows={6}
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm font-mono resize-y disabled:opacity-60"
        />
      </section>
    </div>
  );
}
