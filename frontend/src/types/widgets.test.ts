// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, expect, it } from 'vitest'

import { validateWidgetDefinition } from './widgets'

describe('validateWidgetDefinition', () => {
  it('accepts media widgets with durable workspace refs', () => {
    const widget = {
      type: 'video',
      data: {
        videoUrl: 'https://example.com/video.mp4',
        asset_id: 'asset-1',
        bundle_id: 'bundle-1',
        deliverable_id: 'deliverable-1',
      },
      workspace: {
        mode: 'grid',
        bundleId: 'bundle-1',
        deliverableId: 'deliverable-1',
        workspaceItemId: 'workspace-1',
      },
    }

    expect(validateWidgetDefinition(widget)).toBe(true)
  })

  it('rejects invalid workspace layout modes', () => {
    const widget = {
      type: 'image',
      data: {
        imageUrl: 'https://example.com/image.png',
      },
      workspace: {
        mode: 'stacked',
      },
    }

    expect(validateWidgetDefinition(widget)).toBe(false)
  })
})
