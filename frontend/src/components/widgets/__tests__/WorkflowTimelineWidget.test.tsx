// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import WorkflowTimelineWidget from '../WorkflowTimelineWidget';

vi.mock('@/services/api', () => ({
    fetchWithAuth: vi.fn(),
}));

import { fetchWithAuth } from '@/services/api';

describe('WorkflowTimelineWidget — goal header', () => {
    beforeEach(() => vi.clearAllMocks());

    it('renders the workflow name and goal in the header', async () => {
        vi.mocked(fetchWithAuth).mockResolvedValueOnce({
            json: async () => ({
                execution_id: 'exec-1',
                name: 'Marketing Plan',
                goal: 'Ship the Q3 marketing plan by Friday',
                status: 'running',
                created_at: '2026-05-11T10:00:00Z',
                completed_at: null,
                steps: [],
                chain_info: null,
            }),
        } as Response);

        render(<WorkflowTimelineWidget definition={{
            type: 'workflow_timeline',
            title: 'X',
            data: { execution_id: 'exec-1' },
        }} />);

        await waitFor(() => {
            expect(screen.getByText('Marketing Plan')).toBeDefined();
            expect(screen.getByText(/Ship the Q3 marketing plan by Friday/)).toBeDefined();
        });
    });

    it('does not render goal block when goal is null', async () => {
        vi.mocked(fetchWithAuth).mockResolvedValueOnce({
            json: async () => ({
                execution_id: 'exec-2',
                name: 'No Goal Workflow',
                goal: null,
                status: 'running',
                created_at: '2026-05-11T10:00:00Z',
                completed_at: null,
                steps: [],
                chain_info: null,
            }),
        } as Response);

        render(<WorkflowTimelineWidget definition={{
            type: 'workflow_timeline',
            title: 'X',
            data: { execution_id: 'exec-2' },
        }} />);

        await waitFor(() => {
            expect(screen.getByText('No Goal Workflow')).toBeDefined();
        });
        // No goal subtitle should appear
        expect(screen.queryByText(/Ship the Q3/)).toBeNull();
    });
});
