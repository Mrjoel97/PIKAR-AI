'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * TemplateGallery -- Browsable grid of pre-built content templates.
 *
 * Fetches templates from GET /suggestions/templates and renders them
 * as a filterable card grid. Clicking a card fires `onSelectTemplate`
 * so the parent can inject the template's example prompt into the chat.
 */

import { useEffect, useState } from 'react';
import {
  LayoutGrid,
  X,
  Rocket,
  FileText,
  Mail,
  Share2,
  Video,
  MessageCircle,
  Send,
  Search,
  Layout,
  Presentation,
  BarChart,
  Clipboard,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import {
  fetchContentTemplates,
  type ContentTemplate,
} from '@/services/suggestions';

// ---------------------------------------------------------------------------
// Icon mapping (string name -> lucide component)
// ---------------------------------------------------------------------------

const ICON_MAP: Record<string, LucideIcon> = {
  rocket: Rocket,
  'file-text': FileText,
  mail: Mail,
  'share-2': Share2,
  video: Video,
  'message-circle': MessageCircle,
  send: Send,
  search: Search,
  layout: Layout,
  presentation: Presentation,
  'bar-chart': BarChart,
  clipboard: Clipboard,
};

function TemplateIcon({ name }: { name: string }) {
  const Icon = ICON_MAP[name] || FileText;
  return <Icon size={20} className="text-teal-500" />;
}

// ---------------------------------------------------------------------------
// Category filter options
// ---------------------------------------------------------------------------

const CATEGORIES = [
  'All',
  'Content',
  'Marketing',
  'Sales',
  'Strategy',
  'Operations',
  'Data',
] as const;

// ---------------------------------------------------------------------------
// Skeleton loader
// ---------------------------------------------------------------------------

function SkeletonCards() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {[1, 2, 3].map((n) => (
        <div
          key={n}
          className="h-28 rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse"
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface TemplateGalleryProps {
  onSelectTemplate: (template: ContentTemplate) => void;
  onClose: () => void;
}

export function TemplateGallery({ onSelectTemplate, onClose }: TemplateGalleryProps) {
  const [templates, setTemplates] = useState<ContentTemplate[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      try {
        const cat = selectedCategory === 'All' ? undefined : selectedCategory.toLowerCase();
        const data = await fetchContentTemplates(cat);
        if (!cancelled) setTemplates(data);
      } catch {
        if (!cancelled) setTemplates([]);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [selectedCategory]);

  return (
    <div className="mb-3 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border border-slate-200 dark:border-slate-700 rounded-2xl shadow-lg p-4 animate-in fade-in slide-in-from-bottom-3 duration-300 max-h-[420px] overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <LayoutGrid size={16} className="text-teal-500" />
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            Content Templates
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {/* Category filters */}
      <div
        className="flex gap-1.5 mb-3 overflow-x-auto pb-1"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setSelectedCategory(cat)}
            className={`flex-shrink-0 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
              selectedCategory === cat
                ? 'bg-teal-600 text-white shadow-sm'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Template grid */}
      {isLoading ? (
        <SkeletonCards />
      ) : templates.length === 0 ? (
        <p className="text-sm text-slate-500 text-center py-6">
          No templates found for this category.
        </p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {templates.map((t) => (
            <button
              key={t.name}
              type="button"
              onClick={() => onSelectTemplate(t)}
              className="group flex flex-col items-start gap-2 p-3 rounded-xl border border-slate-100 dark:border-slate-800 hover:border-teal-300 dark:hover:border-teal-700 hover:scale-[1.02] transition-all text-left bg-white dark:bg-slate-900"
            >
              <TemplateIcon name={t.icon} />
              <p className="text-sm font-medium text-slate-800 dark:text-slate-100 leading-tight">
                {t.name}
              </p>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 leading-snug">
                {t.description}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
