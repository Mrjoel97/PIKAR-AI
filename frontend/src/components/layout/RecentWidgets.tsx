'use client';

import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Calendar,
  ClipboardList,
  FileText,
  Image,
  Layers,
  LayoutGrid,
  Play,
  Rocket,
  Workflow,
  Zap,
} from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
import { WidgetDisplayService, dispatchFocusWidget, WIDGET_CHANGE_EVENT } from '@/services/widgetDisplay';
import type { SavedWidget } from '@/types/widgets';
import type { WidgetType } from '@/types/widgets';

const WIDGET_TYPE_ICON: Record<WidgetType, React.ElementType> = {
  calendar: Calendar,
  form: ClipboardList,
  table: FileText,
  kanban_board: LayoutGrid,
  revenue_chart: BarChart3,
  initiative_dashboard: Rocket,
  product_launch: Rocket,
  workflow_builder: Workflow,
  morning_briefing: Zap,
  boardroom: Layers,
  suggested_workflows: Workflow,
  workflow: Workflow,
  image: Image,
  video: Play,
  video_spec: Play,
  braindump_analysis: FileText,
  campaign_hub: BarChart3,
  self_improvement: Zap,
  workflow_observability: Workflow,
  workflow_timeline: Workflow,
  landing_pages: FileText,
  api_connections: Workflow,
  department_activity: Layers,
};

function widgetIcon(type: WidgetType): React.ElementType {
  return WIDGET_TYPE_ICON[type] || Zap;
}

/**
 * Sidebar section showing the 5 most recently created widgets.
 * Reads directly from WidgetDisplayService localStorage cache.
 */
export function RecentWidgets() {
  const [widgets, setWidgets] = useState<SavedWidget[]>([]);
  const [userId, setUserId] = useState<string | null>(null);
  const supabase = createClient();

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const { data: { user } } = await supabase.auth.getUser();
      if (cancelled || !user) return;

      setUserId(user.id);
      const service = new WidgetDisplayService();
      setWidgets(service.getRecentWidgets(user.id, 5));
    }

    load();

    // Re-read when widgets change (pin/save/delete)
    function onWidgetChange() {
      load();
    }
    window.addEventListener(WIDGET_CHANGE_EVENT, onWidgetChange);

    return () => {
      cancelled = true;
      window.removeEventListener(WIDGET_CHANGE_EVENT, onWidgetChange);
    };
  }, [supabase]);

  if (widgets.length === 0) return null;

  const handleClick = (saved: SavedWidget) => {
    if (userId) {
      dispatchFocusWidget(saved.definition, userId);
    }
  };

  return (
    <div className="flex flex-col space-y-1">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-2 mb-1">
        Recent Widgets
      </h3>
      {widgets.map((w) => {
        const Icon = widgetIcon(w.definition.type);
        const title = w.definition.title || w.definition.type.replace(/_/g, ' ');
        return (
          <button
            key={w.id}
            onClick={() => handleClick(w)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 rounded-lg w-full text-left transition-colors"
            title={title}
          >
            <Icon size={14} className="text-slate-400 shrink-0" />
            <span className="truncate">{title}</span>
          </button>
        );
      })}
    </div>
  );
}
