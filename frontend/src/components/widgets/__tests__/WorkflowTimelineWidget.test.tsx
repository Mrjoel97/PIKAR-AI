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

describe('WorkflowTimelineWidget — inline approval', () => {
    beforeEach(() => vi.clearAllMocks());

    it('renders Approve and Reject buttons on a waiting_approval step', async () => {
        vi.mocked(fetchWithAuth).mockResolvedValueOnce({
            json: async () => ({
                execution_id: 'exec-A',
                name: 'Send Campaign', goal: 'Notify customers about Q3 launch',
                status: 'waiting_approval', created_at: '', completed_at: null, chain_info: null,
                steps: [{
                    id: 's1', phase_name: 'Approve', step_name: 'Confirm send',
                    status: 'waiting_approval', started_at: '', completed_at: null,
                    phase_index: 0, step_index: 0, duration_ms: null, tool_name: 'send_email',
                    error_message: null, outcome_text: null, outcome_source: null,
                }],
            }),
        } as Response);
        render(<WorkflowTimelineWidget definition={{
            type: 'workflow_timeline', title: 'X', data: { execution_id: 'exec-A' },
        }} />);
        await waitFor(() => {
            expect(screen.getByRole('button', { name: /Approve/i })).toBeDefined();
            expect(screen.getByRole('button', { name: /Reject/i })).toBeDefined();
            expect(screen.getByText(/Awaiting your approval/i)).toBeDefined();
        });
    });

    it('POSTs to approve endpoint and disables both buttons optimistically', async () => {
        const initialFetch = vi.fn().mockResolvedValue({
            json: async () => ({
                execution_id: 'exec-B', name: 'X', goal: null,
                status: 'waiting_approval', created_at: '', completed_at: null, chain_info: null,
                steps: [{
                    id: 's1', phase_name: 'P', step_name: 'S', status: 'waiting_approval',
                    started_at: '', completed_at: null, phase_index: 0, step_index: 0,
                    duration_ms: null, tool_name: 't', error_message: null,
                    outcome_text: null, outcome_source: null,
                }],
            }),
        } as Response);
        const approveCall = vi.fn().mockResolvedValue({ ok: true } as Response);
        vi.mocked(fetchWithAuth).mockImplementation((url: any, opts?: any) => {
            if (typeof url === 'string' && url.endsWith('/approve')) return approveCall(url, opts);
            return initialFetch(url, opts);
        });

        render(<WorkflowTimelineWidget definition={{
            type: 'workflow_timeline', title: 'X', data: { execution_id: 'exec-B' },
        }} />);

        const { fireEvent } = await import('@testing-library/react');
        const approveBtn = await screen.findByRole('button', { name: /Approve/i });
        fireEvent.click(approveBtn);

        await waitFor(() => {
            expect(approveCall).toHaveBeenCalledWith(
                '/workflows/executions/exec-B/steps/s1/approve',
                expect.objectContaining({ method: 'POST' }),
            );
        });
        // Both buttons disabled after click
        expect((approveBtn as HTMLButtonElement).disabled).toBe(true);
    });
});

describe('WorkflowTimelineWidget — collapsed strip', () => {
    beforeEach(() => vi.clearAllMocks());

    it('renders one-line strip when payload.interactive is false', async () => {
        vi.mocked(fetchWithAuth).mockResolvedValueOnce({
            json: async () => ({
                execution_id: 'exec-strip-1',
                name: 'Nightly Report',
                goal: null,
                status: 'running',
                created_at: '',
                completed_at: null,
                chain_info: null,
                steps: [
                    {
                        id: 's1', phase_name: '', step_name: '', status: 'completed',
                        started_at: '', completed_at: '', phase_index: 0, step_index: 0,
                        duration_ms: 1, tool_name: '', error_message: null,
                        outcome_text: null, outcome_source: null,
                    },
                    {
                        id: 's2', phase_name: '', step_name: '', status: 'running',
                        started_at: '', completed_at: null, phase_index: 0, step_index: 1,
                        duration_ms: null, tool_name: '', error_message: null,
                        outcome_text: null, outcome_source: null,
                    },
                ],
            }),
        } as Response);

        render(<WorkflowTimelineWidget definition={{
            type: 'workflow_timeline',
            title: 'X',
            data: { execution_id: 'exec-strip-1', interactive: false },
        }} />);

        await waitFor(() => {
            expect(screen.getByTestId('workflow-strip')).toBeDefined();
            expect(screen.getByText(/Nightly Report/)).toBeDefined();
            expect(screen.getByText(/step 2 of 2/i)).toBeDefined();
        });
    });

    it('auto-expands the strip when a step is waiting_approval', async () => {
        vi.mocked(fetchWithAuth).mockResolvedValueOnce({
            json: async () => ({
                execution_id: 'exec-strip-2',
                name: 'Cron',
                goal: null,
                status: 'waiting_approval',
                created_at: '',
                completed_at: null,
                chain_info: null,
                steps: [{
                    id: 's1', phase_name: '', step_name: 'X', status: 'waiting_approval',
                    started_at: '', completed_at: null, phase_index: 0, step_index: 0,
                    duration_ms: null, tool_name: '', error_message: null,
                    outcome_text: null, outcome_source: null,
                }],
            }),
        } as Response);

        render(<WorkflowTimelineWidget definition={{
            type: 'workflow_timeline',
            title: 'X',
            data: { execution_id: 'exec-strip-2', interactive: false },
        }} />);

        await waitFor(() => {
            // expanded view shown, not strip
            expect(screen.queryByTestId('workflow-strip')).toBeNull();
            expect(screen.getByRole('button', { name: /Approve/i })).toBeDefined();
        });
    });

    it('clicking the strip expands to full view', async () => {
        vi.mocked(fetchWithAuth).mockResolvedValueOnce({
            json: async () => ({
                execution_id: 'exec-strip-3',
                name: 'Daily Sync',
                goal: null,
                status: 'running',
                created_at: '',
                completed_at: null,
                chain_info: null,
                steps: [{
                    id: 's1', phase_name: 'P', step_name: 'S', status: 'running',
                    started_at: '', completed_at: null, phase_index: 0, step_index: 0,
                    duration_ms: null, tool_name: '', error_message: null,
                    outcome_text: null, outcome_source: null,
                }],
            }),
        } as Response);
        render(<WorkflowTimelineWidget definition={{
            type: 'workflow_timeline',
            title: 'X',
            data: { execution_id: 'exec-strip-3', interactive: false },
        }} />);
        const strip = await screen.findByTestId('workflow-strip');
        const { fireEvent } = await import('@testing-library/react');
        fireEvent.click(strip);
        await waitFor(() => {
            expect(screen.queryByTestId('workflow-strip')).toBeNull();
            // Header should appear when expanded
            expect(screen.getByText('Daily Sync')).toBeDefined();
        });
    });
});
