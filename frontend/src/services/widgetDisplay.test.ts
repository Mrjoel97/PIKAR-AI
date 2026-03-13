import { describe, expect, it } from 'vitest'

import {
  WORKSPACE_ITEMS_EVENT,
  buildWorkspaceRenderableItem,
  dispatchWorkspaceWidget,
  type WorkspaceItemsEventDetail,
} from './widgetDisplay'

describe('workspace item helpers', () => {
  it('builds a durable workspace item from widget refs', () => {
    const widget = {
      type: 'image',
      title: 'Hero image',
      data: {
        imageUrl: 'https://example.com/image.png',
        workspace_item_id: 'workspace-1',
        session_id: 'session-1',
        workflow_execution_id: 'workflow-1',
      },
      workspace: {
        mode: 'grid',
        workspaceItemId: 'workspace-1',
        sessionId: 'session-1',
        workflowExecutionId: 'workflow-1',
      },
    } as const

    const item = buildWorkspaceRenderableItem(widget, 'user-1')

    expect(item.id).toBe('workspace-1')
    expect(item.sessionId).toBe('session-1')
    expect(item.workflowExecutionId).toBe('workflow-1')
    expect(item.mode).toBe('grid')
    expect(item.persistent).toBe(true)
  })

  it('dispatches add and set_active workspace events for focus widgets', () => {
    const events: WorkspaceItemsEventDetail[] = []
    const listener = (event: Event) => {
      events.push((event as CustomEvent<WorkspaceItemsEventDetail>).detail)
    }

    window.addEventListener(WORKSPACE_ITEMS_EVENT, listener)

    dispatchWorkspaceWidget(
      {
        type: 'video',
        title: 'Launch cut',
        data: {
          videoUrl: 'https://example.com/video.mp4',
          workspace_item_id: 'workspace-video-1',
          session_id: 'session-2',
        },
        workspace: {
          mode: 'focus',
          workspaceItemId: 'workspace-video-1',
          sessionId: 'session-2',
        },
      },
      'user-2',
      { setActive: true },
    )

    window.removeEventListener(WORKSPACE_ITEMS_EVENT, listener)

    expect(events).toHaveLength(2)
    expect(events[0]?.action).toBe('add')
    expect(events[0]?.item?.id).toBe('workspace-video-1')
    expect(events[1]?.action).toBe('set_active')
    expect(events[1]?.itemId).toBe('workspace-video-1')
  })
})
