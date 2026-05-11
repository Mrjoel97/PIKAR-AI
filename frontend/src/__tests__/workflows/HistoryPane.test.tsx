// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for HistoryPane (Phase 110 Plan 05 Task 05-02).
 *
 * Spec: slide-in right-side pane lists ALL versions with version_number,
 * saved_at, saved_by_user_name, comment. Revert button on non-current
 * versions → confirmation dialog → onRevert(versionId) prop. Close button.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import { HistoryPane } from '@/components/workflows/editor/HistoryPane';
import type { HistoryItem } from '@/services/workflows';

const SAMPLE_HISTORY: HistoryItem[] = [
    {
        version_id: 'v3',
        version_number: 3,
        saved_at: '2026-05-11T20:00:00Z',
        saved_by_user_id: 'u1',
        saved_by_user_name: 'Alice',
        comment: 'Added approval step',
    },
    {
        version_id: 'v2',
        version_number: 2,
        saved_at: '2026-05-11T19:00:00Z',
        saved_by_user_id: 'u1',
        saved_by_user_name: 'Alice',
        comment: null,
    },
    {
        version_id: 'v1',
        version_number: 1,
        saved_at: '2026-05-11T18:00:00Z',
        saved_by_user_id: 'u2',
        saved_by_user_name: 'Bob',
        comment: 'Initial save',
    },
];

describe('HistoryPane', () => {
    it('renders all versions with version_number, saved_at, saved_by_user_name', () => {
        render(
            <HistoryPane
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onRevert={() => {}}
                onClose={() => {}}
            />,
        );
        expect(screen.getByTestId('history-pane')).toBeTruthy();
        expect(screen.getByText(/v3/i)).toBeTruthy();
        expect(screen.getByText(/v2/i)).toBeTruthy();
        expect(screen.getByText(/v1/i)).toBeTruthy();
        const aliceMatches = screen.getAllByText(/Alice/i);
        expect(aliceMatches.length).toBeGreaterThanOrEqual(2);
        expect(screen.getByText(/Bob/i)).toBeTruthy();
    });

    it('renders comments when present', () => {
        render(
            <HistoryPane
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onRevert={() => {}}
                onClose={() => {}}
            />,
        );
        expect(screen.getByText(/Added approval step/i)).toBeTruthy();
        expect(screen.getByText(/Initial save/i)).toBeTruthy();
    });

    it('shows Revert button on non-current versions only', () => {
        render(
            <HistoryPane
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onRevert={() => {}}
                onClose={() => {}}
            />,
        );
        // Non-current versions have revert buttons
        expect(screen.queryByTestId('revert-button-v2')).toBeTruthy();
        expect(screen.queryByTestId('revert-button-v1')).toBeTruthy();
        // Current version (v3) does NOT have a revert button
        expect(screen.queryByTestId('revert-button-v3')).toBeNull();
    });

    it('clicking Revert opens a confirmation dialog', () => {
        render(
            <HistoryPane
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onRevert={() => {}}
                onClose={() => {}}
            />,
        );
        // No confirm dialog initially
        expect(screen.queryByTestId('history-revert-confirm')).toBeNull();
        fireEvent.click(screen.getByTestId('revert-button-v1'));
        // Confirm dialog appears
        expect(screen.getByTestId('history-revert-confirm')).toBeTruthy();
    });

    it('confirming the dialog calls onRevert with the target versionId', () => {
        const onRevert = vi.fn();
        render(
            <HistoryPane
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onRevert={onRevert}
                onClose={() => {}}
            />,
        );
        fireEvent.click(screen.getByTestId('revert-button-v1'));
        const confirmBtn = screen.getByTestId('history-revert-confirm-yes');
        fireEvent.click(confirmBtn);
        expect(onRevert).toHaveBeenCalledWith('v1');
    });

    it('cancelling the dialog does NOT call onRevert', () => {
        const onRevert = vi.fn();
        render(
            <HistoryPane
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onRevert={onRevert}
                onClose={() => {}}
            />,
        );
        fireEvent.click(screen.getByTestId('revert-button-v2'));
        const cancelBtn = screen.getByTestId('history-revert-confirm-cancel');
        fireEvent.click(cancelBtn);
        expect(onRevert).not.toHaveBeenCalled();
        // Confirm dialog dismissed
        expect(screen.queryByTestId('history-revert-confirm')).toBeNull();
    });

    it('close button calls onClose', () => {
        const onClose = vi.fn();
        render(
            <HistoryPane
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onRevert={() => {}}
                onClose={onClose}
            />,
        );
        fireEvent.click(screen.getByTestId('history-pane-close'));
        expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('shows empty-state copy when history is empty', () => {
        render(
            <HistoryPane
                history={[]}
                currentVersionId={null}
                onRevert={() => {}}
                onClose={() => {}}
            />,
        );
        expect(screen.getByText(/no version history/i)).toBeTruthy();
    });
});
