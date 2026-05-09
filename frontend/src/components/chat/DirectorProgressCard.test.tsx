// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

import { DirectorProgressCard } from './DirectorProgressCard';

describe('DirectorProgressCard', () => {
    const sampleCaptions = [
        { scene: 1, caption: 'Open on a sunlit cafe at dawn.' },
        { scene: 2, caption: 'Barista pours latte art.', duration: 4 },
        { scene: 3, caption: 'Cut to a close-up of the logo.' },
    ];

    it('renders the header with the scene count', () => {
        render(
            <DirectorProgressCard
                captions={sampleCaptions}
                scene_count={3}
            />,
        );

        expect(screen.getByText(/Storyboard \(3 scenes\)/i)).toBeTruthy();
    });

    it('renders every caption text in a numbered list', () => {
        render(
            <DirectorProgressCard
                captions={sampleCaptions}
                scene_count={3}
                video_prompt="A morning cafe brand spot"
            />,
        );

        expect(screen.getByText(/Open on a sunlit cafe at dawn\./)).toBeTruthy();
        expect(screen.getByText(/Barista pours latte art\./)).toBeTruthy();
        expect(screen.getByText(/Cut to a close-up of the logo\./)).toBeTruthy();
        expect(screen.getByText(/A morning cafe brand spot/)).toBeTruthy();
        expect(screen.getByText(/4s/)).toBeTruthy();
    });

    it('uses singular "scene" for a single-scene storyboard', () => {
        render(
            <DirectorProgressCard
                captions={[{ scene: 1, caption: 'One and done.' }]}
                scene_count={1}
            />,
        );

        expect(screen.getByText(/Storyboard \(1 scene\)/i)).toBeTruthy();
    });

    it('collapses the body when the header is clicked', () => {
        render(
            <DirectorProgressCard
                captions={sampleCaptions}
                scene_count={3}
            />,
        );

        // Body visible by default.
        expect(screen.getByText(/Open on a sunlit cafe at dawn\./)).toBeTruthy();

        const toggle = screen.getByRole('button', { name: /Storyboard/i });
        fireEvent.click(toggle);

        expect(screen.queryByText(/Open on a sunlit cafe at dawn\./)).toBeNull();
    });

    it('shows an empty-state message when there are no captions', () => {
        render(<DirectorProgressCard captions={[]} scene_count={0} />);
        expect(screen.getByText(/No scene captions available\./)).toBeTruthy();
    });
});
