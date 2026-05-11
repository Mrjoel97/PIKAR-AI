// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for VersionSelector (Phase 110 Plan 05 Task 05-02).
 *
 * Spec: controlled dropdown listing recent versions, "current" badge on
 * the version matching template.current_version_id, onSelectVersion +
 * onOpenHistory callbacks, empty-history placeholder.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import { VersionSelector } from '@/components/workflows/editor/VersionSelector';
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

describe('VersionSelector', () => {
    it('renders the selector trigger button with current version label', () => {
        render(
            <VersionSelector
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onSelectVersion={() => {}}
                onOpenHistory={() => {}}
            />,
        );
        const trigger = screen.getByTestId('version-selector');
        expect(trigger).toBeTruthy();
        // Should show "v3" somewhere as the current version
        expect(screen.getByTestId('version-selector-trigger').textContent).toMatch(/v3/);
    });

    it('opens the dropdown when trigger is clicked, listing versions newest-first', () => {
        render(
            <VersionSelector
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onSelectVersion={() => {}}
                onOpenHistory={() => {}}
            />,
        );
        fireEvent.click(screen.getByTestId('version-selector-trigger'));
        // After open, dropdown should be visible
        const items = screen.getAllByTestId(/version-item-/);
        expect(items.length).toBeGreaterThanOrEqual(3);
        // First item is newest (v3)
        expect(items[0].textContent).toMatch(/v3/);
    });

    it('shows "current" badge on the version matching currentVersionId', () => {
        render(
            <VersionSelector
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onSelectVersion={() => {}}
                onOpenHistory={() => {}}
            />,
        );
        fireEvent.click(screen.getByTestId('version-selector-trigger'));
        const currentBadges = screen.getAllByText(/current/i);
        // At least one — on the v3 row in the dropdown
        expect(currentBadges.length).toBeGreaterThanOrEqual(1);
    });

    it('calls onSelectVersion when a non-current item is clicked', () => {
        const onSelect = vi.fn();
        render(
            <VersionSelector
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onSelectVersion={onSelect}
                onOpenHistory={() => {}}
            />,
        );
        fireEvent.click(screen.getByTestId('version-selector-trigger'));
        const v2Item = screen.getByTestId('version-item-v2');
        fireEvent.click(v2Item);
        expect(onSelect).toHaveBeenCalledWith('v2');
    });

    it('calls onOpenHistory when "View full history" is clicked', () => {
        const onOpen = vi.fn();
        render(
            <VersionSelector
                history={SAMPLE_HISTORY}
                currentVersionId="v3"
                onSelectVersion={() => {}}
                onOpenHistory={onOpen}
            />,
        );
        fireEvent.click(screen.getByTestId('version-selector-trigger'));
        const historyButton = screen.getByTestId('version-selector-open-history');
        fireEvent.click(historyButton);
        expect(onOpen).toHaveBeenCalledTimes(1);
    });

    it('renders empty-history placeholder when history is empty', () => {
        render(
            <VersionSelector
                history={[]}
                currentVersionId={null}
                onSelectVersion={() => {}}
                onOpenHistory={() => {}}
            />,
        );
        expect(screen.getByTestId('version-selector-trigger').textContent).toMatch(/v1|—/);
    });
});
