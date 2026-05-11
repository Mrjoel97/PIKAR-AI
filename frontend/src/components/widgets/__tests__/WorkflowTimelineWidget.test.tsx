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

describe('WorkflowTimelineWidget — per-step outcomes', () => {
    beforeEach(() => vi.clearAllMocks());

    it('renders outcome_text on a step row when present', async () => {
        vi.mocked(fetchWithAuth).mockResolvedValueOnce({
            json: async () => ({
                execution_id: 'exec-2',
                name: 'X',
                goal: null,
                status: 'completed',
                created_at: '2026-05-11T10:00:00Z',
                completed_at: '2026-05-11T10:05:00Z',
                chain_info: null,
                steps: [{
                    id: 's1',
                    phase_name: 'Plan',
                    step_name: 'Draft outline',
                    status: 'completed',
                    started_at: '2026-05-11T10:00:00Z',
                    completed_at: '2026-05-11T10:01:00Z',
                    phase_index: 0,
                    step_index: 0,
                    duration_ms: 60000,
                    tool_name: 'generate_doc',
                    error_message: null,
                    outcome_text: 'Generated 3-page outline.',
                    outcome_source: 'tool',
                }],
            }),
        } as Response);
        render(<WorkflowTimelineWidget definition={{
            type: 'workflow_timeline',
            title: 'X',
            data: { execution_id: 'exec-2' },
        }} />);
        await waitFor(() => {
            expect(screen.getByText('Generated 3-page outline.')).toBeDefined();
        });
    });

    it('renders shimmer when outcome_text is null on a completed step', async () => {
        vi.mocked(fetchWithAuth).mockResolvedValueOnce({
            json: async () => ({
                execution_id: 'exec-3',
                name: 'X', goal: null, status: 'completed',
                created_at: '', completed_at: '', chain_info: null,
                steps: [{
                    id: 's1', phase_name: 'P', step_name: 'Step', status: 'completed',
                    started_at: '', completed_at: '', phase_index: 0, step_index: 0,
                    duration_ms: 1, tool_name: 't', error_message: null,
                    outcome_text: null, outcome_source: null,
                }],
            }),
        } as Response);
        render(<WorkflowTimelineWidget definition={{
            type: 'workflow_timeline', title: 'X', data: { execution_id: 'exec-3' },
        }} />);
        await waitFor(() => {
            expect(screen.getByTestId('outcome-shimmer')).toBeDefined();
        });
    });

    it('does not render shimmer when step is still running', async () => {
        vi.mocked(fetchWithAuth).mockResolvedValueOnce({
            json: async () => ({
                execution_id: 'exec-4',
                name: 'X', goal: null, status: 'running',
                created_at: '', completed_at: null, chain_info: null,
                steps: [{
                    id: 's1', phase_name: 'P', step_name: 'Step', status: 'running',
                    started_at: '', completed_at: null, phase_index: 0, step_index: 0,
                    duration_ms: null, tool_name: 't', error_message: null,
                    outcome_text: null, outcome_source: null,
                }],
            }),
        } as Response);
        render(<WorkflowTimelineWidget definition={{
            type: 'workflow_timeline', title: 'X', data: { execution_id: 'exec-4' },
        }} />);
        await waitFor(() => {
            // Running step renders without shimmer
            expect(screen.queryByTestId('outcome-shimmer')).toBeNull();
        });
    });
});
