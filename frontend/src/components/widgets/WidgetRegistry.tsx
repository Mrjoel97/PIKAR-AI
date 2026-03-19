/**
 * Widget Registry - Central mapping of widget types to React components.
 * 
 * This module provides type-safe widget resolution for agent-generated UI.
 * Each widget type string maps to a dynamic React component.
 * 
 * @example
 * // Resolve and render a widget
 * const { Widget } = await import('./WidgetRegistry');
 * <Widget definition={msg.widget} onDismiss={() => {...}} />
 */

import React, { ComponentType } from 'react';
import dynamic from 'next/dynamic';
import { WidgetDefinition, WidgetType } from '@/types/widgets';
import { Loader2, AlertCircle, ChevronDown, ChevronUp, Maximize2, X, Star } from 'lucide-react';

// =============================================================================
// Widget Props Interface
// =============================================================================

export interface WidgetProps {
    /** Widget definition from agent */
    definition: WidgetDefinition;
    /** Callback when user performs an action within the widget */
    onAction?: (action: string, payload?: unknown) => void;
    /** Callback when user dismisses the widget */
    onDismiss?: () => void;
}

// =============================================================================
// Fallback Components
// =============================================================================

function WidgetSkeleton() {
    return (
        <div className="flex items-center justify-center p-8 bg-slate-50 dark:bg-slate-800/50 rounded-lg animate-pulse">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
            <span className="ml-2 text-sm text-slate-500">Loading widget...</span>
        </div>
    );
}

function UnknownWidget({ definition }: WidgetProps) {
    return (
        <div className="flex items-center gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <AlertCircle className="w-5 h-5 text-amber-500" />
            <div>
                <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
                    Unknown widget type: {definition.type}
                </p>
                <p className="text-xs text-amber-600 dark:text-amber-400">
                    This widget type is not registered in the system.
                </p>
            </div>
        </div>
    );
}

// =============================================================================
// Dynamic Widget Components
// =============================================================================

