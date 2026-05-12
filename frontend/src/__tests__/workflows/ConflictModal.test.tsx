// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for ConflictModal (Phase 110 Plan 05 Task 05-03).
 *
 * Spec B decision 6 — three buttons:
 *   - "View their changes" — discards local edits, loads fresh template
 *   - "Overwrite" — secondary confirm → re-fires PUT with body.etag (B-2)
 *   - "Cancel" — closes modal, local state preserved
 *
 * Component is controlled via `open` prop. Escape key fires onCancel.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import { ConflictModal } from '@/components/workflows/editor/ConflictModal';
import type { WorkflowTemplate } from '@/services/workflows';

const SAMPLE_TEMPLATE: WorkflowTemplate = {
    id: 'tpl-1',
    name: 'Test workflow',
    category: 'sales',
    description: null,
    phases: [],
    persona: 'sales',
    lifecycle_status: 'published',
    triggers_enabled: true,
    is_active: true,
    template_version: 2,
    template_key: null,
    created_at: '2026-05-11T18:00:00Z',
    updated_at: '2026-05-11T20:00:00Z',
    created_by: 'u1',
} as unknown as WorkflowTemplate;

describe('ConflictModal', () => {
    it('does not render when open=false', () => {
        const { container } = render(
            <ConflictModal
                open={false}
                freshTemplate={SAMPLE_TEMPLATE}
                onViewTheirChanges={() => {}}
                onOverwrite={() => {}}
                onCancel={() => {}}
            />,
        );
        expect(container.firstChild).toBeNull();
    });

    it('renders three buttons when open: View their changes / Overwrite / Cancel', () => {
        render(
            <ConflictModal
                open={true}
                freshTemplate={SAMPLE_TEMPLATE}
                onViewTheirChanges={() => {}}
                onOverwrite={() => {}}
                onCancel={() => {}}
            />,
        );
        expect(screen.getByTestId('conflict-modal')).toBeTruthy();
        expect(screen.getByTestId('conflict-view')).toBeTruthy();
        expect(screen.getByTestId('conflict-overwrite')).toBeTruthy();
        expect(screen.getByTestId('conflict-cancel')).toBeTruthy();
    });

    it('clicking "View their changes" calls onViewTheirChanges', () => {
        const onView = vi.fn();
        render(
            <ConflictModal
                open={true}
                freshTemplate={SAMPLE_TEMPLATE}
                onViewTheirChanges={onView}
                onOverwrite={() => {}}
                onCancel={() => {}}
            />,
        );
        fireEvent.click(screen.getByTestId('conflict-view'));
        expect(onView).toHaveBeenCalledTimes(1);
    });

    it('clicking "Cancel" calls onCancel', () => {
        const onCancel = vi.fn();
        render(
            <ConflictModal
                open={true}
                freshTemplate={SAMPLE_TEMPLATE}
                onViewTheirChanges={() => {}}
                onOverwrite={() => {}}
                onCancel={onCancel}
            />,
        );
        fireEvent.click(screen.getByTestId('conflict-cancel'));
        expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it('clicking "Overwrite" shows a secondary confirm dialog (does NOT immediately call onOverwrite)', () => {
        const onOverwrite = vi.fn();
        render(
            <ConflictModal
                open={true}
                freshTemplate={SAMPLE_TEMPLATE}
                onViewTheirChanges={() => {}}
                onOverwrite={onOverwrite}
                onCancel={() => {}}
            />,
        );
        fireEvent.click(screen.getByTestId('conflict-overwrite'));
        // onOverwrite has NOT been called yet — needs secondary confirm
        expect(onOverwrite).not.toHaveBeenCalled();
        // Secondary confirm button is now visible
        expect(screen.getByTestId('conflict-overwrite-confirm')).toBeTruthy();
    });

    it('confirming the secondary overwrite dialog calls onOverwrite', () => {
        const onOverwrite = vi.fn();
        render(
            <ConflictModal
                open={true}
                freshTemplate={SAMPLE_TEMPLATE}
                onViewTheirChanges={() => {}}
                onOverwrite={onOverwrite}
                onCancel={() => {}}
            />,
        );
        fireEvent.click(screen.getByTestId('conflict-overwrite'));
        fireEvent.click(screen.getByTestId('conflict-overwrite-confirm'));
        expect(onOverwrite).toHaveBeenCalledTimes(1);
    });

    it('pressing Escape calls onCancel', () => {
        const onCancel = vi.fn();
        render(
            <ConflictModal
                open={true}
                freshTemplate={SAMPLE_TEMPLATE}
                onViewTheirChanges={() => {}}
                onOverwrite={() => {}}
                onCancel={onCancel}
            />,
        );
        fireEvent.keyDown(window, { key: 'Escape' });
        expect(onCancel).toHaveBeenCalled();
    });

    it('handles null freshTemplate gracefully (still renders)', () => {
        render(
            <ConflictModal
                open={true}
                freshTemplate={null}
                onViewTheirChanges={() => {}}
                onOverwrite={() => {}}
                onCancel={() => {}}
            />,
        );
        // Modal still renders the three buttons even without fresh template
        expect(screen.getByTestId('conflict-modal')).toBeTruthy();
        expect(screen.getByTestId('conflict-view')).toBeTruthy();
    });
});
