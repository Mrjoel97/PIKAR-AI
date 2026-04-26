// @vitest-environment jsdom

import type { ComponentProps, ReactNode } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ActiveWorkspace } from './ActiveWorkspace';

let mockSessionWidgets: Array<{
  id: string;
  definition: { type: string; title?: string; data?: Record<string, unknown> };
  userId: string;
  sessionId: string;
  createdAt: string;
}> = [];
let mockVisibleSessionId: string | null = null;

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: ComponentProps<'div'>) => <div {...props}>{children}</div>,
  },
}));

vi.mock('@/components/widgets/WidgetRegistry', () => ({
  WidgetContainer: ({ definition }: { definition?: { type?: string } }) => (
    <div data-testid="widget-container">{definition?.type}</div>
  ),
}));

vi.mock('@/services/widgetDisplay', () => ({
  WidgetDisplayService: class {
    getSessionWidgets() {
      return mockSessionWidgets;
    }
    clearSessionWidgets() {
      return undefined;
    }
  },
  WIDGET_CHANGE_EVENT: 'widget-change',
  WORKSPACE_ACTIVITY_EVENT: 'workspace-activity',
  WORKSPACE_ITEMS_EVENT: 'workspace-items',
  buildWorkspaceRenderableItem: vi.fn((widget, userId, options) => ({
    id: options?.id || 'workspace-item-1',
    widget,
    userId,
    sessionId: options?.sessionId,
    workflowExecutionId: undefined,
    mode: options?.mode || 'focus',
    title: widget?.title,
    persistent: Boolean(options?.persistent),
    createdAt: options?.createdAt || '2026-04-26T00:00:00Z',
    updatedAt: options?.updatedAt || '2026-04-26T00:00:00Z',
  })),
  clearWorkspaceItems: vi.fn(),
  isWorkspaceCanvasWidget: vi.fn((widget?: { type?: string }) => widget?.type !== 'morning_briefing' && widget?.type !== 'campaign_hub'),
  isWorkspaceCanvasWidgetType: vi.fn((type: string) => type !== 'morning_briefing' && type !== 'campaign_hub'),
  setActiveWorkspaceItem: vi.fn(),
}));

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: {
          user: {
            id: 'user-1',
            email: 'alex@example.com',
            user_metadata: {
              full_name: 'Alex Executive',
            },
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
    visibleSessionId: mockVisibleSessionId,
  }),
}));

vi.mock('react-markdown', () => ({
  default: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
}));

describe('ActiveWorkspace', () => {
  beforeEach(() => {
    mockSessionWidgets = [];
    mockVisibleSessionId = null;
  });

  it('keeps the empty workspace free of dashboard brief cards', async () => {
    render(<ActiveWorkspace user={{}} persona="startup" />);

    await waitFor(() => {
      expect(screen.getByText('No agent workspace items yet for this session.')).toBeTruthy();
    });

    expect(screen.getByText('Workspace Canvas')).toBeTruthy();
    expect(screen.queryByText('Your Brief')).toBeNull();
    expect(screen.queryByText(/Start with your brief, use the onboarding checklist/i)).toBeNull();
  });

  it('filters command center widgets out of the workspace canvas', async () => {
    mockVisibleSessionId = 'session-1';
    mockSessionWidgets = [
      {
        id: 'campaign-1',
        definition: { type: 'campaign_hub', title: 'Campaign Hub', data: {} },
        userId: 'user-1',
        sessionId: 'session-1',
        createdAt: '2026-04-26T00:00:00Z',
      },
      {
        id: 'analysis-1',
        definition: {
          type: 'braindump_analysis',
          title: 'Brain Dump Analysis',
          data: {
            markdown: '# Analysis',
            documentId: 'doc-1',
            title: 'Brain Dump Analysis',
            keyThemes: [],
            actionItemCount: 0,
          },
        },
        userId: 'user-1',
        sessionId: 'session-1',
        createdAt: '2026-04-26T00:01:00Z',
      },
    ];

    render(<ActiveWorkspace user={{}} persona="startup" />);

    await waitFor(() => {
      expect(screen.getByText('Brain Dump Analysis')).toBeTruthy();
    });

    expect(screen.queryByText('Campaign Hub')).toBeNull();
    expect(screen.getAllByTestId('widget-container')).toHaveLength(1);
    expect(screen.getByTestId('widget-container').textContent).toBe('braindump_analysis');
  });
});
