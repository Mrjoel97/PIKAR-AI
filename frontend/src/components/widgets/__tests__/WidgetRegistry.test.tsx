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
} from '../WidgetRegistry';
import type { WidgetDefinition } from '@/types/widgets';

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
            'campaign_hub',
            'self_improvement',
            'workflow_observability',
            'workflow_timeline',
            'daily_briefing',
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
