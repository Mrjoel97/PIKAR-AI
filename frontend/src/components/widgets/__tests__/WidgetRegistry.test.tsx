// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

import {
    resolveWidget,
    isWidgetTypeSupported,
    getRegisteredWidgetTypes,
    WidgetContainer,
    Widget,
    isBranchingTemplate,
    resolveWorkflowRunWidget,
} from '../WidgetRegistry';
import type { WidgetDefinition } from '@/types/widgets';
import type { components } from '@/types/api.generated';
type GraphNode = components['schemas']['GraphNode'];

// ---------------------------------------------------------------------------
// Mock all dynamic widget imports so we don't pull in real component trees.
// next/dynamic is mocked to return a simple stub component that renders
// a data-testid matching the display name.
// ---------------------------------------------------------------------------
vi.mock('next/dynamic', () => {
    return {
        __esModule: true,
        default: (loader: () => Promise<any>) => {
            // Return a simple stub component
            const Stub = (props: any) => (
                <div data-testid="dynamic-widget">{props.definition?.type ?? 'widget'}</div>
            );
            Stub.displayName = 'DynamicStub';
            return Stub;
        },
    };
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeDefinition(overrides: Partial<WidgetDefinition> = {}): WidgetDefinition {
    return {
        type: 'initiative_dashboard',
        title: 'Test Widget',
        data: { initiatives: [], metrics: { total: 0, completed: 0, in_progress: 0, blocked: 0 } },
        ...overrides,
    };
}

// =============================================================================
// resolveWidget
// =============================================================================

describe('resolveWidget', () => {
    it('returns a component for every known widget type in the registry', () => {
        const knownTypes = [
            'initiative_dashboard',
            'revenue_chart',
            'product_launch',
            'kanban_board',
            'workflow_builder',
            'morning_briefing',
            'boardroom',
            'suggested_workflows',
            'form',
            'table',
            'calendar',
            'workflow',
            'image',
            'video',
            'video_spec',
            'braindump_analysis',
            'markdown_report',
            'campaign_hub',
            'self_improvement',
            'workflow_observability',
            'workflow_timeline',
            'daily_briefing',
            'app_builder_launcher',
        ] as const;

        knownTypes.forEach((type) => {
            const Component = resolveWidget(type as any);
            expect(Component).toBeDefined();
            expect(typeof Component).toBe('function');
        });
    });

    it('returns UnknownWidget for an unregistered type', () => {
        const Component = resolveWidget('nonexistent_widget' as any);
        expect(Component).toBeDefined();
    });

    it('renders UnknownWidget with informative text for unknown types', () => {
        const Component = resolveWidget('nonexistent_widget' as any);
        const def = makeDefinition({ type: 'nonexistent_widget' as any });
        render(<Component definition={def} />);
        expect(screen.getByText(/Unknown widget type/i)).toBeDefined();
        expect(screen.getByText(/nonexistent_widget/)).toBeDefined();
    });
});

// =============================================================================
// isWidgetTypeSupported
// =============================================================================

describe('isWidgetTypeSupported', () => {
    it('returns true for registered types', () => {
        expect(isWidgetTypeSupported('initiative_dashboard')).toBe(true);
        expect(isWidgetTypeSupported('revenue_chart')).toBe(true);
        expect(isWidgetTypeSupported('daily_briefing')).toBe(true);
        expect(isWidgetTypeSupported('workflow_builder')).toBe(true);
        expect(isWidgetTypeSupported('app_builder_launcher')).toBe(true);
        expect(isWidgetTypeSupported('markdown_report')).toBe(true);
    });

    it('returns false for unregistered types', () => {
        expect(isWidgetTypeSupported('fake_widget')).toBe(false);
        expect(isWidgetTypeSupported('')).toBe(false);
        expect(isWidgetTypeSupported('INITIATIVE_DASHBOARD')).toBe(false);
    });
});

// =============================================================================
// getRegisteredWidgetTypes
// =============================================================================

describe('getRegisteredWidgetTypes', () => {
    it('returns an array of all registered widget type strings', () => {
        const types = getRegisteredWidgetTypes();
        expect(Array.isArray(types)).toBe(true);
        // The registry has 21 entries (20 from WidgetType + daily_briefing)
        expect(types.length).toBeGreaterThanOrEqual(20);
    });

    it('includes core widget types', () => {
        const types = getRegisteredWidgetTypes();
        expect(types).toContain('initiative_dashboard');
        expect(types).toContain('revenue_chart');
        expect(types).toContain('daily_briefing');
        expect(types).toContain('workflow_builder');
        expect(types).toContain('campaign_hub');
        expect(types).toContain('markdown_report');
    });

    it('does not contain duplicates', () => {
        const types = getRegisteredWidgetTypes();
        const unique = new Set(types);
        expect(unique.size).toBe(types.length);
    });
});

// =============================================================================
// WidgetContainer
// =============================================================================

describe('WidgetContainer', () => {
    it('renders widget title from definition', () => {
        const def = makeDefinition({ title: 'My Custom Title' });
        render(<WidgetContainer definition={def} />);
        expect(screen.getByText('My Custom Title')).toBeDefined();
    });

    it('falls back to formatted type name when title is missing', () => {
        const def = makeDefinition({ title: undefined, type: 'revenue_chart' });
        render(<WidgetContainer definition={def} />);
        // The code formats the type: "revenue_chart" -> "Revenue Chart"
        expect(screen.getByText('Revenue Chart')).toBeDefined();
    });

    it('shows collapse button when onToggleMinimized is provided', () => {
        const onToggle = vi.fn();
        const def = makeDefinition();
        render(<WidgetContainer definition={def} onToggleMinimized={onToggle} />);
        const collapseBtn = screen.getByLabelText('Collapse');
        expect(collapseBtn).toBeDefined();
    });

    it('shows expand label when isMinimized is true', () => {
        const onToggle = vi.fn();
        const def = makeDefinition();
        render(
            <WidgetContainer
                definition={def}
                isMinimized={true}
                onToggleMinimized={onToggle}
            />,
        );
        const expandBtn = screen.getByLabelText('Expand');
        expect(expandBtn).toBeDefined();
    });

    it('calls onToggleMinimized when collapse/expand button is clicked', () => {
        const onToggle = vi.fn();
        const def = makeDefinition();
        render(<WidgetContainer definition={def} onToggleMinimized={onToggle} />);
        fireEvent.click(screen.getByLabelText('Collapse'));
        expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it('shows minimized state text when isMinimized is true', () => {
        const def = makeDefinition();
        render(
            <WidgetContainer
                definition={def}
                isMinimized={true}
                onToggleMinimized={() => {}}
            />,
        );
        expect(screen.getByText(/Widget collapsed/)).toBeDefined();
    });

    it('does not render widget content when minimized', () => {
        const def = makeDefinition();
        render(
            <WidgetContainer
                definition={def}
                isMinimized={true}
                onToggleMinimized={() => {}}
            />,
        );
        // The dynamic stub renders data-testid="dynamic-widget"
        // When minimized, the widget content div is not rendered
        const widgetContent = screen.queryByTestId('dynamic-widget');
        expect(widgetContent).toBeNull();
    });

    it('shows dismiss button when definition.dismissible is true and onDismiss provided', () => {
        const onDismiss = vi.fn();
        const def = makeDefinition({ dismissible: true });
        render(<WidgetContainer definition={def} onDismiss={onDismiss} />);
        const dismissBtn = screen.getByLabelText('Dismiss');
        expect(dismissBtn).toBeDefined();
    });

    it('calls onDismiss when dismiss button is clicked', () => {
        const onDismiss = vi.fn();
        const def = makeDefinition({ dismissible: true });
        render(<WidgetContainer definition={def} onDismiss={onDismiss} />);
        fireEvent.click(screen.getByLabelText('Dismiss'));
        expect(onDismiss).toHaveBeenCalledTimes(1);
    });

    it('does not show dismiss button when dismissible is false', () => {
        const def = makeDefinition({ dismissible: false });
        render(<WidgetContainer definition={def} onDismiss={() => {}} />);
        expect(screen.queryByLabelText('Dismiss')).toBeNull();
    });

    it('shows expand-to-fullscreen button when expandable and onExpand provided', () => {
        const def = makeDefinition({ expandable: true });
        render(<WidgetContainer definition={def} onExpand={() => {}} />);
        expect(screen.getByLabelText('Expand to full screen')).toBeDefined();
    });

    it('renders in fullFocus mode without header chrome', () => {
        const def = makeDefinition({ title: 'Should Not Show In Header' });
        const { container } = render(
            <WidgetContainer definition={def} fullFocus={true} />,
        );
        // In fullFocus mode, there is no header with the title
        // The widget content is rendered directly
        const widgetStub = screen.getByTestId('dynamic-widget');
        expect(widgetStub).toBeDefined();
        // Should not have the collapse/dismiss header buttons
        expect(screen.queryByLabelText('Collapse')).toBeNull();
        expect(screen.queryByLabelText('Dismiss')).toBeNull();
    });

    it('shows pin button when showPinButton and onAction are provided', () => {
        const onAction = vi.fn();
        const def = makeDefinition();
        render(
            <WidgetContainer
                definition={def}
                showPinButton={true}
                onAction={onAction}
            />,
        );
        const pinBtn = screen.getByLabelText('Pin to dashboard');
        expect(pinBtn).toBeDefined();
        fireEvent.click(pinBtn);
        expect(onAction).toHaveBeenCalledWith('pin');
    });
});

// =============================================================================
// Widget (simple, no-chrome wrapper)
// =============================================================================

describe('Widget', () => {
    it('renders the resolved widget component', () => {
        const def = makeDefinition({ type: 'revenue_chart' });
        render(<Widget definition={def} />);
        const widgetEl = screen.getByTestId('dynamic-widget');
        expect(widgetEl).toBeDefined();
        expect(widgetEl.textContent).toBe('revenue_chart');
    });
});

// =============================================================================
// Phase 111 Plan 05 — workflow_graph_run + branching-template routing helpers
// =============================================================================

function makeGraphNode(overrides: Partial<GraphNode> = {}): GraphNode {
    return {
        id: 'n-1',
        kind: 'agent-action',
        label: 'Step',
        ...overrides,
    } as GraphNode;
}

describe('isBranchingTemplate', () => {
    it('returns_true_for_condition_node', () => {
        const nodes: GraphNode[] = [
            makeGraphNode({ id: 't', kind: 'trigger', label: 'Start' }),
            makeGraphNode({ id: 'c', kind: 'condition', label: 'Branch?' }),
            makeGraphNode({ id: 'o', kind: 'output', label: 'Done' }),
        ];
        expect(isBranchingTemplate(nodes)).toBe(true);
    });

    it('isBranchingTemplate_returns_true_for_parallel', () => {
        const nodes: GraphNode[] = [
            makeGraphNode({ id: 't', kind: 'trigger', label: 'Start' }),
            makeGraphNode({ id: 'p', kind: 'parallel', label: 'Fan-out' }),
        ];
        expect(isBranchingTemplate(nodes)).toBe(true);
    });

    it('returns_true_for_merge', () => {
        const nodes: GraphNode[] = [
            makeGraphNode({ id: 'm', kind: 'merge', label: 'Merge' }),
        ];
        expect(isBranchingTemplate(nodes)).toBe(true);
    });

    it('isBranchingTemplate_returns_true_for_human_approval', () => {
        const nodes: GraphNode[] = [
            makeGraphNode({ id: 'h', kind: 'human-approval', label: 'Approve' }),
        ];
        expect(isBranchingTemplate(nodes)).toBe(true);
    });

    it('returns_false_for_purely_linear_template', () => {
        const nodes: GraphNode[] = [
            makeGraphNode({ id: 't', kind: 'trigger', label: 'Start' }),
            makeGraphNode({ id: 'a', kind: 'agent-action', label: 'Do' }),
            makeGraphNode({ id: 'o', kind: 'output', label: 'Done' }),
        ];
        expect(isBranchingTemplate(nodes)).toBe(false);
    });

    it('returns_false_for_null', () => {
        expect(isBranchingTemplate(null)).toBe(false);
    });

    it('returns_false_for_undefined', () => {
        expect(isBranchingTemplate(undefined)).toBe(false);
    });

    it('returns_false_for_empty_array', () => {
        expect(isBranchingTemplate([])).toBe(false);
    });
});

describe('resolveWorkflowRunWidget', () => {
    it('resolveWorkflowRunWidget_returns_workflow_graph_run_for_branching', () => {
        const tpl = {
            graph_nodes: [
                makeGraphNode({ id: 't', kind: 'trigger', label: 'Start' }),
                makeGraphNode({ id: 'c', kind: 'condition', label: 'Branch?' }),
            ],
        };
        expect(resolveWorkflowRunWidget(tpl)).toBe('workflow_graph_run');
    });

    it('resolveWorkflowRunWidget_returns_workflow_timeline_for_linear', () => {
        const tpl = {
            graph_nodes: [
                makeGraphNode({ id: 't', kind: 'trigger', label: 'Start' }),
                makeGraphNode({ id: 'a', kind: 'agent-action', label: 'Do' }),
                makeGraphNode({ id: 'o', kind: 'output', label: 'Done' }),
            ],
        };
        expect(resolveWorkflowRunWidget(tpl)).toBe('workflow_timeline');
    });

    it('resolveWorkflowRunWidget_returns_timeline_for_undefined_graph_nodes', () => {
        // Legacy template (pre-Phase-109 eager migration) with no graph_nodes.
        const tpl = {};
        expect(resolveWorkflowRunWidget(tpl)).toBe('workflow_timeline');
    });

    it('returns_workflow_timeline_for_null_graph_nodes', () => {
        const tpl = { graph_nodes: null };
        expect(resolveWorkflowRunWidget(tpl)).toBe('workflow_timeline');
    });
});

describe('WIDGET_MAP — workflow_graph_run entry', () => {
    it('WIDGET_MAP_has_workflow_graph_run', () => {
        // resolveWidget for an unknown type returns UnknownWidget. After
        // Plan 05's GREEN ships, resolveWidget('workflow_graph_run') returns
        // the real WorkflowGraphRunWidget (initially a stub component in
        // Task 05-02; Task 05-03 replaces the body).
        const Component = resolveWidget('workflow_graph_run' as never);
        expect(Component).toBeDefined();
        // resolveWidget for unknown types returns the UnknownWidget — we
        // want a different component here, so render it and check that
        // there's no "Unknown widget type" message.
        const def = makeDefinition({ type: 'workflow_graph_run' as never });
        const { container } = render(<Component definition={def} />);
        expect(container.textContent).not.toMatch(/Unknown widget type/i);
    });

    it('existing_widget_resolutions_unchanged', () => {
        // Regression guard: workflow_timeline still resolves and is not
        // accidentally swapped or removed by Plan 05's registry edit.
        const Component = resolveWidget('workflow_timeline');
        expect(Component).toBeDefined();
        const def = makeDefinition({ type: 'workflow_timeline' });
        render(<Component definition={def} />);
        const widgetEl = screen.getByTestId('dynamic-widget');
        expect(widgetEl).toBeDefined();
        expect(widgetEl.textContent).toBe('workflow_timeline');
    });
});