const InitiativeDashboard = dynamic(() => import('./InitiativeDashboard'), {
    loading: WidgetSkeleton,
    ssr: false
});
const RevenueChart = dynamic(() => import('./RevenueChart'), {
    loading: WidgetSkeleton,
    ssr: false
});
const ProductLaunchWidget = dynamic(() => import('./ProductLaunchWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const WorkflowBuilderWidget = dynamic(() => import('./WorkflowBuilderWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const MorningBriefing = dynamic(() => import('./MorningBriefing'), {
    loading: WidgetSkeleton,
    ssr: false
});
const BoardroomWidget = dynamic(() => import('./BoardroomWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const SuggestedWorkflowsWidget = dynamic(() => import('./SuggestedWorkflowsWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const CalendarWidget = dynamic(() => import('./CalendarWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const KanbanWidget = dynamic(() => import('./KanbanWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const FormWidget = dynamic(() => import('./FormWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const TableWidget = dynamic(() => import('./TableWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const WorkflowWidget = dynamic(() => import('./WorkflowWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const ImageWidget = dynamic(() => import('./ImageWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const VideoWidget = dynamic(() => import('./VideoWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const VideoSpecWidget = dynamic(() => import('./VideoSpecWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const BraindumpAnalysisWidget = dynamic(() => import('./BraindumpAnalysisWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const CampaignHubWidget = dynamic(() => import('./CampaignHubWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const SelfImprovementWidget = dynamic(() => import('./SelfImprovementWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const WorkflowObservabilityWidget = dynamic(() => import('./WorkflowObservabilityWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const WorkflowTimelineWidget = dynamic(() => import('./WorkflowTimelineWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});
const DailyBriefingWidget = dynamic(() => import('./DailyBriefingWidget'), {
    loading: () => <WidgetSkeleton />,
    ssr: false,
});

// =============================================================================
// Widget Registry Map
// =============================================================================

/**
 * Maps widget type strings to their React component implementations.
 * Add new widgets here as they are created.
 */
const WIDGET_MAP: Record<string, ComponentType<WidgetProps>> = {
    initiative_dashboard: InitiativeDashboard,
    revenue_chart: RevenueChart,
    product_launch: ProductLaunchWidget,
    kanban_board: KanbanWidget,
    workflow_builder: WorkflowBuilderWidget,
    morning_briefing: MorningBriefing,
    boardroom: BoardroomWidget,
    suggested_workflows: SuggestedWorkflowsWidget,
    form: FormWidget,
    table: TableWidget,
    calendar: CalendarWidget,
    workflow: WorkflowWidget,
    image: ImageWidget,
    video: VideoWidget,
    video_spec: VideoSpecWidget,
    braindump_analysis: BraindumpAnalysisWidget,
    campaign_hub: CampaignHubWidget,
    self_improvement: SelfImprovementWidget,
    workflow_observability: WorkflowObservabilityWidget,
    workflow_timeline: WorkflowTimelineWidget,
    daily_briefing: DailyBriefingWidget,
};

// =============================================================================
// Widget Resolution
// =============================================================================

/**
 * Resolves a widget type to its corresponding React component.
 * Returns UnknownWidget if the type is not registered.
 */
export function resolveWidget(type: WidgetType): ComponentType<WidgetProps> {
    return WIDGET_MAP[type] ?? UnknownWidget;
}

/**
 * Checks if a widget type is registered in the system.
 */
export function isWidgetTypeSupported(type: string): type is WidgetType {
    return type in WIDGET_MAP;
}

/**
 * Returns all registered widget types.
 */
export function getRegisteredWidgetTypes(): WidgetType[] {
    return Object.keys(WIDGET_MAP) as WidgetType[];
}

// =============================================================================
// Widget Container Component
// =============================================================================

interface WidgetContainerProps extends WidgetProps {
    /** Whether the widget is in minimized state */
    isMinimized?: boolean;
    /** Toggle minimized state */
    onToggleMinimized?: () => void;
    /** Open widget in expanded/full-screen mode */
    onExpand?: () => void;
    /** Custom class name for the container */
    className?: string;
    /** Whether to show the pin button */
    showPinButton?: boolean;
    /** When true, render widget content without chrome (no header/controls) */
    fullFocus?: boolean;
}

/**
 * Widget container with header, collapse/expand, and dismiss functionality.
 * Wraps the actual widget component with consistent UI controls.
 */
export function WidgetContainer({
    definition,
    isMinimized = false,
    onAction,
    onDismiss,
    onToggleMinimized,
    onExpand,
    className,
    showPinButton,
    fullFocus = false,
}: WidgetContainerProps) {
    const WidgetComponent = resolveWidget(definition.type);
    const useFullFocus = fullFocus;

    if (useFullFocus) {
        return (
            <div className={`w-full max-w-full rounded-[28px] overflow-hidden ${className || ''}`}>
                <WidgetComponent
                    definition={definition}
                    onAction={onAction}
                    onDismiss={onDismiss}
                />
            </div>
        );
    }

    return (
        <div className={`w-full bg-white dark:bg-slate-800 rounded-[28px] border border-slate-100/80 dark:border-slate-700 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] overflow-hidden ${className || ''}`}>
            {/* Widget Header */}
            <div className="flex items-center justify-between px-5 py-3.5 bg-slate-50/60 dark:bg-slate-800/80 border-b border-slate-100/80 dark:border-slate-700">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-teal-500"></div>
                    <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                        {definition.title || definition.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </h4>
                </div>

                <div className="flex items-center gap-1">
                    {showPinButton && onAction && (
                        <button
                            onClick={() => onAction('pin')}
                            className="p-1.5 hover:bg-amber-100 dark:hover:bg-amber-900/40 rounded-md transition-colors"
                            aria-label="Pin to dashboard"
                            title="Pin to Dashboard"
                        >
                            <Star className="w-4 h-4 text-slate-400 hover:text-amber-500" />
                        </button>
                    )}

                    {onToggleMinimized && (
                        <button
                            onClick={onToggleMinimized}
                            className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md transition-colors"
                            aria-label={isMinimized ? 'Expand' : 'Collapse'}
                        >
                            {isMinimized ? (
                                <ChevronDown className="w-4 h-4 text-slate-500" />
                            ) : (
                                <ChevronUp className="w-4 h-4 text-slate-500" />
                            )}
                        </button>
                    )}

                    {definition.expandable && onExpand && (
                        <button
                            onClick={onExpand}
                            className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md transition-colors"
                            aria-label="Expand to full screen"
                        >
                            <Maximize2 className="w-4 h-4 text-slate-500" />
                        </button>
                    )}

                    {definition.dismissible && onDismiss && (
                        <button
                            onClick={onDismiss}
                            className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-md transition-colors"
                            aria-label="Dismiss"
                        >
                            <X className="w-4 h-4 text-slate-500 hover:text-red-500" />
                        </button>
                    )}
                </div>
            </div>

            {/* Widget Content */}
            {!isMinimized && (
                <div className="p-4">
                    <WidgetComponent
                        definition={definition}
                        onAction={onAction}
                        onDismiss={onDismiss}
                    />
                </div>
            )}

            {/* Minimized State */}
            {isMinimized && (
                <div className="px-4 py-2 text-xs text-slate-500 dark:text-slate-400">
                    Widget collapsed • Click to expand
                </div>
            )}
        </div>
    );
}

/**
 * Simple widget component without container chrome.
 * Use when you want to render just the widget content.
 */
export function Widget({ definition, onAction, onDismiss }: WidgetProps) {
    const WidgetComponent = resolveWidget(definition.type);

    return (
        <WidgetComponent
            definition={definition}
            onAction={onAction}
            onDismiss={onDismiss}
        />
    );
}
