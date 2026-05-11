// @vitest-environment jsdom

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import type { ComponentProps, ReactNode } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { ActiveWorkspace } from './ActiveWorkspace';
import type { WorkspaceEvent } from '@/types/workspace-events';

// Mutable holder so each test can adjust the events surfaced by the hook
// before render. The hook is mocked below to return whatever is here.
let mockSseEvents: WorkspaceEvent[] = [];

vi.mock('@/hooks/useWorkspaceEvents', () => ({
    useWorkspaceEvents: () => mockSseEvents,
}));

// Stub framer-motion so the test does not animate.
vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: ComponentProps<'div'>) => <div {...props}>{children}</div>,
        section: ({ children, ...props }: ComponentProps<'section'>) => <section {...props}>{children}</section>,
    },
}));

// Stub child components — this test cares only about the SSE artifact strip.
vi.mock('@/components/dashboard/DashboardBriefCard', () => ({
    DashboardBriefCard: () => <div data-testid="dashboard-brief-card" />,
    default: () => <div data-testid="dashboard-brief-card" />,
}));
vi.mock('@/components/dashboard/OnboardingChecklist', () => ({
    default: () => <div data-testid="onboarding-checklist" />,
}));
vi.mock('@/components/workspace/WorkspaceCanvas', () => ({
    WorkspaceCanvas: () => <div data-testid="workspace-canvas" />,
}));
vi.mock('@/components/widgets/WidgetRegistry', () => ({
    WidgetContainer: () => <div data-testid="widget-container" />,
}));

vi.mock('@/services/widgetDisplay', () => ({
    WidgetDisplayService: class {
        getSessionWidgets() {
            return [];
        }
        clearSessionWidgets() {
            return undefined;
        }
        persistWorkspaceItem() {
            return undefined;
        }
        deleteWidget() {
            return undefined;
        }
    },
    WIDGET_CHANGE_EVENT: 'widget-change',
    WORKSPACE_ACTIVITY_EVENT: 'workspace-activity',
    WORKSPACE_ITEMS_EVENT: 'workspace-items',
    buildWorkspaceRenderableItem: vi.fn(),
    clearWorkspaceItems: vi.fn(),
    isWorkspaceCanvasWidget: vi.fn(() => true),
    isWorkspaceCanvasWidgetType: vi.fn(() => true),
    setActiveWorkspaceItem: vi.fn(),
}));

vi.mock('@/lib/supabase/client', () => ({
    createClient: () => ({
        auth: {
            getUser: vi.fn().mockResolvedValue({
                data: {
                    user: {
                        id: 'u-1',
                        email: 'a@b.c',
                        user_metadata: { full_name: 'Alex' },
                    },
                },
            }),
        },
        from: vi.fn(() => ({
            select: vi.fn().mockReturnThis(),
            eq: vi.fn().mockReturnThis(),
            order: vi.fn().mockResolvedValue({ data: [], error: null }),
            delete: vi.fn().mockReturnThis(),
        })),
    }),
}));

vi.mock('@/contexts/SessionControlContext', () => ({
    useSessionControl: () => ({
        visibleSessionId: 's-1',
    }),
}));

vi.mock('react-markdown', () => ({
    default: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
}));

describe('ActiveWorkspace SSE artifact rendering', () => {
    beforeEach(() => {
        mockSseEvents = [];
        if (typeof localStorage !== 'undefined') {
            localStorage.clear();
        }
    });

    it('renders artifact cards for every artifact event from the hook', async () => {
        mockSseEvents = [
            {
                kind: 'progress',
                agent_id: 'FIN',
                contract_id: null,
                item: 'p',
                status: 'started',
            },
            {
                kind: 'artifact',
                agent_id: 'FIN',
                contract_id: 'c-1',
                artifact_kind: 'report',
                ref: 'vault://1',
                summary: 'FY26 forecast',
                preview_url: null,
            },
            {
                kind: 'artifact',
                agent_id: 'CONT',
                contract_id: 'c-2',
                artifact_kind: 'image',
                ref: 'vault://2',
                summary: 'Launch hero',
                preview_url: 'https://cdn/hero.png',
            },
        ];

        render(<ActiveWorkspace persona="startup" />);

        await waitFor(() => {
            expect(screen.getAllByTestId('workspace-artifact-card')).toHaveLength(2);
        });

        expect(screen.getByText('FY26 forecast')).toBeTruthy();
        expect(screen.getByText('Launch hero')).toBeTruthy();
    });

    it('skips the artifact strip when no artifact events have arrived', async () => {
        mockSseEvents = [
            {
                kind: 'progress',
                agent_id: 'FIN',
                contract_id: null,
                item: 'p',
                status: 'in_progress',
            },
        ];

        render(<ActiveWorkspace persona="startup" />);

        await waitFor(() => {
            expect(screen.getByTestId('dashboard-brief-card')).toBeTruthy();
        });

        expect(screen.queryByTestId('workspace-artifact-card')).toBeNull();
    });
});
